"""Seed the Firestore emulator with Keepwell live state (Contract Section 6).

Zero extra SDK dependency: writes directly via Firestore REST API to
`FIRESTORE_EMULATOR_HOST` (default `localhost:8080`).

Seeds:
- All 9 centres: `centres/{cid}/tickets/{tid}`, `technicians/{tech_id}`,
  `visits/{vid}`, `parts_requests/{rid}`, `conversations/{conv_id}`, `feed/{eid}`
- `households/{hid}/whatsapp_thread/{mid}`
- `meta/demo`
- C03 snapshots at 5 points in time (`meta/c03_snapshots/points/t1..t5`)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from mocks.fixtures.build_fixtures import OUT_DIR as FIXTURES_DIR, build_all

ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def to_firestore_value(val: Any) -> dict[str, Any]:
    if val is None:
        return {"nullValue": None}
    if isinstance(val, bool):
        return {"booleanValue": val}
    if isinstance(val, int):
        return {"integerValue": str(val)}
    if isinstance(val, float):
        return {"doubleValue": val}
    if isinstance(val, str):
        if ISO_TS_RE.match(val):
            # Convert offset timestamps to RFC3339 UTC Z for Firestore REST
            try:
                dt = datetime.fromisoformat(val)
                utc_str = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                return {"timestampValue": utc_str}
            except ValueError:
                pass
        return {"stringValue": val}
    if isinstance(val, list):
        return {"arrayValue": {"values": [to_firestore_value(v) for v in val]}}
    if isinstance(val, dict):
        if set(val.keys()) == {"lat", "lon"} and isinstance(val["lat"], (int, float)) and isinstance(val["lon"], (int, float)):
            return {"geoPointValue": {"latitude": float(val["lat"]), "longitude": float(val["lon"])}}
        return {"mapValue": {"fields": {str(k): to_firestore_value(v) for k, v in val.items()}}}
    return {"stringValue": str(val)}


def to_firestore_doc(data: dict[str, Any]) -> dict[str, Any]:
    return {"fields": {str(k): to_firestore_value(v) for k, v in data.items()}}


class FirestoreRestClient:
    def __init__(self, host: str | None = None, project_id: str | None = None, dry_run: bool = False) -> None:
        self.host = host or os.getenv("FIRESTORE_EMULATOR_HOST", "localhost:8080")
        self.project_id = project_id or os.getenv("FIREBASE_PROJECT_ID", "keepwell-demo")
        self.dry_run = dry_run
        self.writes = 0

    def set_doc(self, doc_path: str, data: dict[str, Any]) -> None:
        self.writes += 1
        if self.dry_run:
            return
        url = f"http://{self.host}/v1/projects/{self.project_id}/databases/(default)/documents/{doc_path}"
        body = json.dumps(to_firestore_doc(data)).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="PATCH",
            headers={"Content-Type": "application/json", "Authorization": "Bearer owner"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Firestore PATCH {doc_path} failed ({e.code}): {detail}") from e


def load_fixture(name: str) -> Any:
    path = FIXTURES_DIR / name
    if not path.exists():
        build_all()
    return json.loads(path.read_text(encoding="utf-8"))


def seed_all(host: str | None = None, project_id: str | None = None, dry_run: bool = False) -> dict[str, int]:
    client = FirestoreRestClient(host=host, project_id=project_id, dry_run=dry_run)

    centres = load_fixture("centres.json")
    technicians = load_fixture("technicians.json")
    tickets = load_fixture("tickets.json")
    parts_data = load_fixture("parts.json")
    wa_threads = load_fixture("whatsapp_threads.json")
    c03 = load_fixture("c03_script.json")

    counts = {
        "centres": 0,
        "tickets": 0,
        "technicians": 0,
        "visits": 0,
        "parts_requests": 0,
        "whatsapp_messages": 0,
        "c03_snapshots": 0,
    }

    # Seed centre metadata docs
    for c in centres:
        client.set_doc(f"centres/{c['id']}", {
            "id": c["id"],
            "centre_key": c["centre_key"],
            "name": c["name"],
            "pincode": c["pincode"],
            "default_language": c["default_language"],
        })
        counts["centres"] += 1

    # Seed technicians under centres/{cid}/technicians/{tech_id}
    for tech in technicians:
        cid = tech["centre_id"]
        client.set_doc(f"centres/{cid}/technicians/{tech['id']}", {
            "name": tech["name"],
            "status": tech["status"],
            "current_visit_id": None,
            "last_location": tech["last_location"],
            "last_ping_at": tech["last_ping_at"],
        })
        counts["technicians"] += 1

    # Seed tickets, visits, feed events
    for t in tickets:
        card = t["card"]
        cid = card["centre_id"]
        tid = card["id"]
        chosen = next((c for c in t["candidates"] if c["outcome"] == "chosen"), None)
        latest_pay = t["payments"][-1] if t["payments"] else None
        ticket_doc = {
            **card,
            "unread": card["urgency_class"] in ("safety", "urgent") or t.get("case_id") == "C03",
            "last_event_at": card["updated_at"],
            "assignee": {"technician_id": chosen["technician_id"], "name": chosen["name"]} if chosen else None,
            "next_action": "Dispatch immediately" if card["safety_flag"] else "Confirm visit slot",
            "payment_status": latest_pay["status"] if latest_pay else "none",
        }
        client.set_doc(f"centres/{cid}/tickets/{tid}", ticket_doc)
        counts["tickets"] += 1

        if t.get("visit"):
            v = t["visit"]
            vp = t.get("visit_plan") or {}
            client.set_doc(f"centres/{cid}/visits/{v['id']}", {
                "ticket_id": tid,
                "technician_id": v["technician_id"],
                "planned_start": v["planned_start"],
                "planned_end": v["planned_end"],
                "status": card["status"],
                "brief": {
                    "already_tried": vp.get("already_tried", []),
                    "parts": vp.get("parts", []),
                    "access_notes": vp.get("access_notes", ""),
                },
                "address_released": card["status"] in ("assigned", "in_progress", "closed"),
            })
            counts["visits"] += 1

        for idx, ev in enumerate(t.get("timeline", [])):
            client.set_doc(f"centres/{cid}/feed/{tid}_{idx}", {
                "id": f"{tid}_{idx}",
                "at": ev["at"],
                "centre_id": cid,
                "ticket_id": tid,
                "conversation_id": None,
                "type": ev["type"],
                "actor": ev["actor"],
                "title": ev["title"],
                "detail": ev["detail"],
                "payload": {"ref": ev.get("ref")},
            })

    # Seed parts_requests
    for pr in parts_data.get("parts_requests", []):
        cid = pr["centre_id"]
        client.set_doc(f"centres/{cid}/parts_requests/{pr['id']}", {
            "visit_id": pr["visit_id"],
            "part_no": pr["part_no"],
            "quantity": pr["quantity"],
            "status": pr["status"],
            "parts_centre_id": pr["parts_centre_id"],
        })
        counts["parts_requests"] += 1

    # Seed households/{id}/whatsapp_thread/{message_id}
    for hh_id, msgs in wa_threads.items():
        for m in msgs:
            client.set_doc(f"households/{hh_id}/whatsapp_thread/{m['id']}", m)
            counts["whatsapp_messages"] += 1

    # Seed meta/demo
    client.set_doc("meta/demo", {
        "active_case_id": "C03",
        "reset_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    # Seed C03 snapshots at 5 points in time
    c03_snapshots = [
        ("t1_intake", "Inbound Hindi voice call; household & Wavecrest washer identified; urgency=standard", "triaging", "none"),
        ("t2_video_safefix", "Gates 1 & 2 yes; switched to live video; guiding SF-WM-DRAINFILTER-WC", "triaging", "none"),
        ("t3_rerun_assign", "Drain filter fix failed (E21 returned); diagnosis re-run; Ramesh Yadav assigned", "assigned", "created"),
        ("t4_quote_paid", "Firm quote ₹2,235 approved; Google Pay sandbox payment confirmed", "in_progress", "paid"),
        ("t5_otp_closed", "Voice debrief confirmed (1 unresolved part flagged); closed via household OTP", "closed", "paid"),
    ]
    for idx, (snap_id, desc, status, pay_status) in enumerate(c03_snapshots, start=1):
        client.set_doc(f"meta/c03_snapshots/points/{snap_id}", {
            "step": idx,
            "ticket_id": c03["ticket_id"],
            "centre_id": c03["centre_id"],
            "description": desc,
            "status": status,
            "payment_status": pay_status,
        })
        counts["c03_snapshots"] += 1

    counts["total_writes"] = client.writes
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Firestore emulator with Keepwell mock fixtures.")
    parser.add_argument("--host", default=None, help="Firestore emulator host:port (default FIRESTORE_EMULATOR_HOST or localhost:8080)")
    parser.add_argument("--project", default=None, help="Firebase project ID (default keepwell-demo)")
    parser.add_argument("--dry-run", action="store_true", help="Validate serialization without making HTTP calls")
    args = parser.parse_args()

    res = seed_all(host=args.host, project_id=args.project, dry_run=args.dry_run)
    print("Firestore seed summary:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
