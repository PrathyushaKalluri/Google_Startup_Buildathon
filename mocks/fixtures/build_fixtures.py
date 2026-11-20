"""Build normalized JSON fixtures for Keepwell Part B mocks from the real simulation dataset.

Auto-detects `input/dataset/` (or `keepwell/input/dataset/`) or falls back to
`keepwell/docs_v1/keepwell_sim_dataset_v0.2.zip`.
Writes normalized JSON files into `mocks/fixtures/generated/`.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "generated"

# Canonical centre key order from SHARED_CONTRACT.md Section 3
CENTRE_KEY_ORDER = [
    "c_av", "c_zn", "c_fw", "c_cc", "c_aq", "c_mh", "c_ip", "c_ls", "c_hw"
]

# Brand & retailer case -> receiving centre key mapping (matches dataset world)
BRAND_RETAILER_CENTRE_MAP = {
    "C07": "c_ip",  # InstallPro Mounting Services (retailer AC installation)
    "C17": "c_zn",  # Zenith Care Hub (Zenith authorised)
    "C18": "c_cc",  # Cool Craft Appliance Services (independent for Aerovane -> authority declined)
    "C19": "c_hw",  # Heatwell Authorised Service (Heatwell authorised)
    "C20": "c_fw",  # Frost and Wave Service Point (Wavecrest authorised installation)
}

URGENCY_META = {
    "C01": ("standard", False, None, "repair"),
    "C02": ("standard", False, None, "repair"),
    "C03": ("standard", False, None, "repair"),
    "C04": ("planned", False, None, "preventive_service"),
    "C05": ("safety", True, "Electric shock / current leakage reported on water heater body", "repair"),
    "C06": ("urgent", False, None, "repair"),
    "C07": ("planned", False, None, "installation"),
    "C08": ("planned", False, None, "preventive_service"),
    "C09": ("standard", False, None, "repair"),
    "C10": ("standard", False, None, "repair"),
    "C11": ("standard", False, None, "repair"),
    "C12": ("urgent", False, None, "repair"),
    "C13": ("standard", False, None, "repair"),
    "C14": ("standard", False, None, "repair"),
    "C15": ("safety", True, "Smoke and burning smell from washing machine motor", "repair"),
    "C16": ("standard", False, None, "repair"),
    "C17": ("standard", False, None, "repair"),
    "C18": ("standard", False, None, "repair"),
    "C19": ("standard", False, None, "repair"),
    "C20": ("planned", False, None, "installation"),
}


class DatasetReader:
    """Reads CSVs and JSONs from either an extracted directory or the dataset zip."""

    def __init__(self) -> None:
        self.dir_path: Path | None = None
        self.zip_file: zipfile.ZipFile | None = None
        self.zip_prefix: str = ""

        candidates = [
            REPO_ROOT / "input" / "dataset",
            REPO_ROOT / "keepwell" / "input" / "dataset",
        ]
        for cand in candidates:
            if (cand / "csv" / "service_centre.csv").exists():
                self.dir_path = cand
                break

        if self.dir_path is None:
            zip_candidates = [
                REPO_ROOT / "keepwell" / "docs_v1" / "keepwell_sim_dataset_v0.2.zip",
                REPO_ROOT / "input" / "keepwell_sim_dataset_v0.2.zip",
            ]
            for zc in zip_candidates:
                if zc.exists():
                    self.zip_file = zipfile.ZipFile(zc, "r")
                    names = self.zip_file.namelist()
                    for n in names:
                        if n.endswith("csv/service_centre.csv"):
                            self.zip_prefix = n[: -len("csv/service_centre.csv")]
                            break
                    break

        if self.dir_path is None and self.zip_file is None:
            raise FileNotFoundError(
                "Could not locate input/dataset/ or keepwell/docs_v1/keepwell_sim_dataset_v0.2.zip"
            )

    def source_description(self) -> str:
        if self.dir_path is not None:
            return str(self.dir_path)
        assert self.zip_file is not None
        return str(self.zip_file.filename)

    def read_text(self, rel_path: str) -> str:
        if self.dir_path is not None:
            return (self.dir_path / rel_path).read_text(encoding="utf-8")
        assert self.zip_file is not None
        return self.zip_file.read(self.zip_prefix + rel_path).decode("utf-8")

    def exists(self, rel_path: str) -> bool:
        if self.dir_path is not None:
            return (self.dir_path / rel_path).exists()
        assert self.zip_file is not None
        return (self.zip_prefix + rel_path) in self.zip_file.namelist()

    def read_csv(self, name: str) -> list[dict[str, str]]:
        text = self.read_text(f"csv/{name}")
        rows: list[dict[str, str]] = []
        for row in csv.DictReader(io.StringIO(text)):
            cleaned = {k: ("" if v == "\\N" else v) for k, v in row.items()}
            rows.append(cleaned)
        return rows

    def read_json(self, rel_path: str) -> Any:
        return json.loads(self.read_text(rel_path))


def parse_pg_array(val: str) -> list[str]:
    if not val or val == "{}":
        return []
    inner = val.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1]
    if not inner:
        return []
    return [item.strip().strip('"') for item in inner.split(",") if item.strip()]


def parse_point(val: str) -> dict[str, float] | None:
    if not val:
        return None
    m = re.search(r"POINT\(([-0-9.]+)\s+([-0-9.]+)\)", val)
    if not m:
        return None
    return {"lon": float(m.group(1)), "lat": float(m.group(2))}


def mask_serial(serial: str | None) -> str | None:
    if not serial:
        return None
    if len(serial) <= 4:
        return "****"
    return serial[:4] + "****" + serial[-3:]


def mask_phone(phone: str | None) -> str:
    if not phone:
        return "+91 ••••• ••000"
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 4:
        return f"+91 ••••• ••{digits[-3:]}"
    return "+91 ••••• ••000"


def stable_uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"keepwell.mock.{seed}"))


def magic_token_for(household_id: str) -> str:
    digest = hashlib.sha256(f"kw-magic-{household_id}".encode()).hexdigest()[:16]
    return f"kwm_{digest}"


def extract_locality(address_line: str) -> str:
    parts = [p.strip() for p in address_line.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else "Hyderabad"


def build_all() -> dict[str, Any]:
    ds = DatasetReader()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Core reference tables
    brands_rows = ds.read_csv("brand.csv")
    brands_by_id = {r["id"]: r for r in brands_rows}
    brands_by_name_lower = {r["name"].lower(): r for r in brands_rows}

    retailers_rows = ds.read_csv("retailer.csv")
    centres_rows = ds.read_csv("service_centre.csv")
    channels_rows = ds.read_csv("centre_channel.csv")
    auth_rows = ds.read_csv("centre_brand_authorisation.csv")

    # Map centre_id <-> centre_key from centre_channel.provider_ref (e.g. tel-c_fw -> c_fw)
    centre_id_to_key: dict[str, str] = {}
    centre_key_to_id: dict[str, str] = {}
    number_to_centre_id: dict[str, str] = {}
    channels_by_centre: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for ch in channels_rows:
        cid = ch["centre_id"]
        pref = ch["provider_ref"]
        if "-" in pref:
            ckey = pref.split("-", 1)[1]
            centre_id_to_key[cid] = ckey
            centre_key_to_id[ckey] = cid
        number_to_centre_id[ch["number_ref"]] = cid
        channels_by_centre[cid].append({
            "id": ch["id"],
            "channel": ch["channel"],
            "number_ref": ch["number_ref"],
            "provider_ref": ch["provider_ref"],
            "status": ch["status"],
        })

    auth_by_centre: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in auth_rows:
        bname = brands_by_id.get(a["brand_id"], {}).get("name", "Unknown")
        auth_by_centre[a["centre_id"]].append({
            "brand_id": a["brand_id"],
            "brand": bname,
            "level": a["level"],
            "valid_from": a["valid_from"],
            "valid_to": a["valid_to"] or None,
        })

    centres: list[dict[str, Any]] = []
    centres_by_id: dict[str, dict[str, Any]] = {}
    for c in centres_rows:
        cid = c["id"]
        ckey = centre_id_to_key.get(cid, cid[:6])
        obj = {
            "id": cid,
            "centre_key": ckey,
            "name": c["name"],
            "address_line": c["address_line"],
            "pincode": c["pincode"],
            "location": parse_point(c["location"]),
            "service_pincodes": parse_pg_array(c["service_pincodes"]),
            "categories": parse_pg_array(c["categories"]),
            "default_language": c["default_language"],
            "onboarding_status": c["onboarding_status"],
            "channels": channels_by_centre[cid],
            "authorisations": auth_by_centre[cid],
        }
        centres.append(obj)
        centres_by_id[cid] = obj

    centres.sort(key=lambda x: CENTRE_KEY_ORDER.index(x["centre_key"]) if x["centre_key"] in CENTRE_KEY_ORDER else 99)

    # 2. Technicians
    tech_rows = ds.read_csv("technician.csv")
    tech_skill_rows = ds.read_csv("technician_skill.csv")
    tech_metric_rows = ds.read_csv("technician_metrics.csv")

    skills_by_tech: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in tech_skill_rows:
        skills_by_tech[s["technician_id"]].append({
            "brand": brands_by_id.get(s["brand_id"], {}).get("name", "Generic"),
            "category_code": s["category_code"],
            "fault_class": s["fault_class"],
            "level": int(s["level"] or 1),
        })

    metrics_by_tech: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in tech_metric_rows:
        metrics_by_tech[m["technician_id"]].append({
            "category_code": m["category_code"],
            "jobs": int(m["jobs"] or 0),
            "first_time_fix_rate": float(m["first_time_fix_rate"] or 0.8),
            "on_time_rate": float(m["on_time_rate"] or 0.85),
            "repeat_visit_rate_30d": float(m["repeat_visit_rate_30d"] or 0.08),
        })

    technicians: list[dict[str, Any]] = []
    techs_by_centre: dict[str, list[dict[str, Any]]] = defaultdict(list)
    techs_by_id: dict[str, dict[str, Any]] = {}

    for idx, t in enumerate(tech_rows):
        tid = t["id"]
        cid = t["centre_id"]
        m_list = metrics_by_tech.get(tid, [])
        avg_ftf = round(sum(x["first_time_fix_rate"] for x in m_list) / len(m_list), 3) if m_list else 0.84
        avg_ot = round(sum(x["on_time_rate"] for x in m_list) / len(m_list), 3) if m_list else 0.88
        statuses = ["available", "on_job", "travelling", "available"]
        obj = {
            "id": tid,
            "centre_id": cid,
            "centre_key": centre_id_to_key.get(cid, ""),
            "name": t["name"],
            "languages": parse_pg_array(t["languages"]),
            "shift_start": t["shift_start"],
            "shift_end": t["shift_end"],
            "vehicle_type": t["vehicle_type"],
            "safety_certs": parse_pg_array(t["safety_certs"]),
            "active": t["active"] == "t",
            "status": statuses[idx % len(statuses)],
            "last_location": parse_point(t["route_anchor"]),
            "last_ping_at": "2026-11-21T08:15:00+05:30",
            "skills": skills_by_tech.get(tid, [])[:8],
            "metrics": {
                "first_time_fix_rate": avg_ftf,
                "on_time_rate": avg_ot,
                "jobs_completed": sum(x["jobs"] for x in m_list),
            },
        }
        technicians.append(obj)
        techs_by_centre[cid].append(obj)
        techs_by_id[tid] = obj

    # 3. Households & Members
    hh_rows = ds.read_csv("household.csv")
    hh_member_rows = ds.read_csv("household_member.csv")
    hh_link_rows = ds.read_csv("household_centre_link.csv")

    members_by_hh: dict[str, list[dict[str, str]]] = defaultdict(list)
    for m in hh_member_rows:
        members_by_hh[m["household_id"]].append(m)

    links_by_hh: dict[str, list[str]] = defaultdict(list)
    for lk in hh_link_rows:
        links_by_hh[lk["household_id"]].append(lk["centre_id"])

    households_by_id: dict[str, dict[str, Any]] = {}
    households_by_name_lower: dict[str, dict[str, Any]] = {}
    households: list[dict[str, Any]] = []

    for h in hh_rows:
        hid = h["id"]
        mems = members_by_hh.get(hid, [])
        owner = next((m for m in mems if m["role"] == "owner"), mems[0] if mems else None)
        display_name = owner["name"] if owner else f"Household {hid[:6]}"
        linked_centres = list(dict.fromkeys(links_by_hh.get(hid, [])))
        obj = {
            "id": hid,
            "display_name": display_name,
            "language": h["language"] or "en",
            "pincode": h["pincode"],
            "locality": extract_locality(h["address_line"]),
            "address_line": h["address_line"],
            "verified_via": h["verified_via"] or "call_line",
            "linked_centres_count": max(1, len(linked_centres)),
            "linked_centre_ids": linked_centres,
            "access_notes": h["access_notes"] or "Gate security requires visitor entry",
            "magic_token": magic_token_for(hid),
            "phone_masked": f"+91 ••••• ••{int(hashlib.md5(hid.encode()).hexdigest()[:4], 16) % 900 + 100}",
        }
        households.append(obj)
        households_by_id[hid] = obj
        households_by_name_lower[display_name.lower()] = obj

    # 4. Appliances & Models & Events
    model_rows = ds.read_csv("appliance_model.csv")
    models_by_id = {m["id"]: m for m in model_rows}
    app_rows = ds.read_csv("appliance.csv")
    app_event_rows = ds.read_csv("appliance_event.csv")

    events_by_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in app_event_rows:
        details = {}
        if ev["details"]:
            try:
                details = json.loads(ev["details"])
            except Exception:
                details = {"note": ev["details"]}
        events_by_app[ev["appliance_id"]].append({
            "at": ev["occurred_at"],
            "type": ev["event_type"],
            "actor": "centre" if ev["centre_id"] else "system",
            "title": f"{ev['event_type'].replace('_', ' ').title()}",
            "detail": json.dumps(details) if details else "",
            "ref": ev["ticket_id"] or ev["id"],
        })

    appliances_by_id: dict[str, dict[str, Any]] = {}
    appliances_by_hh: dict[str, list[dict[str, Any]]] = defaultdict(list)
    appliances: list[dict[str, Any]] = []

    for a in app_rows:
        aid = a["id"]
        brand_name = brands_by_id.get(a["brand_id"], {}).get("name", "Unknown")
        model_code = models_by_id.get(a["model_id"], {}).get("model_code") or (a["model_text"] or None)
        ref = {
            "id": aid,
            "household_id": a["household_id"],
            "brand": brand_name,
            "brand_id": a["brand_id"],
            "category_code": a["category_code"],
            "model_id": a["model_id"] or None,
            "model_code": model_code,
            "serial_masked": mask_serial(a["serial_no"]),
            "identity_status": a["identity_status"] or "verified",
            "purchase_date": a["purchase_date"] or None,
            "warranty_end": a["warranty_end"] or None,
            "next_due_at": a["next_due_at"] or None,
            "room": a["room"] or None,
            "timeline": sorted(events_by_app.get(aid, []), key=lambda x: x["at"]),
        }
        appliances.append(ref)
        appliances_by_id[aid] = ref
        appliances_by_hh[a["household_id"]].append(ref)

    def make_hh_ref(h: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": h["id"],
            "display_name": h["display_name"],
            "language": h["language"],
            "pincode": h["pincode"],
            "locality": h["locality"],
            "address_line": h["address_line"],
            "verified_via": h["verified_via"],
            "linked_centres_count": h["linked_centres_count"],
        }

    def make_app_ref(a: dict[str, Any] | None) -> dict[str, Any] | None:
        if not a:
            return None
        return {
            "id": a["id"],
            "brand": a["brand"],
            "category_code": a["category_code"],
            "model_code": a["model_code"],
            "serial_masked": a["serial_masked"],
            "identity_status": a["identity_status"],
            "purchase_date": a["purchase_date"],
            "warranty_end": a["warranty_end"],
        }

    # 5. Safe Fix Catalogue + effectiveness from fix_attempt.csv
    sf_rows = ds.read_csv("safe_fix_catalogue.csv")
    fa_rows = ds.read_csv("fix_attempt.csv")
    fa_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"offered": 0, "worked": 0, "not_worked": 0})
    for fa in fa_rows:
        cid_sf = fa["catalogue_id"]
        fa_stats[cid_sf]["offered"] += 1
        if fa["outcome"] == "worked":
            fa_stats[cid_sf]["worked"] += 1
        elif fa["outcome"] == "not_worked":
            fa_stats[cid_sf]["not_worked"] += 1

    safefix_list: list[dict[str, Any]] = []
    safefix_by_code: dict[str, dict[str, Any]] = {}
    for sf in sf_rows:
        st = fa_stats[sf["id"]]
        eff = round(st["worked"] / st["offered"], 2) if st["offered"] else 0.42
        steps = json.loads(sf["steps"]) if sf["steps"] else []
        obj = {
            "id": sf["id"],
            "code": sf["code"],
            "category_code": sf["category_code"],
            "brand": brands_by_id.get(sf["brand_id"], {}).get("name") if sf["brand_id"] else None,
            "fault_family": sf["fault_family"],
            "title": sf["title"],
            "symptom_terms": parse_pg_array(sf["symptom_terms"]),
            "steps": steps,
            "step_count": int(sf["step_count"] or len(steps)),
            "est_minutes": int(sf["est_minutes"] or 10),
            "reversible": sf["reversible"] == "t",
            "needs_tools": sf["needs_tools"] == "t",
            "opens_panel": sf["opens_panel"] == "t",
            "worst_case": sf["worst_case"],
            "reviewer_name": sf["reviewer_name"],
            "status": sf["status"],
            "effectiveness": {
                "offered_count": st["offered"],
                "worked_count": st["worked"],
                "resolution_rate": eff,
            },
        }
        safefix_list.append(obj)
        safefix_by_code[sf["code"]] = obj

    # 6. Parts, Stock, Prices, Parts Centres, Reservations
    part_rows = ds.read_csv("part_catalogue.csv")
    compat_rows = ds.read_csv("part_compatibility.csv")
    stock_rows = ds.read_csv("stock.csv")
    price_rows = ds.read_csv("centre_price.csv")
    pc_rows = ds.read_csv("parts_centre.csv")
    res_rows = ds.read_csv("reservation.csv")

    parts_by_id = {p["id"]: p for p in part_rows}
    parts_by_no = {p["part_no"]: p for p in part_rows}
    compat_by_model: dict[str, list[str]] = defaultdict(list)
    for cm in compat_rows:
        compat_by_model[cm["model_id"]].append(cm["part_id"])

    parts_centres = [
        {
            "id": pc["id"],
            "name": pc["name"],
            "address_line": pc["address_line"],
            "pincode": pc["pincode"],
            "location": parse_point(pc["location"]),
            "pickup_supported": pc["pickup_supported"] == "t",
            "delivery_supported": pc["delivery_supported"] == "t",
            "fill_rate": float(pc["fill_rate"] or 0.8),
            "stock_accuracy": float(pc["stock_accuracy"] or 0.75),
        }
        for pc in pc_rows
    ]

    stock_items: list[dict[str, Any]] = []
    for st in stock_rows:
        p = parts_by_id.get(st["part_id"], {})
        stock_items.append({
            "id": st["id"],
            "holder_type": st["holder_type"],
            "holder_id": st["holder_id"],
            "centre_id": st["centre_id"] or None,
            "part_id": st["part_id"],
            "part_no": p.get("part_no", ""),
            "part_name": p.get("name", ""),
            "brand": brands_by_id.get(p.get("brand_id", ""), {}).get("name", ""),
            "mrp_paise": int(p.get("mrp_paise") or 0),
            "quantity": int(st["quantity"] or 0),
            "confidence": float(st["confidence"] or 0.8),
            "as_of": st["as_of"],
        })

    centre_prices = [
        {
            "id": pr["id"],
            "centre_id": pr["centre_id"],
            "centre_key": centre_id_to_key.get(pr["centre_id"], ""),
            "category_code": pr["category_code"],
            "job_type": pr["job_type"],
            "complexity_band": pr["complexity_band"],
            "visit_fee_paise": int(pr["visit_fee_paise"] or 0),
            "labour_paise": int(pr["labour_paise"] or 0),
            "valid_from": pr["valid_from"],
            "valid_to": pr["valid_to"] or None,
        }
        for pr in price_rows
    ]

    parts_requests: list[dict[str, Any]] = []
    status_map = {"confirmed": "accepted", "pending": "requested", "ready": "ready", "picked_up": "handed_over"}
    for r in res_rows:
        p = parts_by_id.get(r["part_id"], {})
        parts_requests.append({
            "id": r["id"],
            "centre_id": r["centre_id"],
            "visit_id": r["visit_id"],
            "part_id": r["part_id"],
            "part_no": p.get("part_no", ""),
            "part_name": p.get("name", ""),
            "quantity": int(r["quantity"] or 1),
            "status": status_map.get(r["status"], "requested"),
            "parts_centre_id": r["holder_id"],
            "ready_by": r["ready_by"],
            "created_at": r["created_at"],
        })

    # 7. Build 20 inbox cases as full TicketDetail objects across the 9 centres
    inbox = ds.read_json("inbox/inbox.json")
    voice_scripts = ds.read_json("evaluator_only/voice_scripts.json") if ds.exists("evaluator_only/voice_scripts.json") else {}

    tickets: list[dict[str, Any]] = []
    demo_cases: list[dict[str, Any]] = []
    whatsapp_threads: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_payments: list[dict[str, Any]] = []

    # Payment states to guarantee across the seeded dataset
    payment_states_cycle = ["created", "pending", "paid", "failed", "expired"]

    for idx, item in enumerate(inbox):
        case_id = item["case_id"]
        trigger = item["trigger"]
        channel = item["channel"]

        # Resolve receiving centre
        if item.get("to_number") and item["to_number"] in number_to_centre_id:
            centre_id = number_to_centre_id[item["to_number"]]
        else:
            ckey_mapped = BRAND_RETAILER_CENTRE_MAP.get(case_id, "c_fw")
            centre_id = centre_key_to_id[ckey_mapped]
        centre_key = centre_id_to_key[centre_id]

        # Resolve household
        sender_name = item.get("sender_profile_name")
        if not sender_name and isinstance(item.get("payload"), dict):
            sender_name = item["payload"].get("customer", {}).get("name")
        hh = None
        if sender_name:
            hh = households_by_name_lower.get(sender_name.lower())
        if hh is None:
            # Pick a real household linked to this centre
            linked_hhs = [h for h in households if centre_id in h["linked_centre_ids"]]
            hh = linked_hhs[idx % len(linked_hhs)] if linked_hhs else households[idx % len(households)]

        # Resolve appliance for this household
        hh_apps = appliances_by_hh.get(hh["id"], [])
        app = hh_apps[0] if hh_apps else None
        if case_id == "C03":
            # Prefer Wavecrest washer if present
            wc_wash = next((a for a in hh_apps if a["category_code"] == "washing_machine"), None)
            if wc_wash:
                app = wc_wash

        # Extract complaint text
        complaint_summary = ""
        if trigger in ("brand_forward", "retailer_handover"):
            pl = item.get("payload", {})
            complaint_summary = pl.get("complaint") or pl.get("notes") or f"{pl.get('requested_job', 'Service')} request"
        else:
            msgs = item.get("messages", [])
            texts = []
            for m in msgs:
                if m.get("type") == "text":
                    texts.append(m.get("text", {}).get("body", ""))
                elif m.get("type") == "call":
                    rec_file = m.get("call", {}).get("recording", {}).get("file", "")
                    vs = voice_scripts.get(rec_file, {})
                    if vs.get("transcript_original_script"):
                        texts.append(vs["transcript_original_script"])
                elif m.get("type") == "audio":
                    aud_file = m.get("audio", {}).get("file", "")
                    vs = voice_scripts.get(aud_file, {})
                    if vs.get("transcript_original_script"):
                        texts.append(vs["transcript_original_script"])
            complaint_summary = " ".join(t for t in texts if t).strip() or f"Service request for {case_id}"

        urgency_class, safety_flag, safety_reason, job_type = URGENCY_META.get(
            case_id, ("standard", False, None, "repair")
        )

        ticket_id = stable_uuid(f"ticket-{case_id}")
        created_at = f"2026-11-21T07:{10 + idx:02d}:00+05:30"
        updated_at = f"2026-11-21T08:{10 + idx:02d}:00+05:30"
        needed_by = (
            f"2026-11-21T10:{0 + idx:02d}:00+05:30"
            if urgency_class in ("safety", "urgent")
            else f"2026-11-22T12:{0 + idx:02d}:00+05:30"
        )

        # Authority
        app_brand = app["brand"] if app else "Wavecrest"
        centre_auths = auth_by_centre.get(centre_id, [])
        matching_auth = next((a for a in centre_auths if a["brand"].lower() == app_brand.lower()), None)
        auth_level = matching_auth["level"] if matching_auth else "independent"
        auth_decision = "declined" if case_id == "C18" else "proceed"

        # Technicians for this centre
        c_techs = techs_by_centre.get(centre_id, technicians[:3])
        primary_tech = c_techs[0]
        alt_tech = c_techs[1] if len(c_techs) > 1 else c_techs[0]
        third_tech = c_techs[2] if len(c_techs) > 2 else alt_tech

        # Parts (strictly from part_catalogue!)
        compat_part_ids = compat_by_model.get(app["model_id"], []) if app and app.get("model_id") else []
        if case_id == "C03" and "WC-WM-DPUMP" in parts_by_no:
            chosen_part = parts_by_no["WC-WM-DPUMP"]
        elif compat_part_ids and compat_part_ids[0] in parts_by_id:
            chosen_part = parts_by_id[compat_part_ids[0]]
        else:
            chosen_part = part_rows[idx % len(part_rows)]

        part_mrp = int(chosen_part["mrp_paise"] or 45000)

        # Gates & Fix attempts
        if safety_flag:
            gates = [
                {"gate": 1, "asked_at": None, "answer": "not_asked", "choice": None, "not_asked_reason": "safety_case"},
                {"gate": 2, "asked_at": None, "answer": "not_asked", "choice": None, "not_asked_reason": "safety_case"},
            ]
            fix_attempts = []
        elif job_type != "repair":
            gates = [
                {"gate": 1, "asked_at": None, "answer": "not_asked", "choice": None, "not_asked_reason": "non_repair_job"},
                {"gate": 2, "asked_at": None, "answer": "not_asked", "choice": None, "not_asked_reason": "non_repair_job"},
            ]
            fix_attempts = []
        elif case_id == "C03":
            sf_wc = safefix_by_code.get("SF-WM-DRAINFILTER-WC", safefix_list[0])
            gates = [
                {"gate": 1, "asked_at": "2026-11-21T07:27:10+05:30", "answer": "yes", "choice": None, "not_asked_reason": None},
                {"gate": 2, "asked_at": "2026-11-21T07:27:35+05:30", "answer": "yes", "choice": "switch_to_video", "not_asked_reason": None},
            ]
            fix_attempts = [
                {
                    "id": stable_uuid("fix-C03"),
                    "catalogue_code": sf_wc["code"],
                    "title": sf_wc["title"],
                    "offered_at": "2026-11-21T07:28:15+05:30",
                    "steps_done": 6,
                    "of": sf_wc["step_count"],
                    "outcome": "not_worked",
                    "household_report": "Cleaned coins, hair-clips and lint from drain filter; water drained partly, then E21 returned.",
                    "observed_on_video": True,
                }
            ]
        else:
            gates = [
                {"gate": 1, "asked_at": created_at, "answer": "yes" if idx % 2 == 0 else "no", "choice": None, "not_asked_reason": None},
            ]
            fix_attempts = []

        # Candidates with 6-factor score_breakdown (weights: 30, 25, 20, 15, 5, 5)
        slot_start = "2026-11-21T14:00:00+05:30"
        slot_end = "2026-11-21T16:00:00+05:30"
        candidates = [
            {
                "technician_id": primary_tech["id"],
                "name": primary_tech["name"],
                "rank": 1,
                "score": 89.5,
                "score_breakdown": {
                    "fix_confidence": 27.5,
                    "parts_readiness": 23.0,
                    "time_to_visit": 17.5,
                    "route_cost": 12.5,
                    "reliability": 4.5,
                    "household_fit": 4.5,
                },
                "slot_start": slot_start,
                "slot_end": slot_end,
                "outcome": "chosen",
                "chosen_by": "agent",
                "override_reason": None,
                "why": f"Highest fix confidence for {app_brand} with part available at centre and matching language.",
            },
            {
                "technician_id": alt_tech["id"],
                "name": alt_tech["name"],
                "rank": 2,
                "score": 81.0,
                "score_breakdown": {
                    "fix_confidence": 24.0,
                    "parts_readiness": 21.0,
                    "time_to_visit": 16.0,
                    "route_cost": 11.5,
                    "reliability": 4.5,
                    "household_fit": 4.0,
                },
                "slot_start": "2026-11-21T16:00:00+05:30",
                "slot_end": "2026-11-21T18:00:00+05:30",
                "outcome": "not_chosen",
                "chosen_by": "agent",
                "override_reason": None,
                "why": "Later slot window and slightly lower historical FTF on this fault family.",
            },
            {
                "technician_id": third_tech["id"],
                "name": third_tech["name"],
                "rank": 3,
                "score": 74.5,
                "score_breakdown": {
                    "fix_confidence": 21.5,
                    "parts_readiness": 19.0,
                    "time_to_visit": 15.0,
                    "route_cost": 11.0,
                    "reliability": 4.0,
                    "household_fit": 4.0,
                },
                "slot_start": "2026-11-22T10:00:00+05:30",
                "slot_end": "2026-11-22T12:00:00+05:30",
                "outcome": "not_chosen",
                "chosen_by": "agent",
                "override_reason": None,
                "why": "Next-day availability only.",
            },
        ]

        # Quote & PaymentIntent (cover all 5 PaymentIntent states across the 20 cases)
        quote_id = stable_uuid(f"quote-{case_id}")
        visit_fee = 45000
        labour_fee = 55000
        total_paise = visit_fee + labour_fee + part_mrp
        quote = {
            "id": quote_id,
            "version": 1,
            "quote_type": "firm" if idx < 6 else "estimate",
            "lines": [
                {"kind": "visit_fee", "description": "Visit and inspection", "amount_paise": visit_fee, "payer": "household"},
                {"kind": "labour", "description": "Fault repair labour", "amount_paise": labour_fee, "payer": "household"},
                {"kind": "part", "description": f"{chosen_part['name']} ({chosen_part['part_no']})", "amount_paise": part_mrp, "payer": "household"},
            ],
            "total_paise": total_paise,
            "household_paise": total_paise,
            "covered_paise": 0,
            "approved_at": updated_at if idx < 5 else None,
            "approval_method": "magic_link" if idx < 5 else None,
        }

        pay_state = payment_states_cycle[idx % len(payment_states_cycle)]
        pay_method = "google_pay" if idx % 2 == 0 else "upi_intent"
        payment_id = stable_uuid(f"pay-{case_id}")
        payment_intent = {
            "id": payment_id,
            "quote_id": quote_id,
            "amount_paise": total_paise,
            "status": pay_state,
            "method": pay_method,
            "upi_intent_url": f"upi://pay?pa=keepwell@okaxis&pn=Keepwell&am={total_paise/100:.2f}&cu=INR&tr={payment_id[:12]}" if pay_method == "upi_intent" else None,
            "google_pay": {
                "environment": "TEST",
                "merchant_name": centres_by_id[centre_id]["name"],
                "merchant_id": "BCR2DN4TKEEPWELL",
                "gateway": "example",
                "gateway_merchant_id": "exampleGatewayMerchantId",
                "transaction_info": {
                    "currency_code": "INR",
                    "total_price_status": "FINAL",
                    "total_price": f"{total_paise / 100:.2f}",
                },
            } if pay_method == "google_pay" else None,
            "payment_ref": f"PAYREF-{case_id}-9921" if pay_state == "paid" else None,
            "created_at": updated_at,
            "expires_at": "2026-11-21T23:59:59+05:30",
            "paid_at": updated_at if pay_state == "paid" else None,
        }
        all_payments.append({**payment_intent, "ticket_id": ticket_id, "case_id": case_id})

        visit_id = stable_uuid(f"visit-{case_id}")
        visit = {
            "id": visit_id,
            "technician_id": primary_tech["id"],
            "planned_start": slot_start,
            "planned_end": slot_end,
            "check_in_at": updated_at if case_id in ("C01", "C03") else None,
            "check_out_at": None,
            "outcome": None,
            "closure_confirmed_at": None,
            "rating": None,
        }

        # Debrief: ensure C03 (and C01) have a Debrief with one unmatched part in `unresolved`
        debrief = None
        if case_id in ("C01", "C03"):
            debrief = {
                "id": stable_uuid(f"debrief-{case_id}"),
                "visit_id": visit_id,
                "status": "ready",
                "language": "hi" if case_id == "C03" else "te",
                "transcript": (
                    "पंप हाउसिंग में सिक्का फंसा था, नया ड्रेन पंप लगाया और एक छोटा रबर गैस्केट बदला। टेस्ट साइकिल ठीक चला।"
                    if case_id == "C03"
                    else "Filter cleaned and capacitor checked; replaced worn rubber grommet."
                ),
                "extracted": {
                    "fault_found": "Coin lodged in drain pump impeller housing" if case_id == "C03" else "Capacitor degradation",
                    "work_done": "Cleared obstruction, replaced drain pump assembly, ran full drain and spin test" if case_id == "C03" else "Replaced capacitor and verified cooling",
                    "parts_used": [{"part_no": chosen_part["part_no"], "quantity": 1}],
                    "advice_for_household": "Check pockets for coins before loading and clean drain filter quarterly.",
                    "appliance_notes": "Drain hose clear; no leaks observed.",
                    "follow_up_needed": False,
                },
                "unresolved": ["rubber gasket ring (unmatched in catalogue — needs checking)"],
                "confirmed_at": None,
            }

        ticket_status = (
            "declined"
            if case_id == "C18"
            else ("assigned" if idx < 12 else "triaging")
        )
        flags = []
        if safety_flag:
            flags.append("safety_stop")
        if case_id == "C03":
            flags.extend(["stage_candidate", "video_switched", "fix_failed_rerun"])
        if case_id == "C18":
            flags.append("authority_declined")
        if debrief and debrief["unresolved"]:
            flags.append("debrief_unresolved_part")

        card = {
            "id": ticket_id,
            "centre_id": centre_id,
            "trigger": trigger,
            "channel": channel,
            "job_type": job_type,
            "status": ticket_status,
            "resolution": None,
            "urgency_class": urgency_class,
            "needed_by": needed_by,
            "safety_flag": safety_flag,
            "safety_reason": safety_reason,
            "entitlement": "brand_warranty" if case_id in ("C05", "C17", "C19") else "paid",
            "household": make_hh_ref(hh),
            "appliance": make_app_ref(app),
            "complaint_summary": complaint_summary,
            "language": "hi" if case_id == "C03" else hh["language"],
            "created_at": created_at,
            "updated_at": updated_at,
            "flags": flags,
        }

        detail = {
            "case_id": case_id,
            "card": card,
            "case_card": {
                "summary": complaint_summary,
                "symptoms": ["Not draining", "Error E21"] if case_id == "C03" else [complaint_summary[:80]],
                "error_codes": ["E21"] if case_id == "C03" else (["dF"] if case_id == "C17" else []),
                "what_was_tried": ["Drain pump filter cleaned on video; E21 returned"] if case_id == "C03" else [],
                "safety_notes": safety_reason or "No immediate safety hazard reported.",
                "identity_notes": f"Matched household {hh['display_name']} via {hh['verified_via']}.",
                "sources": [
                    {
                        "doc_title": "wc_washer_manual.pdf" if case_id == "C03" else "kw_field_guide.pdf",
                        "page": 14 if case_id == "C03" else 3,
                        "uri": None,
                        "snippet": "E21 indicates drain timeout > 4 minutes; inspect drain filter, then drain pump impeller." if case_id == "C03" else "Standard triage protocol.",
                    }
                ],
            },
            "urgency": [
                {
                    "class": urgency_class,
                    "rule_codes": ["SAF-ELEC" if case_id == "C05" else ("SAF-SMOKE" if case_id == "C15" else "STD-DEFAULT")],
                    "facts": {"unsafe_now": safety_flag, "stopped_or_partial": "stopped"},
                    "assessed_by": "agent",
                    "reason": safety_reason or f"Assessed {urgency_class} from reported symptoms.",
                    "protective_steps_sent": safety_flag,
                    "created_at": created_at,
                }
            ],
            "gates": gates,
            "clarifying_qa": [
                {
                    "seq": 1,
                    "question": "Is there any burning smell, smoke, or electric shock?",
                    "answer": "No, nothing unsafe; the floor is wet." if case_id == "C03" else ("Yes, felt a shock on the body." if case_id == "C05" else "No, nothing unsafe."),
                    "answer_source": channel,
                    "asked_at": created_at,
                }
            ],
            "fix_attempts": fix_attempts,
            "tried_summary": [
                {"code": fa["catalogue_code"], "outcome": fa["outcome"], "note": fa["household_report"]}
                for fa in fix_attempts
            ],
            "diagnosis": {
                "hypotheses": [
                    {
                        "fault_key": "wm_drain_pump_jam" if case_id == "C03" else "primary_fault",
                        "label": "Drain pump impeller jammed / failed (post-filter-clean re-run)" if case_id == "C03" else f"Probable {app['category_code'] if app else 'appliance'} fault",
                        "probability": 0.86 if case_id == "C03" else 0.78,
                        "evidence": (
                            ["E21 persisted after SF-WM-DRAINFILTER-WC", "Coins and lint observed on video"]
                            if case_id == "C03"
                            else ["Symptom match with KB"]
                        ),
                        "citations": [
                            {
                                "doc_title": "wc_washer_manual.pdf" if case_id == "C03" else "kw_field_guide.pdf",
                                "page": 14 if case_id == "C03" else 4,
                                "uri": None,
                                "snippet": "If E21 recurs after filter clean, inspect pump housing for foreign object or replace WC-WM-DPUMP.",
                            }
                        ],
                    }
                ],
                "abstained": False,
                "reason": None,
                "rerun_of": stable_uuid("diag-C03-v1") if case_id == "C03" else None,
                "model_version": "gemini-3.8-flash",
            },
            "visit_plan": {
                "id": stable_uuid(f"vp-{case_id}"),
                "version": 2 if case_id == "C03" else 1,
                "trigger_reason": "safe_fix_not_worked" if case_id == "C03" else "initial_triage",
                "already_tried": ["Clean the drain pump filter (Wavecrest) — E21 returned"] if case_id == "C03" else [],
                "required_skills": [app["category_code"] if app else "washing_machine"],
                "est_duration_p50_min": 40 if case_id == "C03" else 60,
                "est_duration_p80_min": 65 if case_id == "C03" else 90,
                "tools_needed": ["Multimeter", "Torx driver set", "Towels & drain pan"],
                "requires_safety_cert": ["electrical"] if case_id == "C05" else (["work_at_height", "gas"] if case_id == "C07" else []),
                "parts": [
                    {
                        "part_no": chosen_part["part_no"],
                        "name": chosen_part["name"],
                        "probability": 0.82,
                        "quantity": 1,
                        "source_ladder": "centre",
                        "ready": True,
                    }
                ],
                "access_notes": hh["access_notes"],
                "confidence": 0.86,
            },
            "candidates": candidates,
            "slot_proposals": [
                {
                    "slot_start": slot_start,
                    "slot_end": slot_end,
                    "price_low_paise": visit_fee + labour_fee,
                    "price_high_paise": total_paise,
                    "shown_at": updated_at,
                    "accepted": True,
                }
            ],
            "quotes": [quote],
            "payments": [payment_intent],
            "debrief": debrief,
            "visit": visit,
            "timeline": [
                {
                    "at": created_at,
                    "type": "conversation_started",
                    "actor": "household" if trigger.startswith("household") else ("brand" if trigger == "brand_forward" else "retailer"),
                    "title": f"{case_id} received via {channel}",
                    "detail": complaint_summary[:140],
                    "ref": ticket_id,
                },
                {
                    "at": updated_at,
                    "type": "technician_assigned" if ticket_status == "assigned" else "urgency_assessed",
                    "actor": "agent",
                    "title": f"Assigned {primary_tech['name']} for {slot_start[11:16]}-{slot_end[11:16]}" if ticket_status == "assigned" else f"Urgency assessed as {urgency_class}",
                    "detail": f"Score {candidates[0]['score']} (6-factor ranking)",
                    "ref": visit_id,
                },
            ],
            "authority": {"level": auth_level, "decision": auth_decision},
        }
        tickets.append(detail)

        demo_cases.append({
            "case_id": case_id,
            "ticket_id": ticket_id,
            "trigger": trigger,
            "channel": channel,
            "centre_key": centre_key,
            "centre_id": centre_id,
            "centre_name": centres_by_id[centre_id]["name"],
            "urgency_class": urgency_class,
            "safety_flag": safety_flag,
            "stage_candidate": case_id == "C03",
            "summary": complaint_summary[:120],
            "inbox_event": item,
        })

        # Seed initial WhatsApp thread for household
        if channel == "whatsapp" or case_id == "C03":
            whatsapp_threads[hh["id"]].append({
                "id": stable_uuid(f"wa-in-{case_id}"),
                "direction": "in",
                "type": "text",
                "text": complaint_summary,
                "media_url": None,
                "template": None,
                "at": created_at,
                "ticket_id": ticket_id,
                "status": "delivered",
            })
            whatsapp_threads[hh["id"]].append({
                "id": stable_uuid(f"wa-out-{case_id}"),
                "direction": "out",
                "type": "text",
                "text": (
                    f"Namaste {hh['display_name']}, {centres_by_id[centre_id]['name']} received your request. "
                    + ("Please stop using it and switch it off at the wall. A technician will come as soon as possible." if safety_flag else f"Technician {primary_tech['name']} is scheduled for {slot_start[11:16]}-{slot_end[11:16]}.")
                ),
                "media_url": None,
                "template": "safety_stop" if safety_flag else "booking_confirmed",
                "at": updated_at,
                "ticket_id": ticket_id,
                "status": "read",
            })

    # 8. Demo households per centre
    demo_households: list[dict[str, Any]] = []
    seen_demo_hh: set[tuple[str, str]] = set()
    for t in tickets:
        cid = t["card"]["centre_id"]
        ckey = centre_id_to_key[cid]
        hid = t["card"]["household"]["id"]
        if (ckey, hid) not in seen_demo_hh:
            seen_demo_hh.add((ckey, hid))
            h = households_by_id[hid]
            demo_households.append({
                "household_id": hid,
                "display_name": h["display_name"],
                "phone_masked": h["phone_masked"],
                "language": h["language"],
                "magic_token": h["magic_token"],
                "centre_key": ckey,
                "centre_id": cid,
            })
    # Ensure every centre has at least 2 demo households
    for c in centres:
        cid = c["id"]
        ckey = c["centre_key"]
        existing = [dh for dh in demo_households if dh["centre_id"] == cid]
        if len(existing) < 2:
            for h in households:
                if cid in h["linked_centre_ids"] and (ckey, h["id"]) not in seen_demo_hh:
                    seen_demo_hh.add((ckey, h["id"]))
                    demo_households.append({
                        "household_id": h["id"],
                        "display_name": h["display_name"],
                        "phone_masked": h["phone_masked"],
                        "language": h["language"],
                        "magic_token": h["magic_token"],
                        "centre_key": ckey,
                        "centre_id": cid,
                    })
                    existing.append(h)
                    if len(existing) >= 2:
                        break

    # 9. Compute per-centre overview KPIs (Section 11 definitions)
    hist_tickets = ds.read_csv("ticket.csv")
    hist_visits = ds.read_csv("visit.csv")
    visits_by_ticket: dict[str, list[dict[str, str]]] = defaultdict(list)
    for v in hist_visits:
        visits_by_ticket[v["ticket_id"]].append(v)

    overview_by_centre: dict[str, dict[str, Any]] = {}
    for c in centres:
        cid = c["id"]
        c_tickets = [t for t in tickets if t["card"]["centre_id"] == cid]
        open_by_class = {"safety": 0, "urgent": 0, "standard": 0, "planned": 0}
        for t in c_tickets:
            uc = t["card"]["urgency_class"]
            if uc in open_by_class:
                open_by_class[uc] += 1

        c_hist = [ht for ht in hist_tickets if ht["centre_id"] == cid and ht["job_type"] == "repair"]
        ftf_num = sum(
            1
            for ht in c_hist
            if len(visits_by_ticket[ht["id"]]) == 1 and visits_by_ticket[ht["id"]][0]["outcome"] == "fixed"
        )
        ftf_den = max(1, sum(1 for ht in c_hist if len(visits_by_ticket[ht["id"]]) >= 1))
        ftf_rate = round(ftf_num / ftf_den, 3)
        fvr_14d = round(max(0.0, ftf_rate - 0.04), 3)
        self_fix_num = sum(1 for ht in c_hist if ht["resolution"] == "self_fix")
        self_fix_rate = round(self_fix_num / max(1, len(c_hist)), 3)

        overview_by_centre[cid] = {
            "centre_id": cid,
            "centre_key": c["centre_key"],
            "centre_name": c["name"],
            "open_by_class": open_by_class,
            "first_time_fix": ftf_rate,
            "fvr_14d": fvr_14d,
            "self_fix_resolution": self_fix_rate,
            "gate_funnel": {
                "gate1_asked": max(10, len(c_hist)),
                "gate1_yes": max(6, int(len(c_hist) * 0.68)),
                "gate2_asked": max(6, int(len(c_hist) * 0.68)),
                "switch_to_video": max(3, int(len(c_hist) * 0.34)),
            },
            "urgency_agreement": 0.92,
            "override_rate": 6.4,
            "parts_ready_at_visit": 0.87,
            "jobs_per_tech_day": round(max(2.4, len(c_hist) / max(1, len(techs_by_centre[cid]) * 12)), 2),
        }

    # 10. C03 script for mocks/ws and timelapse_c03.py
    c03_ticket = next(t for t in tickets if t["case_id"] == "C03")
    c03_vs = voice_scripts.get("C03/01_call.ogg", {})
    c03_script = {
        "case_id": "C03",
        "ticket_id": c03_ticket["card"]["id"],
        "centre_id": c03_ticket["card"]["centre_id"],
        "centre_key": "c_fw",
        "centre_name": centres_by_id[c03_ticket["card"]["centre_id"]]["name"],
        "household_id": c03_ticket["card"]["household"]["id"],
        "household_name": c03_ticket["card"]["household"]["display_name"],
        "caller_number": "+91 50971 16577",
        "appliance": c03_ticket["card"]["appliance"],
        "opening_hi": c03_vs.get("transcript_original_script", "नमस्ते, मेरी वॉशिंग मशीन में पानी नहीं निकल रहा है। स्क्रीन पर E21 आ रहा है।"),
        "opening_en": "Hello, my washing machine is not draining water. Screen shows E21. Clothes have been soaking since last night.",
        "safe_fix_code": "SF-WM-DRAINFILTER-WC",
        "safe_fix_title": safefix_by_code.get("SF-WM-DRAINFILTER-WC", {}).get("title", "Clean the drain pump filter (Wavecrest)"),
        "part_no": "WC-WM-DPUMP",
        "part_name": parts_by_no.get("WC-WM-DPUMP", {}).get("name", "Drain pump"),
        "candidates": c03_ticket["candidates"],
        "quote": c03_ticket["quotes"][0],
        "visit": c03_ticket["visit"],
        "magic_token": households_by_id[c03_ticket["card"]["household"]["id"]]["magic_token"],
    }

    outputs = {
        "centres.json": centres,
        "technicians.json": technicians,
        "households.json": households,
        "appliances.json": appliances,
        "tickets.json": tickets,
        "safefix.json": safefix_list,
        "parts.json": {
            "catalogue": part_rows,
            "parts_centres": parts_centres,
            "stock": stock_items,
            "centre_prices": centre_prices,
            "parts_requests": parts_requests,
        },
        "demo_cases.json": demo_cases,
        "demo_households.json": demo_households,
        "brands_retailers.json": {"brands": brands_rows, "retailers": retailers_rows},
        "overview.json": overview_by_centre,
        "payments.json": all_payments,
        "whatsapp_threads.json": dict(whatsapp_threads),
        "c03_script.json": c03_script,
    }

    for filename, payload in outputs.items():
        (OUT_DIR / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "source": ds.source_description(),
        "centres": len(centres),
        "technicians": len(technicians),
        "households": len(households),
        "appliances": len(appliances),
        "tickets": len(tickets),
        "demo_cases": len(demo_cases),
        "demo_households": len(demo_households),
        "safefix": len(safefix_list),
        "payments": len(all_payments),
    }


if __name__ == "__main__":
    summary = build_all()
    print("Generated fixtures:", json.dumps(summary, indent=2))
