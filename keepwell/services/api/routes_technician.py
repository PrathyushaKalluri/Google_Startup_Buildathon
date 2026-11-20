"""Technician REST routes (Contract C5.2)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from services.agents.engines.pricing import compute_gst_paise, compute_variance_pct
from services.agents.memory_agent import confirm_debrief, process_spoken_debrief
from services.api.deps import APIError, otp_service, require_technician_auth
from services.api.serializers import (
    list_envelope,
    serialize_quote,
    serialize_ticket_card,
    serialize_ticket_detail,
    serialize_visit,
)
from services.common.auth import AuthContext
from services.common.config import settings
from services.common.crypto import decrypt_phone
from services.common.db import get_rls_session
from services.common.storage import storage_adapter
from services.worker.projections import projection_store

router = APIRouter(tags=["Technician"])


class LocationPingRequest(BaseModel):
    lat: float
    lon: float
    at: Optional[str] = None


class CheckInRequest(BaseModel):
    lat: float
    lon: float


class PartUsedItem(BaseModel):
    part_id: Optional[str] = None
    part_no: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    serial_no: Optional[str] = None
    source_type: str = "van"


class PartsUsedRequest(BaseModel):
    parts: List[PartUsedItem]


class VisitOutcomeRequest(BaseModel):
    outcome: str  # fixed | needs_part | customer_absent | cancelled | escalated
    outcome_notes: Optional[str] = None
    root_cause_confirmed: Optional[str] = None


class MediaUploadUrlRequest(BaseModel):
    kind: str = "debrief_audio"
    content_type: str = "audio/ogg"


class QuoteLineInput(BaseModel):
    kind: str = "labour"
    description: str
    amount_paise: int = Field(ge=0)
    payer: str = "household"
    part_id: Optional[str] = None
    quantity: int = 1


class FirmQuoteRequest(BaseModel):
    lines: List[QuoteLineInput]


class DebriefRequest(BaseModel):
    media_ref: str
    language: str = "en"
    transcript: Optional[str] = None


class DebriefConfirmRequest(BaseModel):
    extracted: Dict[str, Any]


class CloseConfirmRequest(BaseModel):
    otp_ref: str
    code: str


class DeviceRegisterRequest(BaseModel):
    token: str
    platform: str = "android"


@router.get("/technicians/me/jobs")
def my_jobs(
    date: Optional[str] = Query(default=None),
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        clauses: List[str] = []
        params: List[Any] = []
        if auth.technician_id:
            clauses.append("technician_id = ?")
            params.append(auth.technician_id)
        if date:
            clauses.append("planned_start LIKE ?")
            params.append(f"{date}%")
        where_sql = " AND ".join(clauses) if clauses else None
        visits = db.select("visit", where=where_sql, params=params, order_by="planned_start DESC", limit=50)
        items = []
        for v in visits:
            t_row = db.select_one("ticket", "id = ?", (v["ticket_id"],))
            items.append(
                {
                    "visit": serialize_visit(v),
                    "ticket": serialize_ticket_card(db, t_row) if t_row else None,
                }
            )
        return list_envelope(items)


@router.post("/technicians/me/location")
def update_my_location(
    body: LocationPingRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    now_iso = body.at or datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        tech_id = auth.technician_id or "unknown"
        cid = auth.centre_id or ""
        t_row = db.select_one("technician", "id = ?", (tech_id,)) if auth.technician_id else None
        if t_row:
            cid = t_row["centre_id"]
        if cid:
            projection_store.project_technician(
                cid,
                tech_id,
                {
                    "name": t_row["name"] if t_row else "Technician",
                    "status": "travelling",
                    "current_visit_id": None,
                    "last_location": {"lat": body.lat, "lon": body.lon},
                    "last_ping_at": now_iso,
                },
            )
    return {"status": "ok", "technician_id": auth.technician_id, "lat": body.lat, "lon": body.lon, "at": now_iso}


@router.get("/visits/{visit_id}")
def get_visit_brief(
    visit_id: str,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        ticket = db.select_one("ticket", "id = ?", (visit["ticket_id"],))
        if not ticket:
            raise APIError("ticket_not_found", f"Ticket {visit['ticket_id']} not found", status_code=404)

        detail = serialize_ticket_detail(db, ticket)
        slot_confirmed = bool(visit.get("planned_start")) and ticket.get("status") not in ("new", "triage")

        address: Optional[str] = None
        phone: Optional[str] = None
        if slot_confirmed:
            address = ticket.get("visit_address") or detail["card"]["household"]["address_line"]
            hh = db.raw_query("SELECT phone_enc FROM household WHERE id = ? LIMIT 1", (ticket["household_id"],))
            if hh and hh[0].get("phone_enc"):
                raw_enc = str(hh[0]["phone_enc"])
                if raw_enc.startswith("\\x"):
                    phone = decrypt_phone(bytes.fromhex(raw_enc[2:]))
                else:
                    phone = "+91 *****0000"
            else:
                phone = "+91 *****0000"

            # Log PII address/phone release in append-only access_log
            db.conn.execute(
                """
                INSERT INTO access_log (
                  id, actor_type, actor_id, actor_centre_id, record_table, record_id,
                  owner_centre_id, cross_centre, ticket_id, reason, occurred_at
                ) VALUES (?, 'technician', ?, ?, 'visit', ?, ?, 'f', ?, 'visit brief address and phone released', ?)
                """,
                (
                    str(uuid.uuid4()),
                    auth.technician_id or auth.user_id,
                    visit["centre_id"],
                    visit_id,
                    visit["centre_id"],
                    ticket["id"],
                    now_iso,
                ),
            )

        return {
            "visit": serialize_visit(visit),
            "ticket": detail["card"],
            "visit_plan": detail["visit_plan"],
            "already_tried": detail["tried_summary"],
            "parts": detail["visit_plan"]["parts"] if detail["visit_plan"] else [],
            "access_notes": detail["visit_plan"]["access_notes"] if detail["visit_plan"] else "",
            "address_released": slot_confirmed,
            "address": address,
            "phone": phone,
            "debrief": detail["debrief"],
            "quotes": detail["quotes"],
        }


@router.post("/visits/{visit_id}/check-in")
def visit_check_in(
    visit_id: str,
    body: CheckInRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        db.update(
            "visit",
            {
                "check_in_at": now_iso,
                "check_in_location": f"SRID=4326;POINT({body.lon} {body.lat})",
                "updated_at": now_iso,
            },
            "id = ?",
            (visit_id,),
        )
        db.update("ticket", {"status": "in_progress", "updated_at": now_iso}, "id = ?", (visit["ticket_id"],))
        updated = db.select_one("visit", "id = ?", (visit_id,))
        assert updated is not None
        return serialize_visit(updated)


@router.post("/visits/{visit_id}/parts-used")
def record_parts_used(
    visit_id: str,
    body: PartsUsedRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        cid = visit["centre_id"]
        inserted: List[Dict[str, Any]] = []
        for p in body.parts:
            part_id = p.part_id
            if not part_id and p.part_no:
                found = db.raw_query("SELECT id FROM part_catalogue WHERE part_no = ? LIMIT 1", (p.part_no,))
                if not found:
                    raise APIError("unknown_part", f"Part {p.part_no} not found in part_catalogue", status_code=400, field="part_no")
                part_id = found[0]["id"]
            if not part_id:
                raise APIError("missing_part_id", "part_id or part_no is required", status_code=400)

            rec_id = str(uuid.uuid4())
            row = {
                "id": rec_id,
                "visit_id": visit_id,
                "part_id": part_id,
                "serial_no": p.serial_no,
                "quantity": p.quantity,
                "source_type": p.source_type,
                "centre_id": cid,
            }
            db.insert("visit_part_used", row)
            inserted.append(row)
        return list_envelope(inserted)


@router.post("/visits/{visit_id}/outcome")
def record_visit_outcome(
    visit_id: str,
    body: VisitOutcomeRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        db.update(
            "visit",
            {
                "outcome": body.outcome,
                "outcome_notes": body.outcome_notes,
                "root_cause_confirmed": body.root_cause_confirmed,
                "check_out_at": now_iso,
                "updated_at": now_iso,
            },
            "id = ?",
            (visit_id,),
        )
        # Note: ticket moves to 'completed' (NOT 'closed' — closure is by OTP only!)
        new_ticket_status = "needs_part" if body.outcome == "needs_part" else "completed"
        db.update("ticket", {"status": new_ticket_status, "updated_at": now_iso}, "id = ?", (visit["ticket_id"],))
        updated = db.select_one("visit", "id = ?", (visit_id,))
        assert updated is not None
        return serialize_visit(updated)


@router.post("/visits/{visit_id}/media/upload-url")
def get_visit_media_upload_url(
    visit_id: str,
    body: MediaUploadUrlRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        ext = "ogg" if "audio" in body.content_type else "jpg"
        obj_path = f"visits/{visit_id}/{body.kind}_{uuid.uuid4().hex[:8]}.{ext}"
        return storage_adapter.generate_signed_upload_url(obj_path, content_type=body.content_type)


@router.post("/tickets/{ticket_id}/quotes")
def issue_firm_quote(
    ticket_id: str,
    body: FirmQuoteRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        ticket = db.select_one("ticket", "id = ?", (ticket_id,))
        if not ticket:
            raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)
        cid = ticket["centre_id"]

        prior_quotes = db.select("quote", "ticket_id = ?", (ticket_id,), order_by="CAST(version AS INTEGER) DESC")
        next_ver = int(prior_quotes[0]["version"]) + 1 if prior_quotes else 1

        # Compute prior estimate total for variance
        est_total = 0
        for pq in prior_quotes:
            if pq.get("quote_type") == "estimate":
                est_total = serialize_quote(db, pq)["total_paise"]
                break

        quote_id = str(uuid.uuid4())
        db.insert(
            "quote",
            {
                "id": quote_id,
                "centre_id": cid,
                "ticket_id": ticket_id,
                "version": next_ver,
                "quote_type": "firm",
                "created_at": now_iso,
            },
        )

        has_gst = any(line.kind == "tax_gst" for line in body.lines)
        taxable_hh = 0
        for line in body.lines:
            db.insert(
                "quote_line",
                {
                    "id": str(uuid.uuid4()),
                    "centre_id": cid,
                    "quote_id": quote_id,
                    "line_type": line.kind,
                    "description": line.description,
                    "part_id": line.part_id,
                    "quantity": line.quantity,
                    "amount_paise": line.amount_paise,
                    "payer": line.payer,
                },
            )
            if line.payer == "household" and line.kind != "tax_gst":
                taxable_hh += line.amount_paise

        if not has_gst and taxable_hh > 0:
            gst = compute_gst_paise(taxable_hh)
            db.insert(
                "quote_line",
                {
                    "id": str(uuid.uuid4()),
                    "centre_id": cid,
                    "quote_id": quote_id,
                    "line_type": "tax_gst",
                    "description": "GST (18%)",
                    "quantity": 1,
                    "amount_paise": gst,
                    "payer": "household",
                },
            )

        q_row = db.select_one("quote", "id = ?", (quote_id,))
        assert q_row is not None
        q_out = serialize_quote(db, q_row)
        variance_pct = compute_variance_pct(est_total, q_out["total_paise"]) if est_total else 0.0

        projection_store.emit_event(
            db,
            cid,
            "quote_issued",
            "technician",
            f"Firm quote issued: Rs {q_out['total_paise'] / 100:.2f}",
            ticket_id=ticket_id,
            payload={"type": "firm", "total_paise": q_out["total_paise"], "variance_pct": variance_pct},
        )
        return {**q_out, "variance_pct": variance_pct}


@router.post("/visits/{visit_id}/debrief")
def submit_visit_debrief(
    visit_id: str,
    body: DebriefRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        cid = visit["centre_id"]
        transcript = body.transcript or f"Spoken debrief from {body.media_ref}: replaced faulty component and tested cycle."
        debrief = process_spoken_debrief(
            db=db,
            visit_id=visit_id,
            centre_id=cid,
            transcript=transcript,
            language=body.language,
            media_ref=body.media_ref,
        )
        projection_store.emit_event(
            db,
            cid,
            "debrief_processed",
            "agent",
            f"Debrief processed ({len(debrief['unresolved'])} unresolved)",
            ticket_id=visit["ticket_id"],
            payload={"visit_id": visit_id, "unresolved_count": len(debrief["unresolved"])},
        )
        return debrief


@router.post("/visits/{visit_id}/debrief/confirm")
def confirm_visit_debrief(
    visit_id: str,
    body: DebriefConfirmRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        try:
            return confirm_debrief(db=db, visit_id=visit_id, centre_id=visit["centre_id"], extracted=body.extracted)
        except ValueError as exc:
            raise APIError("debrief_not_found", str(exc), status_code=404) from exc


@router.post("/visits/{visit_id}/close/request-otp")
def request_close_otp(
    visit_id: str,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)
        ticket = db.select_one("ticket", "id = ?", (visit["ticket_id"],))
        if not ticket:
            raise APIError("ticket_not_found", f"Ticket {visit['ticket_id']} not found", status_code=404)

        rec = otp_service.issue_otp(visit_id=visit_id, household_id=ticket["household_id"])
        db.update("visit", {"closure_otp_ref": rec.otp_ref}, "id = ?", (visit_id,))
        db.update("ticket", {"closure_otp_ref": rec.otp_ref}, "id = ?", (ticket["id"],))
        projection_store.emit_event(
            db,
            visit["centre_id"],
            "otp_sent",
            "system",
            "Closure OTP sent to household",
            ticket_id=ticket["id"],
            payload={"otp_ref": rec.otp_ref, "visit_id": visit_id},
        )
        out: Dict[str, Any] = {
            "otp_ref": rec.otp_ref,
            "visit_id": visit_id,
            "expires_at": rec.expires_at.isoformat(),
        }
        if settings.otp_provider == "sandbox":
            out["sandbox_code"] = otp_service.get_sandbox_otp(rec.otp_ref)
        return out


@router.post("/visits/{visit_id}/close/confirm")
def confirm_close_otp(
    visit_id: str,
    body: CloseConfirmRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        visit = db.select_one("visit", "id = ?", (visit_id,))
        if not visit:
            raise APIError("visit_not_found", f"Visit {visit_id} not found", status_code=404)

        res = otp_service.verify_otp(otp_ref=body.otp_ref, code=body.code)
        if not res.verified or res.visit_id != visit_id:
            raise APIError("invalid_otp", f"OTP verification failed: {res.reason}", status_code=400, field="code")

        closed_iso = (res.closed_at or datetime.now(timezone.utc)).isoformat()
        db.update(
            "visit",
            {
                "closure_otp_ref": body.otp_ref,
                "closure_confirmed_at": closed_iso,
                "outcome": visit.get("outcome") or "fixed",
                "updated_at": closed_iso,
            },
            "id = ?",
            (visit_id,),
        )
        db.update(
            "ticket",
            {
                "status": "closed",
                "resolution": "fixed_by_visit",
                "closure_otp_ref": body.otp_ref,
                "closure_confirmed_at": closed_iso,
                "closed_at": closed_iso,
                "updated_at": closed_iso,
            },
            "id = ?",
            (visit["ticket_id"],),
        )
        projection_store.emit_event(
            db,
            visit["centre_id"],
            "ticket_closed",
            "household",
            "Job closed by household OTP",
            ticket_id=visit["ticket_id"],
            payload={"resolution": "fixed_by_visit", "closure_confirmation_ref": res.closure_confirmation_ref},
        )
        updated_ticket = db.select_one("ticket", "id = ?", (visit["ticket_id"],))
        assert updated_ticket is not None
        projection_store.project_ticket(visit["centre_id"], serialize_ticket_card(db, updated_ticket))
        return {
            "closed": True,
            "visit_id": visit_id,
            "ticket_id": visit["ticket_id"],
            "closure_confirmation_ref": res.closure_confirmation_ref,
            "closed_at": closed_iso,
        }


@router.post("/devices")
def register_device(
    body: DeviceRegisterRequest,
    auth: AuthContext = Depends(require_technician_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role="platform") as db:
        dev_id = str(uuid.uuid4())
        db.conn.execute(
            """
            INSERT INTO device_token (id, centre_id, user_id, role, token, platform, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (dev_id, auth.centre_id, auth.user_id, auth.role, body.token, body.platform, now_iso),
        )
    return {"id": dev_id, "status": "registered", "platform": body.platform, "updated_at": now_iso}
