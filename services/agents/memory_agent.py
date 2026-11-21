from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.agents.engines.parts import CataloguePart, CompatibilityRow, RequestedPart, resolve_parts
from services.common.db import RLSSession
from services.common.untrusted_guard import ModelArmorGuard


PART_TOKEN_RE = re.compile(r"\b([A-Z]{2,6}[-_][A-Z0-9]{2,8}|R32|FLARE|MEMB|SED|CARB|DEFH|DEFT|PTC|LIDSW|HEL_ST|THS|MCAP|CAPF|GASK)\b")


def process_spoken_debrief(
    db: RLSSession,
    visit_id: str,
    centre_id: str,
    transcript: str,
    language: str = "en",
    media_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ADK Memory Agent:
    Processes a technician's spoken close-out debrief into structured JSON,
    validates EVERY mentioned part through parts.resolve_parts() against
    part_catalogue + part_compatibility, and places any unmatched part in `unresolved`.
    """
    guard = ModelArmorGuard.screen_inbound(transcript, source="technician_debrief")
    clean = guard.sanitized_text

    visit = db.raw_query("SELECT * FROM visit WHERE id = %s", (visit_id,))
    if not visit:
        raise ValueError(f"Visit {visit_id} not found")
    ticket = db.raw_query("SELECT * FROM ticket WHERE id = %s", (visit[0]["ticket_id"],))[0]
    appliance = db.raw_query("SELECT * FROM appliance WHERE id = %s", (ticket["appliance_id"],))[0] if ticket.get("appliance_id") else None

    mentioned_codes = list(dict.fromkeys(PART_TOKEN_RE.findall(clean.upper())))
    verified_parts_out: List[Dict[str, Any]] = []
    unresolved_out: List[str] = []

    if mentioned_codes and appliance and appliance.get("model_id"):
        cat_rows = [
            CataloguePart(
                id=r["id"],
                brand_id=r["brand_id"],
                part_no=r["part_no"],
                name=r["name"],
                kind=r.get("kind") or "genuine",
                mrp_paise=int(r.get("mrp_paise") or 0),
                warranty_months=int(r.get("warranty_months") or 0),
            )
            for r in db.raw_query("SELECT * FROM part_catalogue")
        ]
        compat_rows = [
            CompatibilityRow(part_id=r["part_id"], model_id=r["model_id"], revision=r.get("revision") or "")
            for r in db.raw_query("SELECT * FROM part_compatibility")
        ]
        req = [RequestedPart(part_no=c, quantity=1) for c in mentioned_codes]
        verified, unresolved = resolve_parts(req, appliance["brand_id"], appliance["model_id"], cat_rows, compat_rows)
        verified_parts_out = [{"part_no": vp.part_no, "quantity": vp.quantity} for vp in verified]
        unresolved_out = [f"{u.query} ({u.reason})" for u in unresolved]
    else:
        unresolved_out = [f"{c} (model_unverified)" for c in mentioned_codes]

    extracted = {
        "fault_found": clean[:180],
        "work_done": clean,
        "parts_used": verified_parts_out,
        "advice_for_household": "Monitor appliance for 24 hours and contact your service centre if symptoms return.",
        "appliance_notes": "Close-out debrief processed.",
        "follow_up_needed": "follow" in clean.lower() or "return" in clean.lower(),
    }

    debrief_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    db.execute("DELETE FROM visit_debrief WHERE visit_id = %s", (visit_id,))
    db.execute(
        """
        INSERT INTO visit_debrief (id, centre_id, visit_id, status, language, media_ref, transcript, extracted, unresolved, confirmed_at, created_at, updated_at)
        VALUES (%s, %s, %s, 'ready', %s, %s, %s, %s, %s, NULL, %s, %s)
        """,
        (
            debrief_id,
            centre_id,
            visit_id,
            language,
            media_ref,
            clean,
            json.dumps(extracted, ensure_ascii=False),
            json.dumps(unresolved_out, ensure_ascii=False),
            now_iso,
            now_iso,
        ),
    )

    return {
        "id": debrief_id,
        "visit_id": visit_id,
        "status": "ready",
        "language": language,
        "transcript": clean,
        "extracted": extracted,
        "unresolved": unresolved_out,
        "confirmed_at": None,
    }


def confirm_debrief(db: RLSSession, visit_id: str, centre_id: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    row = db.raw_query("SELECT * FROM visit_debrief WHERE visit_id = %s", (visit_id,))
    if not row:
        raise ValueError(f"No debrief found for visit {visit_id}")
    debrief = row[0]
    db.execute(
        "UPDATE visit_debrief SET status = 'confirmed', extracted = %s, confirmed_at = %s, updated_at = %s WHERE id = %s",
        (json.dumps(extracted, ensure_ascii=False), now_iso, now_iso, debrief["id"]),
    )

    # Append technical event to appliance_event (Home Memory)
    visit = db.raw_query("SELECT * FROM visit WHERE id = %s", (visit_id,))[0]
    ticket = db.raw_query("SELECT * FROM ticket WHERE id = %s", (visit["ticket_id"],))[0]
    if ticket.get("appliance_id"):
        db.execute(
            """
            INSERT INTO appliance_event (id, appliance_id, centre_id, event_type, visibility, occurred_at, ticket_id, details)
            VALUES (%s, %s, %s, 'repair', 'technical', %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                ticket["appliance_id"],
                centre_id,
                now_iso,
                ticket["id"],
                json.dumps(extracted, ensure_ascii=False),
            ),
        )

    return {
        "id": debrief["id"],
        "visit_id": visit_id,
        "status": "confirmed",
        "language": debrief["language"],
        "transcript": debrief["transcript"],
        "extracted": extracted,
        "unresolved": debrief["unresolved"] if isinstance(debrief["unresolved"], list) else json.loads(debrief["unresolved"] or "[]"),
        "confirmed_at": now_iso,
    }
