"""Admin & Demo REST routes (Contract C5.2)."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from db.seed.load_seed import load_seed
from services.agents.orchestrator import process_inbound_case
from services.api.deps import APIError, load_directory_maps, require_admin_auth
from services.api.routes_channels import (
    _extract_text_from_wa_messages,
    _find_centre_by_number,
    _resolve_target_centre_for_brand,
)
from services.api.serializers import list_envelope
from services.common.auth import AuthContext
from services.common.config import settings
from services.common.crypto import decrypt_phone, mask_phone, mint_magic_token
from services.common.db import get_rls_session
from services.live.bridge import RECORDED_REPLAYS
from services.worker.projections import projection_store

router = APIRouter(prefix="/admin", tags=["Admin & Demo"])


class PlayCaseRequest(BaseModel):
    case_id: str


def _load_inbox_cases() -> List[Dict[str, Any]]:
    inbox_path = settings.dataset_dir / "inbox" / "inbox.json"
    return json.loads(inbox_path.read_text(encoding="utf-8"))


def _resolve_case_centre(db: Any, case: Dict[str, Any]) -> tuple[str, str]:
    ck2id, cid2key, _, _, _ = load_directory_maps(db)
    if case.get("to_number"):
        cid = _find_centre_by_number(db, case["to_number"])
        if cid:
            return cid, cid2key.get(cid, "c_fw")
    payload = case.get("payload") or {}
    if case.get("trigger") == "brand_forward":
        brand_name = str(payload.get("brand") or "")
        b_rows = db.raw_query("SELECT id FROM brand WHERE LOWER(name) = LOWER(%s) LIMIT 1", (brand_name,))
        bid = b_rows[0]["id"] if b_rows else None
        cid = _resolve_target_centre_for_brand(db, payload, bid)
        return cid, cid2key.get(cid, "c_fw")
    if case.get("trigger") == "retailer_handover":
        notes = str(payload.get("notes") or "")
        ckey = "c_fw" if "washer" in notes.lower() else "c_ip"
        cid = ck2id.get(ckey) or next(iter(ck2id.values()))
        return cid, cid2key.get(cid, ckey)
    cid = ck2id.get("c_fw") or next(iter(ck2id.values()))
    return cid, cid2key.get(cid, "c_fw")


@router.get("/demo/cases")
def list_demo_cases(auth: AuthContext = Depends(require_admin_auth)) -> Dict[str, Any]:
    cases = _load_inbox_cases()
    items: List[Dict[str, Any]] = []
    with get_rls_session(role="platform") as db:
        for c in cases:
            cid, ckey = _resolve_case_centre(db, c)
            items.append(
                {
                    "case_id": c["case_id"],
                    "trigger": c["trigger"],
                    "channel": c["channel"],
                    "centre_id": cid,
                    "centre_key": ckey,
                    "sender_profile_name": c.get("sender_profile_name") or (c.get("payload") or {}).get("customer", {}).get("name"),
                    "stage_candidate": c["case_id"] == "C03",
                }
            )
    return list_envelope(items)


@router.post("/demo/play-case")
def play_demo_case(
    body: PlayCaseRequest,
    auth: AuthContext = Depends(require_admin_auth),
) -> Dict[str, Any]:
    cases = _load_inbox_cases()
    case = next((c for c in cases if c["case_id"].upper() == body.case_id.upper()), None)
    if not case:
        raise APIError("case_not_found", f"Demo case {body.case_id} not found", status_code=404, field="case_id")

    with get_rls_session(role="platform") as db:
        centre_id, centre_key = _resolve_case_centre(db, case)
        trigger = case["trigger"]
        channel = case["channel"]

        if trigger in ("brand_forward", "retailer_handover"):
            payload = case.get("payload") or {}
            customer = payload.get("customer") or {}
            from_phone = str(customer.get("phone") or "+91 50000 00000")
            display_name = customer.get("name")
            text = str(payload.get("complaint") or payload.get("notes") or f"{trigger} case {case['case_id']}")
            brand_name = payload.get("brand")
            claimed = "brand_warranty" if str(payload.get("claimed_warranty") or "").lower() in ("in_warranty", "brand_warranty") else "paid"
            note = str(payload.get("brand_note") or "")
            serial_m = re.search(r"Serial[^:]*:\s*([A-Z0-9-]+)", note, re.IGNORECASE)
            res = process_inbound_case(
                db,
                centre_id=centre_id,
                trigger=trigger,
                channel=channel,
                from_phone=from_phone,
                text=text,
                display_name=display_name,
                brand_name=brand_name,
                serial_no=serial_m.group(1) if serial_m else None,
                entitlement_claim=claimed,
                requested_job=payload.get("requested_job"),
            )
        else:
            from_phone = str(case.get("from_phone") or "+91 50971 16577")
            display_name = case.get("sender_profile_name")
            msgs = case.get("messages") or []
            text = _extract_text_from_wa_messages(msgs)
            if case["case_id"] == "C03":
                text = "मेरी Wavecrest वॉशिंग मशीन में पानी नहीं निकल रहा और डिस्प्ले पर E21 आ रहा है"
            res = process_inbound_case(
                db,
                centre_id=centre_id,
                trigger=trigger,
                channel=channel,
                from_phone=from_phone,
                text=text,
                display_name=display_name,
                gate1_answer="yes",
                gate2_choice="switch_to_video" if case["case_id"] == "C03" else "continue_here",
            )

        projection_store.set_demo_meta(active_case_id=case["case_id"])
        return {
            "case_id": case["case_id"],
            "centre_key": centre_key,
            "centre_id": centre_id,
            "status": res["status"],
            "ticket_id": res.get("ticket_id"),
            "declined_reason": res.get("declined_reason"),
            "urgency": res.get("urgency"),
            "authority": res.get("authority"),
            "events_count": len(res.get("events", [])),
        }


@router.get("/demo/households")
def list_demo_households(
    centre_key: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    auth: AuthContext = Depends(require_admin_auth),
) -> Dict[str, Any]:
    with get_rls_session(role="platform") as db:
        ck2id, _, _, _, _ = load_directory_maps(db)
        if centre_key:
            cid = ck2id.get(centre_key)
            if not cid:
                raise APIError("unknown_centre", f"Unknown centre_key: {centre_key}", status_code=404, field="centre_key")
            rows = db.raw_query(
                """
                SELECT h.* FROM household h
                JOIN household_centre_link l ON l.household_id = h.id
                WHERE l.centre_id = %s
                ORDER BY h.created_at
                LIMIT %s
                """,
                (cid, limit),
            )
        else:
            rows = db.raw_query("SELECT * FROM household ORDER BY created_at LIMIT %s", (limit,))

        items: List[Dict[str, Any]] = []
        for h in rows:
            members = db.raw_query(
                "SELECT name FROM household_member WHERE household_id = %s ORDER BY CASE role WHEN 'owner' THEN 0 ELSE 1 END LIMIT 1",
                (h["id"],),
            )
            display_name = members[0]["name"] if members else "Household"
            raw_enc = str(h.get("phone_enc") or "")
            phone = decrypt_phone(bytes.fromhex(raw_enc[2:])) if raw_enc.startswith("\\x") else "+91 *****0000"
            magic_token = mint_magic_token(h["id"], scope="household", ttl_seconds=86400, extra={"household_id": h["id"]})
            items.append(
                {
                    "household_id": h["id"],
                    "display_name": display_name,
                    "phone_masked": mask_phone(phone),
                    "language": h.get("language") or "en",
                    "magic_token": magic_token,
                }
            )
        return list_envelope(items)


@router.post("/demo/reset")
def reset_demo(auth: AuthContext = Depends(require_admin_auth)) -> Dict[str, Any]:
    counts = load_seed()
    projection_store.clear()
    projection_store.set_demo_meta(None)
    return {"status": "reset_complete", "tables_loaded": len(counts), "total_rows": sum(counts.values())}


@router.post("/projection/rebuild")
def rebuild_projections(auth: AuthContext = Depends(require_admin_auth)) -> Dict[str, Any]:
    with get_rls_session(role="platform") as db:
        counts = projection_store.rebuild_all(db)
    return {"status": "rebuilt", "backend": projection_store.backend_mode, "counts": counts}


@router.post("/demo/replay-call")
def replay_recorded_call(auth: AuthContext = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Recorded-call fallback returning C03 events if a live session was captured or replaying C03."""
    if RECORDED_REPLAYS:
        last_conv_id = list(RECORDED_REPLAYS.keys())[-1]
        events = RECORDED_REPLAYS[last_conv_id]
        return {"source": "recorded_live_session", "conversation_id": last_conv_id, "events": events}

    # Deterministic C03 replay fallback
    with get_rls_session(role="platform") as db:
        ck2id, _, _, _, _ = load_directory_maps(db)
        cid = ck2id["c_fw"]
        res = process_inbound_case(
            db,
            centre_id=cid,
            trigger="household_call",
            channel="voice",
            from_phone="+91 50971 16577",
            text="मेरी Wavecrest वॉशिंग मशीन में पानी नहीं निकल रहा और डिस्प्ले पर E21 आ रहा है",
            language_hint="hi",
            gate1_answer="yes",
            gate2_choice="switch_to_video",
            fix_outcome="not_worked",
        )
        return {
            "source": "c03_fallback_replay",
            "ticket_id": res.get("ticket_id"),
            "events": res.get("events", []),
        }
