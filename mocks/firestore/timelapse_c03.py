"""Real-time C03 time-lapse emitter for Firestore emulator (and optional REST mock).

Writes the full C03 stage story over ~25 seconds (configurable via `--delay`),
including:
- `centres/{cid}/conversations/{conv_id}` & `turns/{turn_id}`
- `centres/{cid}/feed/{event_id}` covering the Contract Section 8 live event catalogue
- Progressive updates to `centres/{cid}/tickets/{tid}` (triaging -> video -> rerun -> assigned -> quote -> paid -> closed)
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from mocks.firestore.seed_emulator import FirestoreRestClient, load_fixture


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_c03_sequence(c03: dict[str, Any]) -> list[dict[str, Any]]:
    cid = c03["centre_id"]
    tid = c03["ticket_id"]
    tech1 = c03["candidates"][0]
    tech2 = c03["candidates"][1]
    quote = c03["quote"]

    return [
        {"type": "conversation_started", "actor": "household", "title": "Inbound Hindi call from Sunita Sharma", "detail": c03["caller_number"], "payload": {"channel": "voice", "caller_masked": "+91 ••••• ••577"}, "turn": ("household", c03["opening_hi"], "hi", "speech")},
        {"type": "recording_notice_logged", "actor": "system", "title": "Recording notice played", "detail": "This call may be recorded to help your service centre.", "payload": {}},
        {"type": "household_identified", "actor": "agent", "title": f"Identified {c03['household_name']}", "detail": "Verified via call_line; known to Frost and Wave Service Point", "payload": {"household_id": c03["household_id"], "verified_via": "call_line", "known_to_this_centre": True}},
        {"type": "appliance_identified", "actor": "agent", "title": "Identified Wavecrest Front-Load Washer", "detail": "24-month warranty ended 22 days ago", "payload": {"brand": "Wavecrest", "source": "record"}},
        {"type": "authority_checked", "actor": "agent", "title": "Authority confirmed: authorised_service for Wavecrest", "detail": "Proceeding with repair triage", "payload": {"level": "authorised_service", "decision": "proceed"}},
        {"type": "clarifying_asked", "actor": "agent", "title": "Asked safety & symptom check", "detail": "Any burning smell, shock, or leaking near electrical socket?", "payload": {"seq": 1}, "turn": ("agent", "क्या मशीन से कोई जलने की बदबू या करंट आ रहा है?", "hi", "speech")},
        {"type": "clarifying_answered", "actor": "household", "title": "No electrical hazard reported", "detail": "Nothing unsafe; floor is wet only", "payload": {}, "turn": ("household", "नहीं, कुछ खतरनाक नहीं है, बस फर्श गीला है।", "hi", "speech")},
        {"type": "urgency_assessed", "actor": "agent", "title": "Urgency assessed: standard", "detail": "Rule STD-DEFAULT: no safety hazard or perishable loss", "payload": {"class": "standard", "rule_codes": ["STD-DEFAULT"]}},
        {"type": "gate_asked", "actor": "agent", "title": "Consent Gate 1 asked", "detail": "Are you okay to try a quick, safe fix yourself first?", "payload": {"gate": 1}, "turn": ("agent", "क्या आप पहले एक छोटा और सुरक्षित उपाय खुद आज़माना चाहेंगी?", "hi", "speech")},
        {"type": "gate_answered", "actor": "household", "title": "Gate 1 answered: yes", "detail": "Household agreed to try drain filter clean", "payload": {"gate": 1, "answer": "yes", "choice": None}, "turn": ("household", "जी हाँ, अगर आसान है तो ठीक है।", "hi", "speech")},
        {"type": "gate_asked", "actor": "agent", "title": "Consent Gate 2 asked", "detail": "Would you like to switch to video, or carry on here?", "payload": {"gate": 2}},
        {"type": "gate_answered", "actor": "household", "title": "Gate 2 answered: switch_to_video", "detail": "Magic video link sent on WhatsApp", "payload": {"gate": 2, "answer": "yes", "choice": "switch_to_video"}},
        {"type": "modality_changed", "actor": "household", "title": "Switched from voice to live video", "detail": "Same conversation resumed with camera", "payload": {"from": "voice", "to": "video"}, "conv_modality": "video"},
        {"type": "fix_offered", "actor": "agent", "title": f"Offered {c03['safe_fix_code']}: {c03['safe_fix_title']}", "detail": "6 reversible steps, ~10 min", "payload": {"code": c03["safe_fix_code"], "steps": 6, "est_minutes": 10}},
        {"type": "fix_step", "actor": "agent", "title": "Step 6 of 6 completed on video", "detail": "Cleared coins, hair-clips, and lint from drain filter", "payload": {"n": 6, "of": 6}},
        {"type": "fix_result", "actor": "household", "title": "Safe fix outcome: not_worked", "detail": "Water drained partly, then E21 returned", "payload": {"outcome": "not_worked", "household_report": "E21 returned after drain cycle"}},
        {"type": "diagnosis_updated", "actor": "agent", "title": "Diagnosis re-run: drain pump impeller jammed (86%)", "detail": f"Added {c03['part_no']} ({c03['part_name']}) to visit plan", "payload": {"top_hypothesis": "wm_drain_pump_jam", "probability": 0.86, "rerun": True}},
        {"type": "visit_plan_ready", "actor": "agent", "title": f"Visit plan v2 ready ({c03['part_no']} in centre stock)", "detail": "Already tried: SF-WM-DRAINFILTER-WC", "payload": {"already_tried": [c03["safe_fix_code"]]}},
        {"type": "candidates_scored", "actor": "agent", "title": f"6-factor ranking: #1 {tech1['name']} (89.5)", "detail": "fix_confidence 27.5, parts_readiness 23.0, time_to_visit 17.5", "payload": {"top_3": c03["candidates"]}},
        {"type": "slots_offered", "actor": "agent", "title": "Offered 14:00-16:00 slot (₹1,000 - ₹2,235)", "detail": "Household accepted afternoon slot", "payload": {"window": "14:00-16:00"}},
        {"type": "technician_assigned", "actor": "agent", "title": f"Assigned {tech1['name']} for 14:00-16:00", "detail": "Chosen by agent", "payload": {"name": tech1["name"], "chosen_by": "agent"}, "ticket_status": "assigned", "assignee": tech1},
        {"type": "reassigned", "actor": "centre", "title": f"Centre reassigned from {tech1['name']} to {tech2['name']}", "detail": "Logged as training override", "payload": {"from": tech1["name"], "to": tech2["name"], "reason": "Earlier job overran"}, "assignee": tech2},
        {"type": "quote_issued", "actor": "technician", "title": f"Firm quote issued (₹{quote['total_paise'] / 100:.2f})", "detail": "Includes WC-WM-DPUMP + labour + visit fee", "payload": {"type": "firm", "total_paise": quote["total_paise"]}},
        {"type": "quote_approved", "actor": "household", "title": "Household approved firm quote via magic link", "detail": f"₹{quote['total_paise'] / 100:.2f}", "payload": {}},
        {"type": "payment_initiated", "actor": "household", "title": "Payment initiated via Google Pay", "detail": f"₹{quote['total_paise'] / 100:.2f}", "payload": {"method": "google_pay", "amount_paise": quote["total_paise"]}, "payment_status": "pending"},
        {"type": "payment_confirmed", "actor": "system", "title": "Payment confirmed (SANDBOX-C03-OK)", "detail": "Payment does not close ticket; awaiting household OTP", "payload": {"payment_ref": "SANDBOX-C03-OK"}, "payment_status": "paid"},
        {"type": "debrief_processed", "actor": "agent", "title": "Voice debrief extracted (1 unresolved part flagged)", "detail": "rubber gasket ring marked needs checking", "payload": {"unresolved_count": 1}},
        {"type": "otp_sent", "actor": "system", "title": "Closure OTP sent to household", "detail": "Awaiting 6-digit confirmation code", "payload": {}},
        {"type": "ticket_closed", "actor": "household", "title": "Ticket closed by household OTP", "detail": "Resolution: visit (first-time fix)", "payload": {"resolution": "visit"}, "ticket_status": "closed"},
    ]


def run_timelapse(
    delay: float = 0.85,
    host: str | None = None,
    project_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    client = FirestoreRestClient(host=host, project_id=project_id, dry_run=dry_run)
    c03 = load_fixture("c03_script.json")
    cid = c03["centre_id"]
    tid = c03["ticket_id"]
    conv_id = f"conv_c03_{uuid.uuid4().hex[:8]}"

    client.set_doc(f"centres/{cid}/conversations/{conv_id}", {
        "ticket_id": tid,
        "channel": "voice",
        "modality": "voice",
        "language": "hi",
        "started_at": utc_now(),
        "ended_at": None,
        "recording_notice_logged": True,
        "state": "active",
        "caller_masked": "+91 ••••• ••577",
    })

    steps = build_c03_sequence(c03)
    for idx, step in enumerate(steps, start=1):
        at = utc_now()
        ev_id = f"c03_tl_{idx:02d}"
        client.set_doc(f"centres/{cid}/feed/{ev_id}", {
            "id": ev_id,
            "at": at,
            "centre_id": cid,
            "ticket_id": tid,
            "conversation_id": conv_id,
            "type": step["type"],
            "actor": step["actor"],
            "title": step["title"],
            "detail": step["detail"],
            "payload": step.get("payload", {}),
        })

        if "turn" in step:
            speaker, text, lang, kind = step["turn"]
            client.set_doc(f"centres/{cid}/conversations/{conv_id}/turns/turn_{idx:02d}", {
                "at": at,
                "speaker": speaker,
                "text": text,
                "lang": lang,
                "final": True,
                "kind": kind,
            })

        if "conv_modality" in step:
            client.set_doc(f"centres/{cid}/conversations/{conv_id}", {
                "ticket_id": tid,
                "channel": "voice",
                "modality": step["conv_modality"],
                "language": "hi",
                "started_at": at,
                "ended_at": None,
                "recording_notice_logged": True,
                "state": "active",
                "caller_masked": "+91 ••••• ••577",
            })

        if "ticket_status" in step or "payment_status" in step or "assignee" in step:
            patch: dict[str, Any] = {"last_event_at": at, "updated_at": at}
            if "ticket_status" in step:
                patch["status"] = step["ticket_status"]
            if "payment_status" in step:
                patch["payment_status"] = step["payment_status"]
            if "assignee" in step:
                patch["assignee"] = {
                    "technician_id": step["assignee"]["technician_id"],
                    "name": step["assignee"]["name"],
                }
            client.set_doc(f"centres/{cid}/tickets/{tid}", patch)

        if delay > 0 and not dry_run:
            time.sleep(delay)

    return {"conversation_id": conv_id, "events_emitted": len(steps), "total_writes": client.writes}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run C03 real-time time-lapse into Firestore emulator.")
    parser.add_argument("--delay", type=float, default=0.85, help="Seconds between events (default 0.85s -> ~25s total)")
    parser.add_argument("--host", default=None, help="Firestore emulator host:port")
    parser.add_argument("--project", default=None, help="Firebase project ID")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without HTTP calls")
    args = parser.parse_args()

    res = run_timelapse(delay=args.delay, host=args.host, project_id=args.project, dry_run=args.dry_run)
    print("C03 timelapse complete:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
