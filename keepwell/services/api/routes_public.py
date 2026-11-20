"""Public household REST routes (Contract C5.2) — signed expiring magic tokens, no accounts."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.agents.engines.payments import (
    PaymentIntentModel,
    complete_sandbox_payment,
    create_payment_intent,
)
from services.api.deps import APIError, otp_service
from services.api.serializers import (
    serialize_appliance_ref,
    serialize_household_ref,
    serialize_payment_intent,
    serialize_quote,
    serialize_ticket_card,
)
from services.common.auth import mint_household_custom_token
from services.common.config import settings
from services.common.crypto import verify_magic_token
from services.common.db import RLSSession, get_rls_session, parse_pg_json
from services.worker.projections import projection_store

router = APIRouter(prefix="/public", tags=["Public Household"])


class PublicSessionRequest(BaseModel):
    magic_token: str


class PayIntentRequest(BaseModel):
    method: Literal["upi_intent", "google_pay"] = "upi_intent"


class SandboxCompleteRequest(BaseModel):
    payment_id: str
    result: Literal["success", "failure"] = "success"


class PublicOtpConfirmRequest(BaseModel):
    otp_ref: str
    code: str


def _verify_token_or_401(token: str) -> Dict[str, Any]:
    try:
        return verify_magic_token(token)
    except ValueError as exc:
        raise APIError("invalid_magic_token", str(exc), status_code=401) from exc


def _resolve_quote_from_token(db: RLSSession, claims: Dict[str, Any]) -> Dict[str, Any]:
    sub = claims.get("sub", "")
    scope = claims.get("scope", "")
    # Token may be scoped directly to a quote_id, ticket_id, or household_id
    if scope == "quote" or claims.get("quote_id"):
        qid = claims.get("quote_id") or sub
        rows = db.raw_query("SELECT * FROM quote WHERE id = ? LIMIT 1", (qid,))
        if rows:
            return rows[0]
    if scope == "ticket" or claims.get("ticket_id"):
        tid = claims.get("ticket_id") or sub
        rows = db.raw_query("SELECT * FROM quote WHERE ticket_id = ? ORDER BY CAST(version AS INTEGER) DESC LIMIT 1", (tid,))
        if rows:
            return rows[0]
    # Fallback: treat sub as quote_id first, then household_id
    rows = db.raw_query("SELECT * FROM quote WHERE id = ? LIMIT 1", (sub,))
    if rows:
        return rows[0]
    hh_id = claims.get("household_id") or sub
    rows = db.raw_query(
        """
        SELECT q.* FROM quote q
        JOIN ticket t ON t.id = q.ticket_id
        WHERE t.household_id = ?
        ORDER BY q.created_at DESC, CAST(q.version AS INTEGER) DESC
        LIMIT 1
        """,
        (hh_id,),
    )
    if rows:
        return rows[0]
    raise APIError("quote_not_found", "No quote found for this token", status_code=404)


@router.post("/session")
def create_public_session(body: PublicSessionRequest) -> Dict[str, Any]:
    claims = _verify_token_or_401(body.magic_token)
    household_id = claims.get("household_id") or claims.get("sub")
    if not household_id:
        raise APIError("invalid_magic_token", "Token does not reference a household", status_code=401)
    ttl = 3600
    custom_token = mint_household_custom_token(household_id, ttl_seconds=ttl)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    return {
        "firebase_custom_token": custom_token,
        "household_id": household_id,
        "expires_at": expires_at,
    }


@router.get("/home/{token}")
def get_home_memory(token: str) -> Dict[str, Any]:
    claims = _verify_token_or_401(token)
    household_id = claims.get("household_id") or claims.get("sub")
    with get_rls_session(role="platform") as db:
        hh_rows = db.raw_query("SELECT * FROM household WHERE id = ? LIMIT 1", (household_id,))
        if not hh_rows:
            raise APIError("household_not_found", f"Household {household_id} not found", status_code=404)
        hh_ref = serialize_household_ref(db, hh_rows[0])

        app_rows = db.raw_query("SELECT * FROM appliance WHERE household_id = ? ORDER BY created_at", (household_id,))
        appliances = [serialize_appliance_ref(db, a) for a in app_rows]

        app_ids = [a["id"] for a in app_rows]
        timeline: List[Dict[str, Any]] = []
        if app_ids:
            placeholders = ", ".join("?" for _ in app_ids)
            ev_rows = db.raw_query(
                f"SELECT * FROM appliance_event WHERE appliance_id IN ({placeholders}) ORDER BY occurred_at DESC LIMIT 100",
                app_ids,
            )
            timeline = [
                {
                    "at": e.get("occurred_at"),
                    "type": e.get("event_type"),
                    "actor": "centre" if e.get("centre_id") else "system",
                    "title": f"{e.get('event_type')} event",
                    "detail": str(parse_pg_json(e.get("details"), e.get("details") or "")),
                    "ref": e.get("id"),
                }
                for e in ev_rows
            ]

        next_due = [
            {
                "appliance_id": a["id"],
                "category_code": a.get("category_code"),
                "next_due_at": a.get("next_due_at"),
                "last_service_at": a.get("last_service_at"),
            }
            for a in app_rows
            if a.get("next_due_at")
        ]
        warranty = [
            {
                "appliance_id": a["id"],
                "category_code": a.get("category_code"),
                "warranty_start": a.get("warranty_start"),
                "warranty_end": a.get("warranty_end"),
                "active": bool(a.get("warranty_end") and a["warranty_end"] >= "2026-11-21"),
            }
            for a in app_rows
        ]

        return {
            "household": hh_ref,
            "appliances": appliances,
            "timeline": timeline,
            "next_due": next_due,
            "warranty": warranty,
        }


@router.get("/quotes/{token}")
def get_public_quote(token: str) -> Dict[str, Any]:
    claims = _verify_token_or_401(token)
    with get_rls_session(role="platform") as db:
        q_row = _resolve_quote_from_token(db, claims)
        q_out = serialize_quote(db, q_row)
        p_rows = db.raw_query(
            "SELECT * FROM payment_intent WHERE quote_id = ? ORDER BY created_at DESC LIMIT 1",
            (q_row["id"],),
        )
        return {
            **q_out,
            "payment": serialize_payment_intent(p_rows[0]) if p_rows else None,
        }


@router.post("/quotes/{token}/approve")
def approve_public_quote(token: str) -> Dict[str, Any]:
    claims = _verify_token_or_401(token)
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(role="platform") as db:
        q_row = _resolve_quote_from_token(db, claims)
        db.conn.execute(
            "UPDATE quote SET approved_at = ?, approval_channel = 'web_link', approval_ref = ? WHERE id = ?",
            (now_iso, f"APR-{uuid.uuid4().hex[:8].upper()}", q_row["id"]),
        )
        projection_store.emit_event(
            db,
            q_row["centre_id"],
            "quote_approved",
            "household",
            "Household approved the quote",
            ticket_id=q_row["ticket_id"],
            payload={"quote_id": q_row["id"], "approval_method": "web_link"},
        )
        updated = db.raw_query("SELECT * FROM quote WHERE id = ? LIMIT 1", (q_row["id"],))[0]
        return serialize_quote(db, updated)


@router.post("/otp/{token}/confirm")
def public_confirm_otp(token: str, body: PublicOtpConfirmRequest) -> Dict[str, Any]:
    _verify_token_or_401(token)
    res = otp_service.verify_otp(otp_ref=body.otp_ref, code=body.code)
    if not res.verified:
        raise APIError("invalid_otp", f"OTP verification failed: {res.reason}", status_code=400, field="code")

    closed_iso = (res.closed_at or datetime.now(timezone.utc)).isoformat()
    with get_rls_session(role="platform") as db:
        v_rows = db.raw_query("SELECT * FROM visit WHERE id = ? LIMIT 1", (res.visit_id,))
        if not v_rows:
            raise APIError("visit_not_found", f"Visit {res.visit_id} not found", status_code=404)
        visit = v_rows[0]
        db.conn.execute(
            "UPDATE visit SET closure_otp_ref = ?, closure_confirmed_at = ?, outcome = COALESCE(outcome, 'fixed'), updated_at = ? WHERE id = ?",
            (body.otp_ref, closed_iso, closed_iso, visit["id"]),
        )
        db.conn.execute(
            "UPDATE ticket SET status = 'closed', resolution = 'fixed_by_visit', closure_otp_ref = ?, closure_confirmed_at = ?, closed_at = ?, updated_at = ? WHERE id = ?",
            (body.otp_ref, closed_iso, closed_iso, closed_iso, visit["ticket_id"]),
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
        t_row = db.raw_query("SELECT * FROM ticket WHERE id = ? LIMIT 1", (visit["ticket_id"],))[0]
        projection_store.project_ticket(visit["centre_id"], serialize_ticket_card(db, t_row))
        return {
            "closed": True,
            "visit_id": visit["id"],
            "ticket_id": visit["ticket_id"],
            "closure_confirmation_ref": res.closure_confirmation_ref,
            "closed_at": closed_iso,
        }


@router.post("/quotes/{token}/pay-intent")
def create_public_pay_intent(token: str, body: PayIntentRequest) -> Dict[str, Any]:
    claims = _verify_token_or_401(token)
    with get_rls_session(role="platform") as db:
        q_row = _resolve_quote_from_token(db, claims)
        q_ser = serialize_quote(db, q_row)
        amount = q_ser["household_paise"] or q_ser["total_paise"]
        if amount <= 0:
            raise APIError("zero_payable_amount", "Quote has no household payable balance", status_code=400)

        c_rows = db.raw_query("SELECT name FROM service_centre WHERE id = ? LIMIT 1", (q_row["centre_id"],))
        merchant_name = c_rows[0]["name"] if c_rows else "Keepwell Service Centre"

        intent = create_payment_intent(
            quote_id=q_row["id"],
            amount_paise=amount,
            method=body.method,
            upi_vpa=settings.upi_vpa,
            merchant_name=merchant_name,
            google_pay_environment=settings.google_pay_environment,  # type: ignore[arg-type]
            google_pay_merchant_id=settings.google_pay_merchant_id,
            google_pay_gateway=settings.google_pay_gateway,
            google_pay_gateway_merchant_id=settings.google_pay_gateway_merchant_id,
        )

        gpay_json = json.dumps(intent.google_pay.model_dump()) if intent.google_pay else None
        db.conn.execute(
            """
            INSERT INTO payment_intent (
              id, centre_id, quote_id, ticket_id, amount_paise, status, method,
              upi_intent_url, google_pay_json, payment_ref, created_at, expires_at, paid_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL)
            """,
            (
                intent.id,
                q_row["centre_id"],
                q_row["id"],
                q_row["ticket_id"],
                str(intent.amount_paise),
                intent.status,
                intent.method,
                intent.upi_intent_url,
                gpay_json,
                intent.created_at.isoformat(),
                intent.expires_at.isoformat(),
            ),
        )
        projection_store.emit_event(
            db,
            q_row["centre_id"],
            "payment_initiated",
            "household",
            f"Payment initiated via {intent.method} (Rs {intent.amount_paise / 100:.2f})",
            ticket_id=q_row["ticket_id"],
            payload={"payment_id": intent.id, "method": intent.method, "amount_paise": intent.amount_paise},
        )
        row = db.raw_query("SELECT * FROM payment_intent WHERE id = ? LIMIT 1", (intent.id,))[0]
        return serialize_payment_intent(row)


@router.get("/quotes/{token}/payment")
def get_public_payment(token: str) -> Dict[str, Any]:
    claims = _verify_token_or_401(token)
    with get_rls_session(role="platform") as db:
        q_row = _resolve_quote_from_token(db, claims)
        p_rows = db.raw_query(
            "SELECT * FROM payment_intent WHERE quote_id = ? ORDER BY created_at DESC LIMIT 1",
            (q_row["id"],),
        )
        if not p_rows:
            raise APIError("payment_not_found", "No payment intent found for this quote", status_code=404)
        return serialize_payment_intent(p_rows[0])


@router.post("/quotes/{token}/payment/sandbox-complete")
def sandbox_complete_public_payment(token: str, body: SandboxCompleteRequest) -> Dict[str, Any]:
    if settings.payment_mode != "sandbox":
        raise APIError("sandbox_disabled", "Sandbox payment completion is disabled outside sandbox mode", status_code=403)
    _verify_token_or_401(token)

    with get_rls_session(role="platform") as db:
        p_rows = db.raw_query("SELECT * FROM payment_intent WHERE id = ? LIMIT 1", (body.payment_id,))
        if not p_rows:
            raise APIError("payment_not_found", f"Payment intent {body.payment_id} not found", status_code=404)
        p_row = p_rows[0]

        intent_model = PaymentIntentModel(
            id=p_row["id"],
            quote_id=p_row["quote_id"],
            amount_paise=int(p_row["amount_paise"]),
            status=p_row["status"],
            method=p_row["method"],
            upi_intent_url=p_row.get("upi_intent_url"),
            google_pay=parse_pg_json(p_row["google_pay_json"]) if p_row.get("google_pay_json") else None,
            payment_ref=p_row.get("payment_ref"),
            created_at=datetime.fromisoformat(p_row["created_at"]),
            expires_at=datetime.fromisoformat(p_row["expires_at"]),
        )
        updated = complete_sandbox_payment(intent_model, result=body.result, payment_mode=settings.payment_mode)
        paid_iso = updated.paid_at.isoformat() if updated.paid_at else None

        db.conn.execute(
            "UPDATE payment_intent SET status = ?, payment_ref = ?, paid_at = ? WHERE id = ?",
            (updated.status, updated.payment_ref, paid_iso, updated.id),
        )

        # Update or insert household settlement_line — NEVER close the ticket!
        if updated.status == "paid":
            existing_sl = db.raw_query(
                "SELECT id FROM settlement_line WHERE ticket_id = ? AND party_type = 'household' LIMIT 1",
                (p_row["ticket_id"],),
            )
            if existing_sl:
                db.conn.execute(
                    "UPDATE settlement_line SET status = 'settled', payment_ref = ?, settled_at = ? WHERE id = ?",
                    (updated.payment_ref, paid_iso, existing_sl[0]["id"]),
                )
            else:
                db.conn.execute(
                    """
                    INSERT INTO settlement_line (id, ticket_id, party_type, party_id, direction, amount_paise, status, payment_ref, due_at, settled_at, centre_id)
                    VALUES (?, ?, 'household', NULL, 'receivable', ?, 'settled', ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        p_row["ticket_id"],
                        str(updated.amount_paise),
                        updated.payment_ref,
                        paid_iso,
                        paid_iso,
                        p_row["centre_id"],
                    ),
                )
            projection_store.emit_event(
                db,
                p_row["centre_id"],
                "payment_confirmed",
                "system",
                f"Payment confirmed ({updated.payment_ref})",
                ticket_id=p_row["ticket_id"],
                payload={"payment_id": updated.id, "payment_ref": updated.payment_ref, "amount_paise": updated.amount_paise},
            )
        else:
            projection_store.emit_event(
                db,
                p_row["centre_id"],
                "payment_failed",
                "system",
                "Sandbox payment failed",
                ticket_id=p_row["ticket_id"],
                payload={"payment_id": updated.id, "reason": "sandbox_failure"},
            )

        refreshed = db.raw_query("SELECT * FROM payment_intent WHERE id = ? LIMIT 1", (updated.id,))[0]
        return serialize_payment_intent(refreshed)
