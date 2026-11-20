"""Serializers mapping Postgres/SQLite rows to exact Contract C5.1 JSON shapes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.common.db import RLSSession, parse_pg_array, parse_pg_bool, parse_pg_json


def list_envelope(items: List[Any], next_cursor: Optional[str] = None) -> Dict[str, Any]:
    return {"items": items, "next_cursor": next_cursor}


def _to_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def serialize_household_ref(db: RLSSession, hh_row: Dict[str, Any]) -> Dict[str, Any]:
    hid = hh_row["id"]
    members = db.raw_query(
        "SELECT name FROM household_member WHERE household_id = ? ORDER BY CASE role WHEN 'owner' THEN 0 ELSE 1 END, created_at LIMIT 1",
        (hid,),
    )
    display_name = members[0]["name"] if members else "Household"
    linked_cnt_rows = db.raw_query(
        "SELECT COUNT(*) AS c FROM household_centre_link WHERE household_id = ?",
        (hid,),
    )
    linked_count = _to_int(linked_cnt_rows[0]["c"]) if linked_cnt_rows else 1
    addr = hh_row.get("address_line") or ""
    locality = addr.split(",")[-1].strip() if "," in addr else (hh_row.get("pincode") or "")
    return {
        "id": hid,
        "display_name": display_name,
        "language": hh_row.get("language") or "en",
        "pincode": hh_row.get("pincode") or "",
        "locality": locality,
        "address_line": addr,
        "verified_via": hh_row.get("verified_via") or "call_line",
        "linked_centres_count": linked_count,
    }


def serialize_appliance_ref(db: RLSSession, app_row: Dict[str, Any]) -> Dict[str, Any]:
    brand_rows = db.raw_query("SELECT name FROM brand WHERE id = ? LIMIT 1", (app_row.get("brand_id"),))
    brand_name = brand_rows[0]["name"] if brand_rows else "Unknown"
    model_code = app_row.get("model_text")
    if app_row.get("model_id"):
        m_rows = db.raw_query("SELECT model_code FROM appliance_model WHERE id = ? LIMIT 1", (app_row["model_id"],))
        if m_rows:
            model_code = m_rows[0]["model_code"]
    serial = app_row.get("serial_no") or ""
    serial_masked = f"****{serial[-4:]}" if len(serial) >= 4 else (serial or None)
    return {
        "id": app_row["id"],
        "brand": brand_name,
        "category_code": app_row.get("category_code") or "ac",
        "model_code": model_code,
        "serial_masked": serial_masked,
        "identity_status": app_row.get("identity_status") or "unverified",
        "purchase_date": app_row.get("purchase_date"),
        "warranty_end": app_row.get("warranty_end"),
    }


def serialize_ticket_card(db: RLSSession, ticket_row: Dict[str, Any]) -> Dict[str, Any]:
    hh_rows = db.raw_query("SELECT * FROM household WHERE id = ? LIMIT 1", (ticket_row.get("household_id"),))
    hh_ref = serialize_household_ref(db, hh_rows[0]) if hh_rows else {
        "id": ticket_row.get("household_id") or "",
        "display_name": "Unknown",
        "language": "en",
        "pincode": "",
        "locality": "",
        "address_line": ticket_row.get("visit_address") or "",
        "verified_via": "call_line",
        "linked_centres_count": 1,
    }

    app_ref: Optional[Dict[str, Any]] = None
    if ticket_row.get("appliance_id"):
        a_rows = db.raw_query("SELECT * FROM appliance WHERE id = ? LIMIT 1", (ticket_row["appliance_id"],))
        if a_rows:
            app_ref = serialize_appliance_ref(db, a_rows[0])

    case_card = parse_pg_json(ticket_row.get("case_card"), {})
    summary = case_card.get("summary") or ""
    if not summary:
        raw_inputs = parse_pg_json(ticket_row.get("raw_inputs"), [])
        if isinstance(raw_inputs, list) and raw_inputs:
            first = raw_inputs[0]
            summary = first.get("text", "") if isinstance(first, dict) else str(first)

    safety_flag = parse_pg_bool(ticket_row.get("safety_flag"))
    flags: List[str] = []
    if safety_flag:
        flags.append("safety")
    if ticket_row.get("brand_referral_id"):
        flags.append("brand_forward")
    if ticket_row.get("retailer_handover_id"):
        flags.append("retailer_handover")
    if ticket_row.get("entitlement") == "brand_warranty":
        flags.append("warranty")

    return {
        "id": ticket_row["id"],
        "centre_id": ticket_row["centre_id"],
        "trigger": ticket_row.get("trigger") or "household_message",
        "channel": ticket_row.get("channel") or "whatsapp",
        "job_type": ticket_row.get("job_type") or "repair",
        "status": ticket_row.get("status") or "new",
        "resolution": ticket_row.get("resolution"),
        "urgency_class": ticket_row.get("urgency_class") or "standard",
        "needed_by": ticket_row.get("needed_by"),
        "safety_flag": safety_flag,
        "safety_reason": ticket_row.get("safety_reason"),
        "entitlement": ticket_row.get("entitlement") or "paid",
        "household": hh_ref,
        "appliance": app_ref,
        "complaint_summary": summary,
        "language": hh_ref.get("language") or "en",
        "created_at": ticket_row.get("created_at"),
        "updated_at": ticket_row.get("updated_at") or ticket_row.get("created_at"),
        "flags": flags,
    }


def serialize_quote(db: RLSSession, q_row: Dict[str, Any]) -> Dict[str, Any]:
    line_rows = db.raw_query("SELECT * FROM quote_line WHERE quote_id = ? ORDER BY id", (q_row["id"],))
    lines: List[Dict[str, Any]] = []
    total = 0
    household = 0
    covered = 0
    for lr in line_rows:
        amt = _to_int(lr.get("amount_paise"))
        payer = lr.get("payer") or "household"
        lines.append(
            {
                "kind": lr.get("line_type") or "labour",
                "description": lr.get("description") or "",
                "amount_paise": amt,
                "payer": payer,
            }
        )
        total += amt
        if payer == "household":
            household += amt
        else:
            covered += amt
    return {
        "id": q_row["id"],
        "version": _to_int(q_row.get("version"), 1),
        "quote_type": q_row.get("quote_type") or "estimate",
        "lines": lines,
        "total_paise": total,
        "household_paise": household,
        "covered_paise": covered,
        "approved_at": q_row.get("approved_at"),
        "approval_method": q_row.get("approval_channel"),
    }


def serialize_payment_intent(row: Dict[str, Any]) -> Dict[str, Any]:
    gpay = parse_pg_json(row.get("google_pay_json"), None) if row.get("google_pay_json") else None
    return {
        "id": row["id"],
        "quote_id": row["quote_id"],
        "amount_paise": _to_int(row.get("amount_paise")),
        "status": row.get("status") or "created",
        "method": row.get("method") or "upi_intent",
        "upi_intent_url": row.get("upi_intent_url"),
        "google_pay": gpay,
        "payment_ref": row.get("payment_ref"),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
        "paid_at": row.get("paid_at"),
    }


def serialize_visit(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "technician_id": row["technician_id"],
        "planned_start": row.get("planned_start"),
        "planned_end": row.get("planned_end"),
        "check_in_at": row.get("check_in_at"),
        "check_out_at": row.get("check_out_at"),
        "outcome": row.get("outcome"),
        "closure_confirmed_at": row.get("closure_confirmed_at"),
        "rating": _to_int(row["rating"]) if row.get("rating") is not None else None,
    }


def serialize_debrief(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "visit_id": row["visit_id"],
        "status": row.get("status") or "ready",
        "language": row.get("language") or "en",
        "transcript": row.get("transcript") or "",
        "extracted": parse_pg_json(row.get("extracted"), {}),
        "unresolved": parse_pg_json(row.get("unresolved"), []),
        "confirmed_at": row.get("confirmed_at"),
    }


def serialize_ticket_detail(db: RLSSession, ticket_row: Dict[str, Any]) -> Dict[str, Any]:
    tid = ticket_row["id"]
    cid = ticket_row["centre_id"]
    card = serialize_ticket_card(db, ticket_row)

    cc_raw = parse_pg_json(ticket_row.get("case_card"), {})
    case_card = {
        "summary": cc_raw.get("summary") or card["complaint_summary"],
        "symptoms": cc_raw.get("symptoms") or [],
        "error_codes": cc_raw.get("error_codes") or [],
        "what_was_tried": cc_raw.get("what_was_tried") or [],
        "safety_notes": cc_raw.get("safety_notes") or (ticket_row.get("safety_reason") or ""),
        "identity_notes": cc_raw.get("identity_notes") or "",
        "sources": cc_raw.get("sources") or [],
    }

    urgency_rows = db.raw_query(
        "SELECT * FROM urgency_assessment WHERE ticket_id = ? ORDER BY created_at",
        (tid,),
    )
    urgency = [
        {
            "class": u.get("class") or "standard",
            "rule_codes": parse_pg_array(u.get("rule_codes")),
            "facts": parse_pg_json(u.get("facts"), {}),
            "assessed_by": u.get("assessed_by") or "agent",
            "reason": u.get("reason") or "",
            "protective_steps_sent": parse_pg_bool(u.get("protective_steps_sent")),
            "created_at": u.get("created_at"),
        }
        for u in urgency_rows
    ]

    gate_rows = db.raw_query(
        "SELECT * FROM consent_gate WHERE ticket_id = ? ORDER BY gate, asked_at",
        (tid,),
    )
    gates = [
        {
            "gate": _to_int(g.get("gate"), 1),
            "asked_at": g.get("asked_at"),
            "answer": g.get("answer") or "not_asked",
            "choice": g.get("choice"),
            "not_asked_reason": g.get("not_asked_reason"),
        }
        for g in gate_rows
    ]

    qa_rows = db.raw_query(
        "SELECT * FROM clarifying_qa WHERE ticket_id = ? ORDER BY CAST(seq AS INTEGER), asked_at",
        (tid,),
    )
    clarifying_qa = [
        {
            "seq": _to_int(q.get("seq"), 1),
            "question": q.get("question") or "",
            "answer": q.get("answer"),
            "answer_source": q.get("answer_source"),
            "asked_at": q.get("asked_at"),
        }
        for q in qa_rows
    ]

    fa_rows = db.raw_query("SELECT * FROM fix_attempt WHERE ticket_id = ? ORDER BY offered_at", (tid,))
    fix_attempts: List[Dict[str, Any]] = []
    tried_summary: List[Dict[str, Any]] = []
    for fa in fa_rows:
        cat = db.raw_query(
            "SELECT code, title, step_count FROM safe_fix_catalogue WHERE id = ? LIMIT 1",
            (fa.get("catalogue_id"),),
        )
        cat_code = cat[0]["code"] if cat else ""
        cat_title = cat[0]["title"] if cat else ""
        step_of = _to_int(cat[0]["step_count"], 1) if cat else _to_int(fa.get("steps_done"), 1)
        item = {
            "id": fa["id"],
            "catalogue_code": cat_code,
            "title": cat_title,
            "offered_at": fa.get("offered_at"),
            "steps_done": _to_int(fa.get("steps_done"), 0),
            "of": step_of,
            "outcome": fa.get("outcome") or "not_worked",
            "household_report": fa.get("household_report") or "",
            "observed_on_video": parse_pg_bool(fa.get("observed_on_video")),
        }
        fix_attempts.append(item)
        tried_summary.append(
            {
                "fix": cat_code,
                "title": cat_title,
                "steps_done": item["steps_done"],
                "of": step_of,
                "outcome": item["outcome"],
                "seen_on_video": item["observed_on_video"],
            }
        )

    vp_rows = db.raw_query(
        "SELECT * FROM visit_plan WHERE ticket_id = ? ORDER BY CAST(version AS INTEGER) DESC, created_at DESC LIMIT 1",
        (tid,),
    )
    visit_plan: Optional[Dict[str, Any]] = None
    diagnosis: Optional[Dict[str, Any]] = None
    if vp_rows:
        vp = vp_rows[0]
        hyps = db.raw_query(
            "SELECT * FROM plan_hypothesis WHERE visit_plan_id = ? ORDER BY CAST(rank AS INTEGER)",
            (vp["id"],),
        )
        diagnosis = {
            "hypotheses": [
                {
                    "fault_key": f"rank_{h.get('rank')}",
                    "label": h.get("cause") or "",
                    "probability": _to_float(h.get("probability"), 0.5),
                    "evidence": parse_pg_json(h.get("evidence"), []),
                    "citations": case_card.get("sources") or [],
                }
                for h in hyps
            ],
            "abstained": len(hyps) == 0,
            "reason": None if hyps else "insufficient_evidence",
            "rerun_of": vp.get("trigger_reason") if vp.get("trigger_reason") == "self_fix_failed" else None,
            "model_version": vp.get("model_version") or "keepwell-diag-v1",
        }

        pp_rows = db.raw_query("SELECT * FROM plan_part WHERE visit_plan_id = ?", (vp["id"],))
        parts_list: List[Dict[str, Any]] = []
        for pp in pp_rows:
            pcat = db.raw_query("SELECT part_no, name FROM part_catalogue WHERE id = ? LIMIT 1", (pp.get("part_id"),))
            parts_list.append(
                {
                    "part_no": pcat[0]["part_no"] if pcat else (pp.get("part_id") or ""),
                    "name": pcat[0]["name"] if pcat else "",
                    "probability": _to_float(pp.get("probability"), 0.8),
                    "quantity": _to_int(pp.get("quantity"), 1),
                    "source_ladder": "centre",
                    "ready": True,
                }
            )

        visit_plan = {
            "id": vp["id"],
            "version": _to_int(vp.get("version"), 1),
            "trigger_reason": vp.get("trigger_reason") or "initial",
            "already_tried": parse_pg_json(vp.get("already_tried"), tried_summary),
            "required_skills": parse_pg_json(vp.get("required_skills"), []),
            "est_duration_p50_min": _to_int(vp.get("est_duration_p50_min"), 50),
            "est_duration_p80_min": _to_int(vp.get("est_duration_p80_min"), 80),
            "tools_needed": parse_pg_array(vp.get("tools_needed")),
            "requires_safety_cert": parse_pg_array(vp.get("requires_safety_cert")),
            "parts": parts_list,
            "access_notes": vp.get("access_notes") or "",
            "confidence": _to_float(vp.get("confidence"), 0.75),
        }

    cand_rows = db.raw_query(
        "SELECT * FROM assignment_candidate WHERE ticket_id = ? ORDER BY CAST(rank AS INTEGER), created_at",
        (tid,),
    )
    candidates: List[Dict[str, Any]] = []
    for c in cand_rows:
        t_rows = db.raw_query("SELECT name FROM technician WHERE id = ? LIMIT 1", (c.get("technician_id"),))
        t_name = t_rows[0]["name"] if t_rows else "Technician"
        bd = parse_pg_json(c.get("score_breakdown"), {})
        candidates.append(
            {
                "technician_id": c["technician_id"],
                "name": t_name,
                "rank": _to_int(c.get("rank"), 1),
                "score": _to_float(c.get("score"), 0.0),
                "score_breakdown": {
                    "fix_confidence": _to_float(bd.get("fix_confidence")),
                    "parts_readiness": _to_float(bd.get("parts_readiness")),
                    "time_to_visit": _to_float(bd.get("time_to_visit")),
                    "route_cost": _to_float(bd.get("route_cost")),
                    "reliability": _to_float(bd.get("reliability")),
                    "household_fit": _to_float(bd.get("household_fit")),
                },
                "slot_start": c.get("slot_start"),
                "slot_end": c.get("slot_end"),
                "outcome": c.get("outcome") or "proposed",
                "chosen_by": c.get("chosen_by") or "agent",
                "override_reason": c.get("override_reason"),
                "why": c.get("override_reason") or f"Ranked #{c.get('rank')} inside centre",
            }
        )

    sp_rows = db.raw_query("SELECT * FROM slot_proposal WHERE ticket_id = ? ORDER BY shown_at", (tid,))
    slot_proposals = [
        {
            "slot_start": sp.get("slot_start"),
            "slot_end": sp.get("slot_end"),
            "price_low_paise": _to_int(sp.get("price_low_paise")),
            "price_high_paise": _to_int(sp.get("price_high_paise")),
            "shown_at": sp.get("shown_at"),
            "accepted": parse_pg_bool(sp.get("accepted")),
        }
        for sp in sp_rows
    ]

    q_rows = db.raw_query("SELECT * FROM quote WHERE ticket_id = ? ORDER BY CAST(version AS INTEGER)", (tid,))
    quotes = [serialize_quote(db, q) for q in q_rows]

    p_rows = db.raw_query("SELECT * FROM payment_intent WHERE ticket_id = ? ORDER BY created_at", (tid,))
    payments = [serialize_payment_intent(p) for p in p_rows]

    v_rows = db.raw_query("SELECT * FROM visit WHERE ticket_id = ? ORDER BY created_at DESC LIMIT 1", (tid,))
    visit = serialize_visit(v_rows[0]) if v_rows else None

    debrief: Optional[Dict[str, Any]] = None
    if v_rows:
        d_rows = db.raw_query("SELECT * FROM visit_debrief WHERE visit_id = ? LIMIT 1", (v_rows[0]["id"],))
        if d_rows:
            debrief = serialize_debrief(d_rows[0])

    ev_rows = db.raw_query(
        "SELECT * FROM outbox_event WHERE ticket_id = ? ORDER BY created_at",
        (tid,),
    )
    timeline = [
        {
            "at": e.get("created_at"),
            "type": e.get("event_type"),
            "actor": e.get("actor") or "system",
            "title": e.get("title") or "",
            "detail": e.get("detail") or "",
            "ref": e.get("id"),
        }
        for e in ev_rows
    ]

    auth_level = "none"
    if ticket_row.get("appliance_id"):
        a_rows = db.raw_query("SELECT brand_id FROM appliance WHERE id = ? LIMIT 1", (ticket_row["appliance_id"],))
        if a_rows and a_rows[0].get("brand_id"):
            auth_level = db.centre_authority(cid, a_rows[0]["brand_id"], on_date="2026-11-21")

    authority = {
        "level": auth_level,
        "decision": "return_to_brand" if ticket_row.get("status") == "cancelled" and ticket_row.get("brand_referral_id") else "proceed",
    }

    return {
        "card": card,
        "case_card": case_card,
        "urgency": urgency,
        "gates": gates,
        "clarifying_qa": clarifying_qa,
        "fix_attempts": fix_attempts,
        "tried_summary": tried_summary,
        "diagnosis": diagnosis,
        "visit_plan": visit_plan,
        "candidates": candidates,
        "slot_proposals": slot_proposals,
        "quotes": quotes,
        "payments": payments,
        "debrief": debrief,
        "visit": visit,
        "timeline": timeline,
        "authority": authority,
    }
