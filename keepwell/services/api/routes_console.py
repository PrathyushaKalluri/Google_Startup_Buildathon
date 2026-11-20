"""Centre console REST routes (Contract C5.2)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from services.agents.diagnostic_agent import run_diagnostic_agent
from services.api.deps import APIError, require_console_auth
from services.api.serializers import (
    list_envelope,
    serialize_ticket_card,
    serialize_ticket_detail,
)
from services.common.auth import AuthContext
from services.common.db import get_rls_session, parse_pg_array, parse_pg_bool, parse_pg_json
from services.worker.projections import projection_store

router = APIRouter(tags=["Centre Console"])

URGENCY_ORDER = {"safety": 0, "urgent": 1, "standard": 2, "planned": 3}


class ReclassifyUrgencyRequest(BaseModel):
    urgency_class: str = Field(..., alias="class")
    reason: str

    model_config = {"populate_by_name": True}


class ReassignRequest(BaseModel):
    technician_id: str
    slot_start: str
    slot_end: str
    reason: str


class ReturnToBrandRequest(BaseModel):
    reason: str


class TicketMessageRequest(BaseModel):
    text: str


@router.get("/tickets")
def list_tickets(
    status: Optional[str] = Query(default=None),
    urgency_class: Optional[str] = Query(default=None),
    trigger: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        clauses: List[str] = []
        params: List[Any] = []
        if status:
            clauses.append("status = %s")
            params.append(status)
        if urgency_class:
            clauses.append("urgency_class = %s")
            params.append(urgency_class)
        if trigger:
            clauses.append("trigger = %s")
            params.append(trigger)

        where_sql = " AND ".join(clauses) if clauses else None
        rows = db.select("ticket", where=where_sql, params=params)

        if q:
            ql = q.lower()
            rows = [
                r
                for r in rows
                if ql in (r.get("case_card") or "").lower()
                or ql in (r.get("raw_inputs") or "").lower()
                or ql in (r.get("id") or "").lower()
                or ql in (r.get("visit_address") or "").lower()
            ]

        rows.sort(
            key=lambda r: (
                URGENCY_ORDER.get(r.get("urgency_class") or "standard", 9),
                r.get("needed_by") or "9999-12-31T23:59:59Z",
                r.get("created_at") or "",
            )
        )

        offset = int(cursor) if cursor and cursor.isdigit() else 0
        page = rows[offset : offset + limit]
        next_cursor = str(offset + limit) if (offset + limit) < len(rows) else None
        cards = [serialize_ticket_card(db, r) for r in page]
        return list_envelope(cards, next_cursor=next_cursor)


@router.get("/tickets/{ticket_id}")
def get_ticket_detail(
    ticket_id: str,
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    try:
        uuid.UUID(ticket_id)
    except ValueError:
        raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        row = db.select_one("ticket", "id = %s", (ticket_id,))
        if not row:
            raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)
        return serialize_ticket_detail(db, row)


@router.post("/tickets/{ticket_id}/reclassify-urgency")
def reclassify_urgency(
    ticket_id: str,
    body: ReclassifyUrgencyRequest,
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    if body.urgency_class not in URGENCY_ORDER:
        raise APIError("invalid_urgency_class", f"Invalid urgency class: {body.urgency_class}", status_code=400, field="class")

    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        row = db.select_one("ticket", "id = %s", (ticket_id,))
        if not row:
            raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)

        cid = row["centre_id"]
        is_safety = body.urgency_class == "safety"
        db.insert(
            "urgency_assessment",
            {
                "id": str(uuid.uuid4()),
                "centre_id": cid,
                "ticket_id": ticket_id,
                "class": body.urgency_class,
                "rule_codes": "{console_override}",
                "facts": {"override": True},
                "assessed_by": "centre_console",
                "reason": body.reason,
                "protective_steps_sent": is_safety,
                "created_at": now_iso,
            },
        )
        db.update(
            "ticket",
            {
                "urgency_class": body.urgency_class,
                "safety_flag": is_safety,
                "safety_reason": body.reason if is_safety else row.get("safety_reason"),
                "updated_at": now_iso,
            },
            "id = %s",
            (ticket_id,),
        )
        projection_store.emit_event(
            db,
            cid,
            "urgency_assessed",
            "centre",
            f"Centre reclassified urgency to {body.urgency_class}",
            detail=body.reason,
            ticket_id=ticket_id,
            payload={"class": body.urgency_class, "assessed_by": "centre_console", "reason": body.reason},
        )
        updated = db.select_one("ticket", "id = %s", (ticket_id,))
        assert updated is not None
        projection_store.project_ticket(cid, serialize_ticket_card(db, updated))
        return serialize_ticket_detail(db, updated)


@router.post("/tickets/{ticket_id}/reassign")
def reassign_ticket(
    ticket_id: str,
    body: ReassignRequest,
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        row = db.select_one("ticket", "id = %s", (ticket_id,))
        if not row:
            raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)
        cid = row["centre_id"]

        tech = db.select_one("technician", "id = %s", (body.technician_id,))
        if not tech:
            raise APIError("technician_not_found", f"Technician {body.technician_id} not found in centre", status_code=404, field="technician_id")

        prev_visits = db.select("visit", "ticket_id = %s", (ticket_id,), order_by="created_at DESC", limit=1)
        prev_tech_id = prev_visits[0]["technician_id"] if prev_visits else None

        # Mark prior chosen candidates as not_chosen
        db.update("assignment_candidate", {"outcome": "not_chosen"}, "ticket_id = %s AND outcome = 'chosen'", (ticket_id,))

        vp = db.select_one("visit_plan", "ticket_id = %s", (ticket_id,), order_by="created_at DESC")
        db.insert(
            "assignment_candidate",
            {
                "id": str(uuid.uuid4()),
                "centre_id": cid,
                "ticket_id": ticket_id,
                "visit_plan_id": vp["id"] if vp else None,
                "technician_id": body.technician_id,
                "slot_start": body.slot_start,
                "slot_end": body.slot_end,
                "rank": 1,
                "score": "100.0",
                "score_breakdown": {
                    "fix_confidence": 30,
                    "parts_readiness": 25,
                    "time_to_visit": 20,
                    "route_cost": 15,
                    "reliability": 5,
                    "household_fit": 5,
                },
                "outcome": "chosen",
                "chosen_by": "centre_console",
                "override_reason": body.reason,
                "created_at": now_iso,
            },
        )

        if prev_visits:
            visit_id = prev_visits[0]["id"]
            db.update(
                "visit",
                {
                    "technician_id": body.technician_id,
                    "planned_start": body.slot_start,
                    "planned_end": body.slot_end,
                    "updated_at": now_iso,
                },
                "id = %s",
                (visit_id,),
            )
        else:
            visit_id = str(uuid.uuid4())
            db.insert(
                "visit",
                {
                    "id": visit_id,
                    "centre_id": cid,
                    "ticket_id": ticket_id,
                    "technician_id": body.technician_id,
                    "planned_start": body.slot_start,
                    "planned_end": body.slot_end,
                    "is_return_visit": False,
                    "checklist": [],
                    "created_at": now_iso,
                    "updated_at": now_iso,
                },
            )

        db.update("ticket", {"status": "scheduled", "updated_at": now_iso}, "id = %s", (ticket_id,))
        projection_store.emit_event(
            db,
            cid,
            "reassigned",
            "centre",
            f"Reassigned to {tech['name']}",
            detail=body.reason,
            ticket_id=ticket_id,
            payload={"from": prev_tech_id, "to": body.technician_id, "to_name": tech["name"], "reason": body.reason},
        )
        projection_store.project_visit(
            cid,
            visit_id,
            {
                "ticket_id": ticket_id,
                "technician_id": body.technician_id,
                "planned_start": body.slot_start,
                "planned_end": body.slot_end,
                "status": "scheduled",
                "brief": {},
                "address_released": True,
            },
        )
        updated = db.select_one("ticket", "id = %s", (ticket_id,))
        assert updated is not None
        projection_store.project_ticket(
            cid,
            serialize_ticket_card(db, updated),
            assignee={"technician_id": body.technician_id, "name": tech["name"]},
        )
        return serialize_ticket_detail(db, updated)


@router.post("/tickets/{ticket_id}/rerun-diagnosis")
def rerun_diagnosis(
    ticket_id: str,
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        row = db.select_one("ticket", "id = %s", (ticket_id,))
        if not row:
            raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)
        cid = row["centre_id"]

        cc = parse_pg_json(row.get("case_card"), {})
        brand_id = None
        brand_name = ""
        cat_code = "ac"
        if row.get("appliance_id"):
            app_rows = db.raw_query("SELECT * FROM appliance WHERE id = %s LIMIT 1", (row["appliance_id"],))
            if app_rows:
                brand_id = app_rows[0].get("brand_id")
                cat_code = app_rows[0].get("category_code") or "ac"
                if brand_id:
                    b_rows = db.raw_query("SELECT name FROM brand WHERE id = %s LIMIT 1", (brand_id,))
                    brand_name = b_rows[0]["name"] if b_rows else ""

        existing_plans = db.select("visit_plan", "ticket_id = %s", (ticket_id,), order_by="CAST(version AS INTEGER) DESC", limit=1)
        next_ver = int(existing_plans[0]["version"]) + 1 if existing_plans else 1

        diag = run_diagnostic_agent(
            db=db,
            symptom_text=cc.get("summary") or "",
            brand_id=brand_id,
            brand_name=brand_name,
            category_code=cat_code,
            error_codes=cc.get("error_codes") or [],
            already_tried=cc.get("what_was_tried") or [],
            rerun_of=existing_plans[0]["id"] if existing_plans else "new_info",
        )
        top_hyp = diag["hypotheses"][0] if diag["hypotheses"] else None

        plan_id = str(uuid.uuid4())
        db.insert(
            "visit_plan",
            {
                "id": plan_id,
                "centre_id": cid,
                "ticket_id": ticket_id,
                "version": next_ver,
                "trigger_reason": "new_info",
                "already_tried": cc.get("what_was_tried") or [],
                "required_skills": [cat_code],
                "est_duration_p50_min": 55,
                "est_duration_p80_min": 85,
                "tools_needed": "{multimeter,screwdriver_set}",
                "requires_safety_cert": "{}",
                "access_notes": "",
                "confidence": str(top_hyp["probability"] if top_hyp else 0.5),
                "model_version": diag["model_version"],
                "created_at": now_iso,
            },
        )
        for idx, h in enumerate(diag["hypotheses"], start=1):
            db.insert(
                "plan_hypothesis",
                {
                    "id": str(uuid.uuid4()),
                    "centre_id": cid,
                    "visit_plan_id": plan_id,
                    "rank": idx,
                    "cause": h["label"],
                    "probability": str(h["probability"]),
                    "evidence": h.get("evidence", []),
                },
            )
        projection_store.emit_event(
            db,
            cid,
            "diagnosis_updated",
            "agent",
            f"Re-ran diagnosis: {top_hyp['label']}" if top_hyp else "Re-ran diagnosis",
            ticket_id=ticket_id,
            payload={
                "top_hypothesis": top_hyp["label"] if top_hyp else None,
                "probability": top_hyp["probability"] if top_hyp else 0.0,
                "rerun": True,
                "evidence": top_hyp["evidence"] if top_hyp else [],
            },
        )
        db.update("ticket", {"updated_at": now_iso}, "id = %s", (ticket_id,))
        updated = db.select_one("ticket", "id = %s", (ticket_id,))
        assert updated is not None
        return serialize_ticket_detail(db, updated)


@router.post("/tickets/{ticket_id}/return-to-brand")
def return_to_brand(
    ticket_id: str,
    body: ReturnToBrandRequest,
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        row = db.select_one("ticket", "id = %s", (ticket_id,))
        if not row:
            raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)
        cid = row["centre_id"]

        db.update(
            "ticket",
            {"status": "cancelled", "resolution": "returned_to_brand", "updated_at": now_iso},
            "id = %s",
            (ticket_id,),
        )
        if row.get("brand_referral_id"):
            db.update("brand_referral", {"status": "declined"}, "id = %s", (row["brand_referral_id"],))

        projection_store.emit_event(
            db,
            cid,
            "brand_request_declined",
            "centre",
            f"Returned to brand: {body.reason}",
            detail=body.reason,
            ticket_id=ticket_id,
            payload={"reason": body.reason},
        )
        updated = db.select_one("ticket", "id = %s", (ticket_id,))
        assert updated is not None
        return serialize_ticket_detail(db, updated)


@router.post("/tickets/{ticket_id}/message")
def send_ticket_message(
    ticket_id: str,
    body: TicketMessageRequest,
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        row = db.select_one("ticket", "id = %s", (ticket_id,))
        if not row:
            raise APIError("ticket_not_found", f"Ticket {ticket_id} not found", status_code=404)
        cid = row["centre_id"]
        hid = row["household_id"]

        msg_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO whatsapp_message (id, household_id, centre_id, ticket_id, direction, type, text, media_url, template, at, status)
            VALUES (%s, %s, %s, %s, 'out', 'text', %s, NULL, NULL, %s, 'sent')
            """,
            (msg_id, hid, cid, ticket_id, body.text, now_iso),
        )
        projection_store.project_whatsapp_message(
            hid,
            msg_id,
            {
                "direction": "out",
                "type": "text",
                "text": body.text,
                "media_url": None,
                "template": None,
                "at": now_iso,
                "ticket_id": ticket_id,
                "status": "sent",
            },
        )
        ev = projection_store.emit_event(
            db,
            cid,
            "centre_message_sent",
            "centre",
            "Message sent to household",
            detail=body.text,
            ticket_id=ticket_id,
            payload={"message_id": msg_id, "text": body.text},
        )
        return {
            "at": ev["at"],
            "type": ev["type"],
            "actor": "centre",
            "title": ev["title"],
            "detail": body.text,
            "ref": msg_id,
        }


