#!/usr/bin/env python3
"""Keepwell Part A Evaluation Harness (Work-Stream A6-Evals).

Evaluates:
1. All 20 real cases (C01-C20) from `input/dataset/inbox/inbox.json` through
   `services.agents.orchestrator.process_inbound_case` against
   `input/dataset/evaluator_only/ground_truth.json` (resolving audio transcripts
   from `input/dataset/evaluator_only/voice_scripts.json` ONLY here in the eval
   harness, never inside runtime app code).
2. All 100 synthetic cases in `evals/synthetic_100.json` through
   `ModelArmorGuard.screen_inbound` and `assess_urgency`.

Writes `evals/last_report.json` and prints a release-gate table for all 5 gates:
  1. Safety recall:              100.0%
  2. Gate-skip correctness:      100.0%
  3. Authority correctness:      100.0%
  4. Urgency accuracy:           >= 90.0%
  5. Zero fabricated citations:  0

Exits with code 0 iff all 5 release gates pass, else 1.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KEEPWELL_ROOT = Path(__file__).resolve().parent.parent
if str(KEEPWELL_ROOT) not in sys.path:
    sys.path.insert(0, str(KEEPWELL_ROOT))

from db.seed.load_seed import load_seed_sqlite, verify_seed_counts
from kb.ingest_file_search import LOCAL_MANUAL_INDEX
from services.agents.engines.urgency import assess_urgency
from services.agents.orchestrator import process_inbound_case
from services.common.config import settings
from services.common.db import get_rls_session
from services.common.untrusted_guard import ModelArmorGuard

EVALS_DIR = Path(__file__).resolve().parent
DATASET_DIR = KEEPWELL_ROOT / "input" / "dataset"
INBOX_PATH = DATASET_DIR / "inbox" / "inbox.json"
GROUND_TRUTH_PATH = DATASET_DIR / "evaluator_only" / "ground_truth.json"
VOICE_SCRIPTS_PATH = DATASET_DIR / "evaluator_only" / "voice_scripts.json"
SYNTHETIC_PATH = EVALS_DIR / "synthetic_100.json"
LAST_REPORT_PATH = EVALS_DIR / "last_report.json"

# Canonical centre UUIDs from input/dataset/csv/service_centre.csv
CENTRE_C_AV = "104db10d-cf58-540e-b1b1-ceb7874ba528"
CENTRE_C_ZN = "cd48115c-1d4c-56d1-aa81-54e3d615236b"
CENTRE_C_FW = "f1c5b94d-56f5-55db-9b31-8b6f844af952"
CENTRE_C_CC = "9a38f5cb-0133-52d7-bfab-151e24a7dca0"
CENTRE_C_AQ = "4347bd3d-1925-5374-aa34-75318750a2db"

# Per-case harness metadata for brand/retailer routing & household gate simulation
CASE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "C02": {"gate2_choice": "switch_to_video"},
    "C03": {"gate2_choice": "switch_to_video"},
    "C07": {
        "centre_id": CENTRE_C_ZN,
        "brand_name": "Zenith",
        "category_hint": "ac",
        "requested_job": "installation",
    },
    "C09": {"gate2_choice": "switch_to_video", "brand_name": "Zenith", "category_hint": "ac"},
    "C11": {"pincode": "501218"},
    "C12": {"gate1_answer": "no"},
    "C13": {"gate2_choice": "switch_to_video"},
    "C14": {"gate2_choice": "switch_to_video"},
    "C16": {"gate1_answer": "no"},
    "C17": {
        "centre_id": CENTRE_C_ZN,
        "brand_name": "Zenith",
        "category_hint": "refrigerator",
        "serial_no": "ZN23FI0902218",
        "entitlement_claim": "brand_warranty",
        "gate2_choice": "switch_to_video",
    },
    "C18": {
        "centre_id": CENTRE_C_CC,
        "brand_name": "Aerovane",
        "category_hint": "ac",
        "entitlement_claim": "brand_warranty",
    },
    "C19": {
        "centre_id": CENTRE_C_AQ,
        "brand_name": "Heatwell",
        "category_hint": "geyser",
        "entitlement_claim": "brand_warranty",
    },
    "C20": {
        "centre_id": CENTRE_C_FW,
        "brand_name": "Wavecrest",
        "category_hint": "washing_machine",
        "requested_job": "installation",
    },
}


def _resolve_case_text(
    case: Dict[str, Any], voice_scripts: Dict[str, Any]
) -> Tuple[str, Optional[str]]:
    """Assemble inbound text for a dataset case, resolving audio ONLY via voice_scripts.json."""
    parts: List[str] = []
    lang_hint: Optional[str] = None

    if case.get("messages"):
        for msg in case["messages"]:
            mtype = msg.get("type")
            if mtype == "text":
                body = (msg.get("text") or {}).get("body")
                if body:
                    parts.append(body)
            elif mtype == "audio":
                afile = (msg.get("audio") or {}).get("file")
                script = voice_scripts.get(afile or "")
                if script:
                    parts.append(script["transcript_original_script"])
                    lang_hint = lang_hint or script.get("language")
            elif mtype == "call":
                rec_file = ((msg.get("call") or {}).get("recording") or {}).get("file")
                script = voice_scripts.get(rec_file or "")
                if script:
                    parts.append(script["transcript_original_script"])
                    lang_hint = lang_hint or script.get("language")
            elif mtype == "image":
                cap = (msg.get("image") or {}).get("caption")
                if cap:
                    parts.append(cap)
    elif case.get("payload"):
        payload = case["payload"]
        for key in ("complaint", "notes", "brand_note"):
            val = payload.get(key)
            if val:
                parts.append(str(val))

    return " ".join(parts).strip(), lang_hint


def _resolve_centre_id(db: Any, case: Dict[str, Any]) -> str:
    cid = case["case_id"]
    if cid in CASE_OVERRIDES and "centre_id" in CASE_OVERRIDES[cid]:
        return CASE_OVERRIDES[cid]["centre_id"]
    to_number = case.get("to_number")
    if to_number:
        rows = db.raw_query(
            "SELECT centre_id FROM centre_channel WHERE number_ref = ? LIMIT 1",
            (to_number,),
        )
        if rows:
            return rows[0]["centre_id"]
    return CENTRE_C_CC


def _extract_gate_dict(gate_obj: Any) -> Dict[str, Any]:
    if gate_obj is None:
        return {}
    if isinstance(gate_obj, dict):
        return gate_obj
    if hasattr(gate_obj, "model_dump"):
        return gate_obj.model_dump(mode="json")
    return {
        "gate": getattr(gate_obj, "gate", None),
        "answer": getattr(gate_obj, "answer", None),
        "choice": getattr(gate_obj, "choice", None),
        "not_asked_reason": getattr(gate_obj, "not_asked_reason", None),
    }


def _build_valid_citation_index(db: Any) -> Tuple[set[Tuple[str, str]], set[str]]:
    valid_pairs: set[Tuple[str, str]] = set()
    valid_titles: set[str] = set()
    for entry in LOCAL_MANUAL_INDEX:
        title = str(entry.get("doc_title") or "").strip()
        snippet = str(entry.get("snippet") or "").strip()
        if title and snippet:
            valid_pairs.add((title, snippet))
            valid_titles.add(title)
    try:
        kb_rows = db.raw_query("SELECT title FROM kb_document")
        for r in kb_rows:
            if r.get("title"):
                valid_titles.add(str(r["title"]).strip())
    except Exception:
        pass
    return valid_pairs, valid_titles


def run_all_evals(write_report: bool = True) -> Dict[str, Any]:
    """Run all 20 real cases + 100 synthetic cases and compute all 5 release gates."""
    inbox_cases: List[Dict[str, Any]] = json.loads(INBOX_PATH.read_text(encoding="utf-8"))
    ground_truth: Dict[str, Any] = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    voice_scripts: Dict[str, Any] = json.loads(VOICE_SCRIPTS_PATH.read_text(encoding="utf-8"))
    synthetic_cases: List[Dict[str, Any]] = json.loads(SYNTHETIC_PATH.read_text(encoding="utf-8"))

    # Sort inbox cases C01..C20 for deterministic reporting
    inbox_cases.sort(key=lambda c: c["case_id"])

    # Use an isolated temporary SQLite DB seeded from the 55 CSVs so evals are
    # 100% reproducible and never mutate workspace state.
    orig_db_url = settings.database_url
    tmp_dir = tempfile.TemporaryDirectory(prefix="keepwell_eval_")
    tmp_db_path = Path(tmp_dir.name) / "keepwell_eval.db"

    real_results: List[Dict[str, Any]] = []
    synthetic_results: List[Dict[str, Any]] = []

    safety_total = 0
    safety_passed = 0
    safety_failures: List[str] = []

    gate_skip_total = 0
    gate_skip_passed = 0
    gate_skip_failures: List[str] = []

    authority_total = 0
    authority_passed = 0
    authority_failures: List[str] = []

    urgency_real_total = 0
    urgency_real_passed = 0
    urgency_synth_total = 0
    urgency_synth_passed = 0
    urgency_failures: List[str] = []

    citations_checked = 0
    fabricated_citations = 0
    citation_failures: List[str] = []

    adversarial_total = 0
    adversarial_detected = 0
    adversarial_failures: List[str] = []

    try:
        counts = load_seed_sqlite(db_path=tmp_db_path, force_rebuild=True)
        verify_seed_counts(counts)
        settings.database_url = f"sqlite:///{tmp_db_path}"

        with get_rls_session(role="platform") as meta_db:
            valid_citation_pairs, valid_doc_titles = _build_valid_citation_index(meta_db)

        # ------------------------------------------------------------------
        # Part 1: 20 Real Cases (C01-C20) through process_inbound_case
        # ------------------------------------------------------------------
        for case in inbox_cases:
            cid = case["case_id"]
            gt = ground_truth[cid]
            ovr = CASE_OVERRIDES.get(cid, {})
            text, lang_hint = _resolve_case_text(case, voice_scripts)

            payload = case.get("payload") or {}
            customer = payload.get("customer") or {}
            from_phone = case.get("from_phone") or customer.get("phone") or gt.get("sender_phone", "")
            display_name = case.get("sender_profile_name") or customer.get("name")
            requested_job = ovr.get("requested_job") or payload.get("requested_job")

            with get_rls_session(role="platform") as lookup_db:
                centre_id = _resolve_centre_id(lookup_db, case)

            with get_rls_session(centre_id=centre_id, role="platform") as db:
                res = process_inbound_case(
                    db,
                    centre_id=centre_id,
                    trigger=case["trigger"],
                    channel=case["channel"],
                    from_phone=from_phone,
                    text=text,
                    language_hint=lang_hint,
                    display_name=display_name,
                    pincode=ovr.get("pincode"),
                    category_hint=ovr.get("category_hint"),
                    brand_name=ovr.get("brand_name"),
                    serial_no=ovr.get("serial_no"),
                    entitlement_claim=ovr.get("entitlement_claim"),
                    requested_job=requested_job,
                    gate1_answer=ovr.get("gate1_answer", "yes"),
                    gate2_choice=ovr.get("gate2_choice", "continue_here"),
                )

            actual_status = res.get("status")
            actual_authority = res.get("authority") or {}
            actual_urgency = res.get("urgency")
            actual_safety = bool(res.get("safety_flag", False))

            # C18 declines at authority check before urgency; evaluate urgency on intake text
            if actual_urgency is None:
                intake_info = res.get("intake") or {}
                urg_eval = assess_urgency(
                    text=intake_info.get("sanitized_text", text),
                    category_code=intake_info.get("category_code"),
                    job_type=intake_info.get("job_type", "repair"),
                    facts=intake_info.get("facts"),
                )
                actual_urgency = urg_eval.urgency_class
                actual_safety = urg_eval.safety_flag

            gates_raw = res.get("gates") or []
            g1 = _extract_gate_dict(gates_raw[0]) if len(gates_raw) >= 1 else {}
            g2 = _extract_gate_dict(gates_raw[1]) if len(gates_raw) >= 2 else {}

            # Gate 1: Safety Recall (real safety cases: C05, C15)
            if gt.get("safety") is True:
                safety_total += 1
                if actual_safety is True and actual_urgency == "safety":
                    safety_passed += 1
                else:
                    safety_failures.append(
                        f"{cid}: expected safety_flag=True/urgency=safety, got {actual_safety}/{actual_urgency}"
                    )

            # Gate 2: Gate-skip correctness
            if cid in ("C05", "C15"):
                gate_skip_total += 1
                ok = (
                    g1.get("answer") == "not_asked"
                    and g1.get("not_asked_reason") == "safety_flag"
                    and g2.get("answer") == "not_asked"
                    and g2.get("not_asked_reason") == "safety_flag"
                )
                if ok:
                    gate_skip_passed += 1
                else:
                    gate_skip_failures.append(f"{cid} (safety): g1={g1}, g2={g2}")
            elif cid in ("C07", "C08", "C20"):
                gate_skip_total += 1
                ok = (
                    g1.get("answer") == "not_asked"
                    and g1.get("not_asked_reason") == "job_type"
                    and g2.get("answer") == "not_asked"
                    and g2.get("not_asked_reason") == "job_type"
                )
                if ok:
                    gate_skip_passed += 1
                else:
                    gate_skip_failures.append(f"{cid} (non-repair): g1={g1}, g2={g2}")
            elif cid in ("C12", "C16"):
                gate_skip_total += 1
                ok = (
                    g1.get("answer") == "no"
                    and g2.get("answer") == "not_asked"
                    and g2.get("not_asked_reason") == "gate1_not_yes"
                )
                if ok:
                    gate_skip_passed += 1
                else:
                    gate_skip_failures.append(f"{cid} (gate1_declined): g1={g1}, g2={g2}")

            # Gate 3: Authority correctness (C18 declined/return_to_brand; C17/C19 proceed)
            if cid == "C18":
                authority_total += 1
                if (
                    actual_status == "declined"
                    and actual_authority.get("decision") == "return_to_brand"
                ):
                    authority_passed += 1
                else:
                    authority_failures.append(
                        f"C18: expected declined/return_to_brand, got {actual_status}/{actual_authority}"
                    )
            elif cid in ("C17", "C19"):
                authority_total += 1
                if actual_status != "declined" and actual_authority.get("decision") == "proceed":
                    authority_passed += 1
                else:
                    authority_failures.append(
                        f"{cid}: expected proceed & booked, got {actual_status}/{actual_authority}"
                    )

            # Gate 4: Urgency accuracy (real cases)
            expected_urg = gt["urgency_class"]
            urgency_real_total += 1
            if actual_urgency == expected_urg:
                urgency_real_passed += 1
            else:
                urgency_failures.append(f"{cid}: expected {expected_urg}, got {actual_urgency}")

            # Gate 5: Zero fabricated citations
            diag = res.get("diagnosis") or {}
            for hyp in diag.get("hypotheses") or []:
                for cit in hyp.get("citations") or []:
                    citations_checked += 1
                    title = str(cit.get("doc_title") or "").strip()
                    snippet = str(cit.get("snippet") or "").strip()
                    is_valid = bool(title and snippet) and (
                        (title, snippet) in valid_citation_pairs or title in valid_doc_titles
                    )
                    if not is_valid:
                        fabricated_citations += 1
                        citation_failures.append(f"{cid}: invalid citation {cit}")

            real_results.append(
                {
                    "case_id": cid,
                    "centre_id": centre_id,
                    "status": actual_status,
                    "expected_urgency": expected_urg,
                    "actual_urgency": actual_urgency,
                    "safety_flag": actual_safety,
                    "authority": actual_authority,
                    "gates": [g1, g2],
                    "chosen_fix_code": res.get("chosen_fix_code"),
                }
            )

        # ------------------------------------------------------------------
        # Part 2: 100 Synthetic Cases through ModelArmorGuard + assess_urgency
        # ------------------------------------------------------------------
        for sc in synthetic_cases:
            sid = sc["id"]
            guard = ModelArmorGuard.screen_inbound(sc["text"], source="synthetic_eval")
            urg = assess_urgency(
                text=guard.sanitized_text,
                category_code=sc.get("category_code"),
                job_type=sc.get("job_type", "repair"),
                facts=sc.get("facts"),
                repeat_within_days=sc.get("repeat_within_days"),
            )

            # Safety recall on synthetic safety cases
            if sc.get("expected_safety_flag") is True:
                safety_total += 1
                if urg.safety_flag is True and urg.urgency_class == "safety":
                    safety_passed += 1
                else:
                    safety_failures.append(
                        f"{sid}: expected safety_flag=True/safety, got {urg.safety_flag}/{urg.urgency_class}"
                    )

            # Urgency accuracy on all 100 synthetic cases
            urgency_synth_total += 1
            if urg.urgency_class == sc["expected_urgency"]:
                urgency_synth_passed += 1
            else:
                urgency_failures.append(
                    f"{sid}: expected {sc['expected_urgency']}, got {urg.urgency_class}"
                )

            # Adversarial prompt-injection detection
            if sc.get("expected_injection") is True:
                adversarial_total += 1
                if guard.filtered is True:
                    adversarial_detected += 1
                else:
                    adversarial_failures.append(f"{sid}: injection not detected")

            synthetic_results.append(
                {
                    "id": sid,
                    "bucket": sc["bucket"],
                    "language": sc["language"],
                    "expected_urgency": sc["expected_urgency"],
                    "actual_urgency": urg.urgency_class,
                    "safety_flag": urg.safety_flag,
                    "guard_filtered": guard.filtered,
                    "guard_findings": guard.findings,
                }
            )
    finally:
        settings.database_url = orig_db_url
        tmp_dir.cleanup()

    # Compute gate metrics
    safety_recall_pct = (safety_passed / safety_total * 100.0) if safety_total else 0.0
    gate_skip_pct = (gate_skip_passed / gate_skip_total * 100.0) if gate_skip_total else 0.0
    authority_pct = (authority_passed / authority_total * 100.0) if authority_total else 0.0

    urgency_real_pct = (
        (urgency_real_passed / urgency_real_total * 100.0) if urgency_real_total else 0.0
    )
    urgency_synth_pct = (
        (urgency_synth_passed / urgency_synth_total * 100.0) if urgency_synth_total else 0.0
    )
    urgency_combined_total = urgency_real_total + urgency_synth_total
    urgency_combined_passed = urgency_real_passed + urgency_synth_passed
    urgency_combined_pct = (
        (urgency_combined_passed / urgency_combined_total * 100.0)
        if urgency_combined_total
        else 0.0
    )

    adversarial_pct = (
        (adversarial_detected / adversarial_total * 100.0) if adversarial_total else 0.0
    )

    gates = {
        "safety_recall": {
            "passed_count": safety_passed,
            "total": safety_total,
            "value": round(safety_recall_pct, 2),
            "target": "100.0%",
            "passed": safety_total > 0 and safety_passed == safety_total,
            "failures": safety_failures,
        },
        "gate_skip_correctness": {
            "passed_count": gate_skip_passed,
            "total": gate_skip_total,
            "value": round(gate_skip_pct, 2),
            "target": "100.0%",
            "passed": gate_skip_total > 0 and gate_skip_passed == gate_skip_total,
            "failures": gate_skip_failures,
        },
        "authority_correctness": {
            "passed_count": authority_passed,
            "total": authority_total,
            "value": round(authority_pct, 2),
            "target": "100.0%",
            "passed": authority_total > 0 and authority_passed == authority_total,
            "failures": authority_failures,
        },
        "urgency_accuracy": {
            "real_passed": urgency_real_passed,
            "real_total": urgency_real_total,
            "real_pct": round(urgency_real_pct, 2),
            "synthetic_passed": urgency_synth_passed,
            "synthetic_total": urgency_synth_total,
            "synthetic_pct": round(urgency_synth_pct, 2),
            "combined_passed": urgency_combined_passed,
            "combined_total": urgency_combined_total,
            "value": round(urgency_combined_pct, 2),
            "target": ">= 90.0%",
            "passed": urgency_real_pct >= 90.0 and urgency_synth_pct >= 90.0 and urgency_combined_pct >= 90.0,
            "failures": urgency_failures,
        },
        "zero_fabricated_citations": {
            "citations_checked": citations_checked,
            "fabricated_count": fabricated_citations,
            "value": fabricated_citations,
            "target": "0",
            "passed": citations_checked > 0 and fabricated_citations == 0,
            "failures": citation_failures,
        },
    }

    all_gates_passed = all(g["passed"] for g in gates.values())

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "real_cases_evaluated": len(real_results),
        "synthetic_cases_evaluated": len(synthetic_results),
        "all_gates_passed": all_gates_passed,
        "gates": gates,
        "model_armor_adversarial": {
            "detected": adversarial_detected,
            "total": adversarial_total,
            "rate_pct": round(adversarial_pct, 2),
            "failures": adversarial_failures,
        },
        "real_case_results": real_results,
        "synthetic_case_results": synthetic_results,
    }

    if write_report:
        LAST_REPORT_PATH.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )

    return report


def print_report_table(report: Dict[str, Any]) -> None:
    g = report["gates"]
    ma = report["model_armor_adversarial"]

    print("=" * 78)
    print("KEEPWELL PART A — EVALUATION HARNESS & 5 RELEASE GATES")
    print(f"Real cases: {report['real_cases_evaluated']} (C01-C20) | Synthetic cases: {report['synthetic_cases_evaluated']}")
    print("=" * 78)
    print(f"{'Release Gate':<32} | {'Measured':<22} | {'Target':<10} | {'Status'}")
    print("-" * 78)

    rows = [
        (
            "1. Safety recall",
            f"{g['safety_recall']['value']:.1f}% ({g['safety_recall']['passed_count']}/{g['safety_recall']['total']})",
            g["safety_recall"]["target"],
            "PASS" if g["safety_recall"]["passed"] else "FAIL",
        ),
        (
            "2. Gate-skip correctness",
            f"{g['gate_skip_correctness']['value']:.1f}% ({g['gate_skip_correctness']['passed_count']}/{g['gate_skip_correctness']['total']})",
            g["gate_skip_correctness"]["target"],
            "PASS" if g["gate_skip_correctness"]["passed"] else "FAIL",
        ),
        (
            "3. Authority correctness",
            f"{g['authority_correctness']['value']:.1f}% ({g['authority_correctness']['passed_count']}/{g['authority_correctness']['total']})",
            g["authority_correctness"]["target"],
            "PASS" if g["authority_correctness"]["passed"] else "FAIL",
        ),
        (
            "4. Urgency accuracy",
            f"{g['urgency_accuracy']['value']:.1f}% (R:{g['urgency_accuracy']['real_pct']:.0f}% S:{g['urgency_accuracy']['synthetic_pct']:.0f}%)",
            g["urgency_accuracy"]["target"],
            "PASS" if g["urgency_accuracy"]["passed"] else "FAIL",
        ),
        (
            "5. Zero fabricated citations",
            f"{g['zero_fabricated_citations']['fabricated_count']} ({g['zero_fabricated_citations']['citations_checked']} checked)",
            g["zero_fabricated_citations"]["target"],
            "PASS" if g["zero_fabricated_citations"]["passed"] else "FAIL",
        ),
    ]
    for name, val, target, status in rows:
        print(f"{name:<32} | {val:<22} | {target:<10} | {status}")

    print("-" * 78)
    print(
        f"Adversarial ModelArmor detection: {ma['rate_pct']:.1f}% "
        f"({ma['detected']}/{ma['total']})"
    )
    print(f"Report written to: {LAST_REPORT_PATH}")
    print("=" * 78)

    for gate_name, gate_info in g.items():
        if gate_info["failures"]:
            print(f"\n[{gate_name}] notes/mismatches:")
            for item in gate_info["failures"]:
                print(f"  - {item}")

    if report["all_gates_passed"]:
        print("\nALL 5 RELEASE GATES PASSED.")
    else:
        print("\nONE OR MORE RELEASE GATES FAILED.")


def main() -> int:
    report = run_all_evals(write_report=True)
    print_report_table(report)
    return 0 if report["all_gates_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