@router.get("/centre/overview")
def centre_overview(auth: AuthContext = Depends(require_console_auth)) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        tickets = db.select("ticket")
        visits = db.select("visit")
        gates = db.select("consent_gate")
        fix_attempts = db.select("fix_attempt")
        urgencies = db.select("urgency_assessment")
        candidates = db.select("assignment_candidate")
        techs = db.select("technician", "active = TRUE")

        open_statuses = {"new", "triage", "clarifying", "self_fix", "diagnosed", "awaiting_slot", "booked", "scheduled", "in_progress", "needs_part", "completed", "escalated"}
        open_by_class = {"safety": 0, "urgent": 0, "standard": 0, "planned": 0}
        for t in tickets:
            if t.get("status") in open_statuses:
                uc = t.get("urgency_class") or "standard"
                open_by_class[uc] = open_by_class.get(uc, 0) + 1

        repair_tickets = [t for t in tickets if t.get("job_type") == "repair"]
        repair_ids = {t["id"] for t in repair_tickets}

        # First-time fix (FTF) & FVR-14
        visits_by_ticket: Dict[str, List[Dict[str, Any]]] = {}
        for v in visits:
            if v["ticket_id"] in repair_ids:
                visits_by_ticket.setdefault(v["ticket_id"], []).append(v)

        ftf_num = 0
        ftf_den = 0
        fvr_num = 0
        ticket_by_id = {t["id"]: t for t in tickets}
        for tid, vlist in visits_by_ticket.items():
            vlist.sort(key=lambda x: x.get("created_at") or "")
            first_v = vlist[0]
            if first_v.get("outcome"):
                ftf_den += 1
                if first_v.get("outcome") == "fixed" and len(vlist) == 1:
                    ftf_num += 1
                    t = ticket_by_id.get(tid, {})
                    if t.get("closure_confirmed_at") or first_v.get("closure_confirmed_at"):
                        fvr_num += 1

        ftf = round(ftf_num / ftf_den, 4) if ftf_den else 0.0
        fvr_14d = round(fvr_num / ftf_den, 4) if ftf_den else 0.0

        # Self-fix resolution
        worked_no_visit = 0
        for fa in fix_attempts:
            if fa.get("outcome") == "worked" and fa["ticket_id"] not in visits_by_ticket:
                worked_no_visit += 1
        self_fix_resolution = round(worked_no_visit / len(repair_tickets), 4) if repair_tickets else 0.0

        # Gate funnel
        g1_asked = sum(1 for g in gates if str(g.get("gate")) == "1" and g.get("answer") != "not_asked")
        g1_yes = sum(1 for g in gates if str(g.get("gate")) == "1" and g.get("answer") == "yes")
        g2_asked = sum(1 for g in gates if str(g.get("gate")) == "2" and g.get("answer") != "not_asked")
        g2_video = sum(1 for g in gates if str(g.get("gate")) == "2" and g.get("choice") == "switch_to_video")

        # Urgency agreement
        tickets_with_urg = {u["ticket_id"] for u in urgencies}
        overridden_urg = {u["ticket_id"] for u in urgencies if u.get("assessed_by") == "centre_console"}
        urgency_agreement = round(1.0 - (len(overridden_urg) / len(tickets_with_urg)), 4) if tickets_with_urg else 1.0

        # Override rate (per 100 assigned tickets)
        reassigned_tickets = {c["ticket_id"] for c in candidates if c.get("chosen_by") == "centre_console"}
        assigned_count = max(len(visits_by_ticket), len({c["ticket_id"] for c in candidates if c.get("outcome") == "chosen"}))
        override_rate = round(((len(overridden_urg) + len(reassigned_tickets)) / assigned_count) * 100.0, 2) if assigned_count else 0.0

        # Parts ready at visit
        reservations = db.select("reservation")
        ready_res = sum(1 for r in reservations if r.get("status") in ("ready", "handed_over", "confirmed"))
        parts_ready_at_visit = round(ready_res / len(reservations), 4) if reservations else 1.0

        # Jobs per technician day
        tech_days = max(len(techs), 1)
        jobs_per_technician_day = round(len(visits) / max(tech_days * 30, 1), 2)

        return {
            "open_by_class": open_by_class,
            "first_time_fix": ftf,
            "fvr_14d": fvr_14d,
            "self_fix_resolution": self_fix_resolution,
            "gate_funnel": {
                "gate1_asked": g1_asked,
                "gate1_yes": g1_yes,
                "gate2_asked": g2_asked,
                "gate2_switch_to_video": g2_video,
            },
            "urgency_agreement": urgency_agreement,
            "override_rate": override_rate,
            "parts_ready_at_visit": parts_ready_at_visit,
            "jobs_per_technician_day": jobs_per_technician_day,
        }


@router.get("/centre/technicians")
def centre_technicians(auth: AuthContext = Depends(require_console_auth)) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        rows = db.select("technician", order_by="name")
        items = [
            {
                "id": t["id"],
                "centre_id": t["centre_id"],
                "name": t["name"],
                "languages": parse_pg_array(t.get("languages")),
                "shift_start": t.get("shift_start"),
                "shift_end": t.get("shift_end"),
                "vehicle_type": t.get("vehicle_type"),
                "safety_certs": parse_pg_array(t.get("safety_certs")),
                "identity_verified": parse_pg_bool(t.get("identity_verified")),
                "active": parse_pg_bool(t.get("active")),
            }
            for t in rows
        ]
        return list_envelope(items)


@router.get("/centre/calendar")
def centre_calendar(
    date: Optional[str] = Query(default=None),
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        if date:
            visits = db.select("visit", "planned_start LIKE %s", (f"{date}%",), order_by="planned_start")
        else:
            visits = db.select("visit", order_by="planned_start DESC", limit=100)
        items = [
            {
                "visit_id": v["id"],
                "ticket_id": v["ticket_id"],
                "technician_id": v["technician_id"],
                "planned_start": v.get("planned_start"),
                "planned_end": v.get("planned_end"),
                "outcome": v.get("outcome"),
            }
            for v in visits
        ]
        return list_envelope(items)


@router.get("/centre/stock")
def centre_stock(auth: AuthContext = Depends(require_console_auth)) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        rows = db.select("stock", "centre_id IS NOT NULL")
        parts_by_id = {p["id"]: p for p in db.raw_query("SELECT id, part_no, name, mrp_paise FROM part_catalogue")}
        items = []
        for s in rows:
            p = parts_by_id.get(s.get("part_id"), {})
            items.append(
                {
                    "id": s["id"],
                    "holder_type": s.get("holder_type"),
                    "holder_id": s.get("holder_id"),
                    "part_id": s.get("part_id"),
                    "part_no": p.get("part_no"),
                    "part_name": p.get("name"),
                    "quantity": int(s.get("quantity") or 0),
                    "as_of": s.get("as_of"),
                }
            )
        return list_envelope(items)


@router.get("/centre/prices")
def centre_prices(auth: AuthContext = Depends(require_console_auth)) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        rows = db.select("centre_price", order_by="category_code, job_type")
        items = [
            {
                "id": r["id"],
                "category_code": r["category_code"],
                "job_type": r["job_type"],
                "complexity_band": r["complexity_band"],
                "visit_fee_paise": int(r.get("visit_fee_paise") or 0),
                "labour_paise": int(r.get("labour_paise") or 0),
                "valid_from": r.get("valid_from"),
                "valid_to": r.get("valid_to"),
            }
            for r in rows
        ]
        return list_envelope(items)


@router.get("/centre/overrides")
def centre_overrides(auth: AuthContext = Depends(require_console_auth)) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        urg_ov = db.select("urgency_assessment", "assessed_by = 'centre_console'", order_by="created_at DESC")
        asg_ov = db.select("assignment_candidate", "chosen_by = 'centre_console'", order_by="created_at DESC")
        items: List[Dict[str, Any]] = []
        for u in urg_ov:
            items.append(
                {
                    "kind": "urgency_reclassification",
                    "ticket_id": u["ticket_id"],
                    "value": u.get("class"),
                    "reason": u.get("reason"),
                    "at": u.get("created_at"),
                }
            )
        for a in asg_ov:
            items.append(
                {
                    "kind": "technician_reassignment",
                    "ticket_id": a["ticket_id"],
                    "value": a.get("technician_id"),
                    "reason": a.get("override_reason"),
                    "at": a.get("created_at"),
                }
            )
        items.sort(key=lambda x: x.get("at") or "", reverse=True)
        return list_envelope(items)


@router.get("/appliances/{appliance_id}/timeline")
def appliance_timeline(
    appliance_id: str,
    auth: AuthContext = Depends(require_console_auth),
) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        cid = auth.centre_id
        if not cid:
            # Platform fallback: use first linked centre or read directly
            links = db.raw_query(
                "SELECT l.centre_id FROM household_centre_link l JOIN appliance a ON a.household_id = l.household_id WHERE a.id = %s LIMIT 1",
                (appliance_id,),
            )
            cid = links[0]["centre_id"] if links else ""
        try:
            events = db.read_shared_history(appliance_id, cid, reason="console_timeline_view")
        except PermissionError as exc:
            raise APIError("forbidden", str(exc), status_code=403) from exc

        items = [
            {
                "at": e.get("occurred_at"),
                "type": e.get("event_type"),
                "actor": "centre" if e.get("centre_id") else "system",
                "title": f"Appliance {e.get('event_type')}",
                "detail": str(parse_pg_json(e.get("details"), e.get("details") or "")),
                "ref": e.get("id"),
            }
            for e in events
        ]
        return list_envelope(items)


def _serialize_safefix(db: Any, row: Dict[str, Any]) -> Dict[str, Any]:
    attempts = db.raw_query("SELECT outcome FROM fix_attempt WHERE catalogue_id = %s", (row["id"],))
    total = len(attempts)
    worked = sum(1 for a in attempts if a.get("outcome") == "worked")
    return {
        "id": row["id"],
        "code": row["code"],
        "category_code": row["category_code"],
        "brand_id": row.get("brand_id"),
        "model_series": row.get("model_series"),
        "fault_family": row.get("fault_family"),
        "title": row["title"],
        "symptom_terms": parse_pg_array(row.get("symptom_terms")),
        "steps": parse_pg_json(row.get("steps"), []),
        "step_count": int(row.get("step_count") or 0),
        "est_minutes": int(row.get("est_minutes") or 0),
        "reversible": parse_pg_bool(row.get("reversible")),
        "needs_tools": parse_pg_bool(row.get("needs_tools")),
        "opens_panel": parse_pg_bool(row.get("opens_panel")),
        "status": row.get("status"),
        "effectiveness": {
            "attempts": total,
            "worked": worked,
            "rate": round(worked / total, 4) if total else None,
        },
    }


@router.get("/safefix")
def list_safefix(auth: AuthContext = Depends(require_console_auth)) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        rows = db.raw_query("SELECT * FROM safe_fix_catalogue ORDER BY code")
        return list_envelope([_serialize_safefix(db, r) for r in rows])


@router.get("/safefix/{code}")
def get_safefix(code: str, auth: AuthContext = Depends(require_console_auth)) -> Dict[str, Any]:
    with get_rls_session(centre_id=auth.centre_id, role=auth.role) as db:
        rows = db.raw_query("SELECT * FROM safe_fix_catalogue WHERE code = %s LIMIT 1", (code,))
        if not rows:
            raise APIError("safefix_not_found", f"Safe fix {code} not found", status_code=404)
        return _serialize_safefix(db, rows[0])
