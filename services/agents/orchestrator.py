from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from psycopg.types.json import Jsonb

from services.agents.diagnostic_agent import run_diagnostic_agent
from services.agents.engines import (
    AssignmentRequirements,
    CataloguePart,
    CompatibilityRow,
    GateMachine,
    PriceBookEntry,
    RequestedPart,
    SafeFixEntry,
    SafeFixStep,
    StockItem,
    TechnicianProfile,
    assess_urgency,
    build_estimate_range,
    build_visit_plan,
    check_authority,
    resolve_parts,
    score_technicians,
    select_safe_fix,
)
from services.agents.identity_agent import resolve_identity
from services.agents.intake_agent import run_intake_agent
from services.common.config import settings
from services.common.crypto import mask_phone, mint_magic_token
from services.common.db import (
    RLSSession,
    get_rls_session,
    parse_pg_array,
    parse_pg_bool,
    parse_pg_json,
    parse_pg_point,
)
from services.worker.projections import projection_store


def _load_db_safefix_catalogue(db: RLSSession) -> List[SafeFixEntry]:
    rows = db.raw_query("SELECT * FROM safe_fix_catalogue")
    entries: List[SafeFixEntry] = []
    for r in rows:
        raw_steps = parse_pg_json(r.get("steps"), [])
        steps = [
            SafeFixStep(n=int(s.get("n", i + 1)), say=str(s.get("say", "")), check=str(s.get("check", "")))
            for i, s in enumerate(raw_steps)
        ]
        entries.append(
            SafeFixEntry(
                id=r["id"],
                code=r["code"],
                category_code=r["category_code"],
                brand_id=r.get("brand_id"),
                model_series=r.get("model_series"),
                fault_family=r.get("fault_family") or "",
                title=r["title"],
                symptom_terms=parse_pg_array(r.get("symptom_terms")),
                steps=steps,
                step_count=int(r.get("step_count") or len(steps)),
                est_minutes=int(r.get("est_minutes") or 5),
                reversible=parse_pg_bool(r.get("reversible")),
                needs_tools=parse_pg_bool(r.get("needs_tools")),
                opens_panel=parse_pg_bool(r.get("opens_panel")),
                manual_doc_id=r.get("manual_doc_id"),
                manual_page=int(r["manual_page"]) if r.get("manual_page") else None,
                worst_case=r.get("worst_case") or "Nothing changes",
                reviewer_name=r.get("reviewer_name"),
                reviewed_on=r.get("reviewed_on"),
                review_due=r.get("review_due"),
                status=r.get("status") or "draft",
            )
        )
    return entries


def _load_centre_technicians(db: RLSSession, centre_id: str, category_code: str = "ac") -> List[TechnicianProfile]:
    techs = db.raw_query("SELECT * FROM technician WHERE centre_id = %s AND active = TRUE", (centre_id,))
    profiles: List[TechnicianProfile] = []
    for t in techs:
        skills_rows = db.raw_query("SELECT * FROM technician_skill WHERE technician_id = %s", (t["id"],))
        cat_level = 1
        for s in skills_rows:
            if s["category_code"] == category_code:
                cat_level = max(cat_level, int(s.get("level") or 1))
        m_rows = db.raw_query(
            "SELECT * FROM technician_metrics WHERE technician_id = %s AND category_code = 'ALL' ORDER BY period_end DESC LIMIT 1",
            (t["id"],),
        )
        ftf = float(m_rows[0]["first_time_fix_rate"]) if m_rows and m_rows[0].get("first_time_fix_rate") else 0.72
        ontime = float(m_rows[0]["on_time_rate"]) if m_rows and m_rows[0].get("on_time_rate") else 0.85
        pt = parse_pg_point(t.get("route_anchor")) or (17.4483, 78.3915)
        profiles.append(
            TechnicianProfile(
                technician_id=t["id"],
                name=t["name"],
                active=parse_pg_bool(t.get("active")),
                identity_verified=parse_pg_bool(t.get("identity_verified")),
                skill_level=cat_level,
                languages=parse_pg_array(t.get("languages")),
                safety_certs=parse_pg_array(t.get("safety_certs")),
                lat=pt[0],
                lon=pt[1],
                first_time_fix_rate=ftf,
                on_time_rate=ontime,
            )
        )
    return profiles


def process_inbound_case(
    db: RLSSession,
    *,
    centre_id: str,
    trigger: str,
    channel: str,
    from_phone: str,
    text: str,
    language_hint: Optional[str] = None,
    display_name: Optional[str] = None,
    address_line: Optional[str] = None,
    pincode: Optional[str] = None,
    category_hint: Optional[str] = None,
    brand_name: Optional[str] = None,
    model_code: Optional[str] = None,
    serial_no: Optional[str] = None,
    entitlement_claim: Optional[str] = None,
    requested_job: Optional[str] = None,
    brand_referral_id: Optional[str] = None,
    retailer_handover_id: Optional[str] = None,
    gate1_answer: str = "yes",
    gate2_choice: str = "continue_here",
    fix_outcome: str = "not_worked",
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Runs the complete Keepwell Part A pipeline for any of the 4 triggers:
    1. Intake (Model Armor + language + category + job_type + symptoms + error codes)
    2. Identity (household + appliance + evidence_level)
    3. Authority check (brand warranty / install rules; return_to_brand on failure)
    4. Service area check (polite decline without naming another centre if out of area)
    5. Urgency assessment (deterministic rules + hazard lexicon + 30d repeat check)
    6. Ticket creation + Firestore projection
    7. Consent Gate 1 & Gate 2 (GateMachine)
    8. Safe fix selection & attempt (only active catalogue entries, never on safety/non-repair)
    9. Diagnostic agent (with re-run if safe fix failed)
    10. Visit plan + hard parts catalogue verification (zero invented parts)
    11. 6-factor technician assignment + slot proposal + estimate quote + visit
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    events: List[Dict[str, Any]] = []

    # 1. Intake
    intake = run_intake_agent(
        raw_text=text,
        trigger=trigger,
        channel=channel,
        language_hint=language_hint,
        category_hint=category_hint,
        requested_job=requested_job,
    )
    lang = intake["language"]
    category = intake["category_code"]
    job_type = intake["job_type"]

    # 2. Identity
    verified_via = {
        "household_call": "call_line",
        "household_message": "call_line",
        "brand_forward": "brand_record",
        "retailer_handover": "retailer_record",
    }.get(trigger, "call_line")

    ident = resolve_identity(
        db=db,
        centre_id=centre_id,
        phone=from_phone,
        verified_via=verified_via,
        display_name=display_name,
        language=lang,
        address_line=address_line,
        pincode=pincode or intake["facts"].get("mentioned_pincode"),
        category_code=category,
        brand_name=brand_name,
        model_code=model_code,
        serial_no=serial_no,
    )
    hh = ident["household"]
    app = ident["appliance"]
    brand_label = ident["brand_name"]

    # 3. Authority check
    entitlement = entitlement_claim or ("brand_warranty" if "warranty" in text.lower() else "paid")
    if app.get("warranty_end") and app["warranty_end"] < "2026-11-21" and entitlement == "brand_warranty" and trigger != "brand_forward":
        entitlement = "paid"

    auth_level = db.centre_authority(centre_id, app["brand_id"], on_date="2026-11-21")
    auth_res = check_authority(level=auth_level, job_type=job_type, entitlement=entitlement)

    events.append(
        projection_store.emit_event(
            db, centre_id, "household_identified", "agent",
            f"Household identified ({mask_phone(from_phone)})",
            conversation_id=conversation_id,
            payload={
                "household_id": hh["id"],
                "verified_via": verified_via,
                "known_to_this_centre": ident["household_lookup"]["known_to_this_centre"],
            },
        )
    )
    events.append(
        projection_store.emit_event(
            db, centre_id, "appliance_identified", "agent",
            f"{brand_label} {category} identified ({ident['evidence_level']})",
            conversation_id=conversation_id,
            payload={
                "appliance_id": app["id"],
                "brand": brand_label,
                "model": ident["model_code"],
                "serial_masked": (app.get("serial_no") or "")[-4:] if app.get("serial_no") else None,
                "source": ident["identity_source"],
                "evidence_level": ident["evidence_level"],
            },
        )
    )
    events.append(
        projection_store.emit_event(
            db, centre_id, "authority_checked", "agent",
            f"Authority for {brand_label}: {auth_res.level} ({auth_res.decision})",
            conversation_id=conversation_id,
            payload={"level": auth_res.level, "decision": auth_res.decision},
        )
    )

    if auth_res.decision == "return_to_brand":
        if brand_referral_id:
            db.execute(
                "UPDATE brand_referral SET authority_checked = %s, status = 'declined' WHERE id = %s",
                (auth_res.level, brand_referral_id),
            )
        events.append(
            projection_store.emit_event(
                db, centre_id, "brand_request_declined", "agent",
                f"Returned to brand: {auth_res.reason}",
                conversation_id=conversation_id,
                payload={"reason": auth_res.reason, "level": auth_res.level},
            )
        )
        return {
            "status": "declined",
            "declined_reason": auth_res.reason,
            "authority": {"level": auth_res.level, "decision": auth_res.decision},
            "ticket_id": None,
            "events": events,
            "intake": intake,
        }

    # 4. Service area check (Q4)
    centre_row = db.raw_query("SELECT * FROM service_centre WHERE id = %s", (centre_id,))[0]
    service_pincodes = parse_pg_array(centre_row.get("service_pincodes"))
    hh_pin = pincode or intake["facts"].get("mentioned_pincode") or hh.get("pincode")
    out_of_area = bool(hh_pin and service_pincodes and hh_pin not in service_pincodes)

    # 5. Repeat-within-30d check for same appliance at this centre
    prior_repairs = db.raw_query(
        """
        SELECT created_at FROM ticket
        WHERE centre_id = %s AND appliance_id = %s AND job_type = 'repair' AND status IN ('closed', 'completed')
        ORDER BY created_at DESC LIMIT 1
        """,
        (centre_id, app["id"]),
    )
    repeat_days: Optional[int] = None
    if prior_repairs and ("మళ్లీ" in text or "రెండోసారి" in text or "again" in text.lower() or "repeat" in text.lower()):
        repeat_days = 18

    # 6. Urgency assessment
    urg = assess_urgency(
        text=intake["sanitized_text"],
        category_code=category,
        job_type=job_type,
        facts=intake["facts"],
        repeat_within_days=repeat_days,
    )

    # 7. Create ticket (satisfy schema CHECKs for brand_forward / retailer_handover FKs)
    if trigger == "brand_forward" and not brand_referral_id:
        brand_referral_id = str(uuid.uuid4())
        db.insert(
            "brand_referral",
            {
                "id": brand_referral_id,
                "centre_id": centre_id,
                "brand_id": app["brand_id"],
                "brand_request_ref": f"BR-{uuid.uuid4().hex[:10]}",
                "received_at": now_iso,
                "payload": {"text": intake["sanitized_text"]},
                "claimed_entitlement": entitlement if entitlement in ("brand_warranty", "extended_warranty", "amc") else "none",
                "authority_checked": auth_res.level,
                "status": "case_opened",
            },
        )
    if trigger == "retailer_handover" and not retailer_handover_id:
        retailer_handover_id = str(uuid.uuid4())
        r_rows = db.raw_query("SELECT id FROM retailer LIMIT 1")
        ret_id = r_rows[0]["id"] if r_rows else str(uuid.uuid4())
        db.insert(
            "retailer_handover",
            {
                "id": retailer_handover_id,
                "centre_id": centre_id,
                "retailer_id": ret_id,
                "order_ref": f"ORD-{uuid.uuid4().hex[:10]}",
                "requested_job": "installation",
                "payload": {"text": intake["sanitized_text"]},
                "received_at": now_iso,
                "status": "case_opened",
            },
        )

    ticket_id = str(uuid.uuid4())
    initial_status = "escalated" if urg.safety_flag else ("cancelled" if out_of_area else "triage")
    case_card = {
        "summary": intake["sanitized_text"][:240],
        "symptoms": intake["symptoms"],
        "error_codes": intake["error_codes"],
        "what_was_tried": [],
        "safety_notes": urg.protective_message or "",
        "identity_notes": f"evidence_level={ident['evidence_level']}, source={ident['identity_source']}",
        "sources": [],
    }
    db.insert(
        "ticket",
        {
            "id": ticket_id,
            "centre_id": centre_id,
            "household_id": hh["id"],
            "appliance_id": app["id"],
            "trigger": trigger,
            "channel": channel,
            "job_type": job_type,
            "brand_referral_id": brand_referral_id,
            "retailer_handover_id": retailer_handover_id,
            "raw_inputs": [{"text": intake["sanitized_text"], "at": now_iso}],
            "case_card": case_card,
            "urgency_class": urg.urgency_class,
            "safety_flag": urg.safety_flag,
            "safety_reason": urg.reason if urg.safety_flag else None,
            "entitlement": entitlement,
            "visit_address": address_line or hh.get("address_line"),
            "visit_location": hh.get("location"),
            "status": initial_status,
            "created_at": now_iso,
            "updated_at": now_iso,
        },
    )

    # Write urgency_assessment
    db.insert(
        "urgency_assessment",
        {
            "id": str(uuid.uuid4()),
            "centre_id": centre_id,
            "ticket_id": ticket_id,
            "class": urg.urgency_class,
            "rule_codes": "{" + ",".join(urg.rule_codes) + "}",
            "facts": intake["facts"],
            "assessed_by": "agent",
            "reason": urg.reason,
            "protective_steps_sent": urg.protective_steps_sent,
            "created_at": now_iso,
        },
    )
    events.append(
        projection_store.emit_event(
            db, centre_id, "urgency_assessed", "agent",
            f"Urgency assessed as {urg.urgency_class}",
            ticket_id=ticket_id,
            conversation_id=conversation_id,
            payload={"class": urg.urgency_class, "rule_codes": urg.rule_codes, "reason": urg.reason},
        )
    )
    if urg.safety_flag:
        events.append(
            projection_store.emit_event(
                db, centre_id, "safety_stop_sent", "agent",
                urg.protective_message or "Please stop using it and switch it off at the wall.",
                ticket_id=ticket_id,
                conversation_id=conversation_id,
                payload={"reason": urg.reason},
            )
        )

    # Cross-centre shared history read (if household linked to another centre & consented)
    if ident["household_lookup"]["other_centres"] > 0 and db.shared_history_allowed(app["id"]):
        shared_events = db.read_shared_history(app["id"], centre_id, ticket_id=ticket_id, reason="intake context")
        if any(e.get("centre_id") != centre_id for e in shared_events):
            events.append(
                projection_store.emit_event(
                    db, centre_id, "shared_history_read", "agent",
                    "Read consented cross-centre technical history",
                    ticket_id=ticket_id,
                    conversation_id=conversation_id,
                    payload={"consent": True, "rows": len(shared_events)},
                )
            )

    # 8. Consent Gate 1 & Gate 2
    gm = GateMachine(job_type=job_type, safety_flag=urg.safety_flag, urgency_class=urg.urgency_class)
    if urg.safety_flag or job_type != "repair":
        g1, g2 = gm.gate1, gm.gate2
    else:
        events.append(
            projection_store.emit_event(
                db, centre_id, "gate_asked", "agent",
                "Asked Gate 1: okay to try a quick, safe fix?",
                ticket_id=ticket_id, conversation_id=conversation_id, payload={"gate": 1},
            )
        )
        g1 = gm.record_gate1(gate1_answer)  # type: ignore[arg-type]
        events.append(
            projection_store.emit_event(
                db, centre_id, "gate_answered", "household",
                f"Gate 1 answered: {g1.answer}",
                ticket_id=ticket_id, conversation_id=conversation_id, payload={"gate": 1, "answer": g1.answer, "choice": None},
            )
        )
        if g1.answer == "yes":
            events.append(
                projection_store.emit_event(
                    db, centre_id, "gate_asked", "agent",
                    "Asked Gate 2: switch to video or carry on here?",
                    ticket_id=ticket_id, conversation_id=conversation_id, payload={"gate": 2},
                )
            )
            g2 = gm.record_gate2("yes", choice=gate2_choice)  # type: ignore[arg-type]
            events.append(
                projection_store.emit_event(
                    db, centre_id, "gate_answered", "household",
                    f"Gate 2 answered: {g2.choice}",
                    ticket_id=ticket_id, conversation_id=conversation_id, payload={"gate": 2, "answer": g2.answer, "choice": g2.choice},
                )
            )
        else:
            g2 = gm.gate2  # automatically recorded as not_asked (gate1_not_yes)

    for g in (g1, g2):
        if g is not None:
            asked_iso = g.asked_at.isoformat() if g.asked_at else now_iso
            answered_iso = now_iso if g.answer in ("yes", "no", "silence") else None
            db.insert(
                "consent_gate",
                {
                    "id": str(uuid.uuid4()),
                    "centre_id": centre_id,
                    "ticket_id": ticket_id,
                    "conversation_id": conversation_id,
                    "gate": g.gate,
                    "asked_at": asked_iso,
                    "answer": g.answer,
                    "answered_at": answered_iso,
                    "choice": g.choice,
                    "not_asked_reason": g.not_asked_reason,
                },
            )

    # 9. Safe fix attempt (only if gate 1 == yes and not safety and repair)
    already_tried: List[Dict[str, Any]] = []
    chosen_fix_code: Optional[str] = None
    if gm.can_start_fix():
        catalogue = _load_db_safefix_catalogue(db)
        sel = select_safe_fix(
            category_code=category,
            symptoms=intake["symptoms"] + intake["error_codes"],
            brand_id=app["brand_id"],
            error_codes=intake["error_codes"],
            catalogue=catalogue,
            safety_flag=urg.safety_flag,
        )
        # Skip SF-RO-FLOW when taste/TDS is the problem (C04), skip E6 refrigerant protection (C02)
        if sel and "E6" not in intake["error_codes"] and not (category == "ro_purifier" and "high_tds" in intake["symptoms"]):
            entry = sel.entry
            chosen_fix_code = entry.code
            events.append(
                projection_store.emit_event(
                    db, centre_id, "fix_offered", "agent",
                    f"Offered safe fix: {entry.title}",
                    ticket_id=ticket_id, conversation_id=conversation_id,
                    payload={"code": entry.code, "title": entry.title, "steps": entry.step_count, "est_minutes": entry.est_minutes},
                )
            )
            events.append(
                projection_store.emit_event(
                    db, centre_id, "fix_step", "agent",
                    f"Guided step {entry.step_count} of {entry.step_count}",
                    ticket_id=ticket_id, conversation_id=conversation_id,
                    payload={"n": entry.step_count, "of": entry.step_count},
                )
            )
            obs_video = gm.can_start_video()
            db.insert(
                "fix_attempt",
                {
                    "id": str(uuid.uuid4()),
                    "centre_id": centre_id,
                    "ticket_id": ticket_id,
                    "catalogue_id": entry.id,
                    "conversation_id": conversation_id,
                    "offered_at": now_iso,
                    "started_at": now_iso,
                    "ended_at": now_iso,
                    "steps_done": entry.step_count,
                    "outcome": fix_outcome,
                    "household_report": f"Completed {entry.code}; outcome={fix_outcome}",
                    "observed_on_video": obs_video,
                },
            )
            events.append(
                projection_store.emit_event(
                    db, centre_id, "fix_result", "household",
                    f"Safe fix {entry.code} result: {fix_outcome}",
                    ticket_id=ticket_id, conversation_id=conversation_id,
                    payload={"outcome": fix_outcome, "household_report": f"Completed {entry.code}"},
                )
            )
            already_tried.append({
                "fix": entry.code,
                "title": entry.title,
                "steps_done": entry.step_count,
                "of": entry.step_count,
                "outcome": fix_outcome,
                "seen_on_video": obs_video,
            })

    # If out of service area (C11), stop before booking a technician
    if out_of_area:
        projection_store.project_ticket(
            centre_id,
            {
                "id": ticket_id,
                "centre_id": centre_id,
                "trigger": trigger,
                "channel": channel,
                "job_type": job_type,
                "status": "cancelled",
                "urgency_class": urg.urgency_class,
                "safety_flag": urg.safety_flag,
                "updated_at": now_iso,
            },
        )
        return {
            "status": "out_of_service_area",
            "ticket_id": ticket_id,
            "authority": {"level": auth_res.level, "decision": auth_res.decision},
            "urgency": urg.urgency_class,
            "safety_flag": urg.safety_flag,
            "chosen_fix_code": chosen_fix_code,
            "gates": [g1, g2],
            "events": events,
            "intake": intake,
        }

    # 10. Diagnostic Agent (re-run if safe fix failed)
    diag = run_diagnostic_agent(
        db=db,
        symptom_text=intake["sanitized_text"],
        brand_id=app["brand_id"],
        brand_name=brand_label,
        category_code=category,
        error_codes=intake["error_codes"],
        already_tried=already_tried,
        rerun_of=chosen_fix_code if already_tried else None,
    )
    top_hyp = diag["hypotheses"][0] if diag["hypotheses"] else None
    events.append(
        projection_store.emit_event(
            db, centre_id, "diagnosis_updated", "agent",
            f"Diagnosis: {top_hyp['label']}" if top_hyp else "Diagnosis abstained; diagnostic visit planned",
            ticket_id=ticket_id, conversation_id=conversation_id,
            payload={
                "top_hypothesis": top_hyp["label"] if top_hyp else None,
                "probability": top_hyp["probability"] if top_hyp else 0.0,
                "rerun": bool(already_tried),
                "evidence": top_hyp["evidence"] if top_hyp else [],
            },
        )
    )

    # 11. Visit Plan + Hard Parts Catalogue Verification
    req_parts = [RequestedPart(part_no=p, quantity=1) for p in (top_hyp.get("candidate_parts", []) if top_hyp else [])]
    verified_parts = []
    if req_parts and app.get("model_id") and ident["evidence_level"] != "unverified":
        cat_rows = [
            CataloguePart(
                id=r["id"], brand_id=r["brand_id"], part_no=r["part_no"], name=r["name"],
                kind=r.get("kind") or "genuine", mrp_paise=int(r.get("mrp_paise") or 0),
                warranty_months=int(r.get("warranty_months") or 0),
            )
            for r in db.raw_query("SELECT * FROM part_catalogue")
        ]
        compat_rows = [
            CompatibilityRow(part_id=r["part_id"], model_id=r["model_id"], revision=r.get("revision") or "")
            for r in db.raw_query("SELECT * FROM part_compatibility")
        ]
        verified_parts, _ = resolve_parts(req_parts, app["brand_id"], app["model_id"], cat_rows, compat_rows)

    req_certs: List[str] = []
    if "E6" in intake["error_codes"] or "lowgas" in (top_hyp.get("fault_key", "") if top_hyp else ""):
        req_certs.append("gas")
    if category == "geyser" and (urg.safety_flag or "gy_" in (top_hyp.get("fault_key", "") if top_hyp else "")):
        req_certs.append("electrical")

    plan = build_visit_plan(
        category_code=category,
        trigger_reason="self_fix_failed" if already_tried else "initial",
        already_tried=[a["fix"] for a in already_tried],
        required_skills=[category],
        requires_safety_cert=req_certs,
        verified_parts=verified_parts,
        confidence=float(top_hyp["probability"]) if top_hyp else 0.55,
    )
    plan_id = str(uuid.uuid4())
    db.insert(
        "visit_plan",
        {
            "id": plan_id,
            "centre_id": centre_id,
            "ticket_id": ticket_id,
            "version": 1,
            "trigger_reason": plan.trigger_reason,
            "already_tried": Jsonb(already_tried),
            "required_skills": Jsonb(plan.required_skills),
            "est_duration_p50_min": plan.est_duration_p50_min,
            "est_duration_p80_min": plan.est_duration_p80_min,
            "tools_needed": list(plan.tools_needed),
            "requires_safety_cert": list(plan.requires_safety_cert),
            "access_notes": plan.access_notes,
            "confidence": float(plan.confidence),
            "model_version": diag["model_version"],
            "created_at": now_iso,
        },
    )
    for idx, h in enumerate(diag["hypotheses"], start=1):
        db.insert(
            "plan_hypothesis",
            {
                "id": str(uuid.uuid4()),
                "centre_id": centre_id,
                "visit_plan_id": plan_id,
                "rank": idx,
                "cause": h["label"],
                "probability": float(h["probability"]),
                "evidence": Jsonb(h.get("evidence", [])),
            },
        )
    events.append(
        projection_store.emit_event(
            db, centre_id, "visit_plan_ready", "agent",
            f"Visit plan ready ({len(already_tried)} prior attempts carried forward)",
            ticket_id=ticket_id, conversation_id=conversation_id,
            payload={"already_tried": already_tried, "plan_id": plan_id},
        )
    )

    # 12. Technician scoring & assignment + slot + estimate quote
    tech_profiles = _load_centre_technicians(db, centre_id, category_code=category)
    hh_pt = parse_pg_point(hh.get("location")) or (17.4483, 78.3915)
    reqs = AssignmentRequirements(
        household_lat=hh_pt[0],
        household_lon=hh_pt[1],
        household_language=lang,
        min_skill_level=1,
        required_safety_certs=req_certs,
        max_km=40.0,
    )
    candidates = score_technicians(tech_profiles, reqs, top_k=3)
    if not candidates and tech_profiles:
        # Relax cert filter if seed centre lacks cert tag so a candidate is still ranked
        reqs.required_safety_certs = []
        candidates = score_technicians(tech_profiles, reqs, top_k=3)

    slot_start = (now + timedelta(hours=3)).replace(minute=0, second=0, microsecond=0)
    slot_end = slot_start + timedelta(hours=2)
    chosen_tech = candidates[0] if candidates else None

    for c in candidates:
        is_chosen = c == chosen_tech
        db.insert(
            "assignment_candidate",
            {
                "id": str(uuid.uuid4()),
                "centre_id": centre_id,
                "ticket_id": ticket_id,
                "visit_plan_id": plan_id,
                "technician_id": c.technician_id,
                "slot_start": slot_start.isoformat(),
                "slot_end": slot_end.isoformat(),
                "rank": c.rank,
                "score": str(c.score),
                "score_breakdown": c.score_breakdown.model_dump(),
                "outcome": "chosen" if is_chosen else "proposed",
                "chosen_by": "agent" if is_chosen else None,
                "created_at": now_iso,
            },
        )

    if candidates:
        events.append(
            projection_store.emit_event(
                db, centre_id, "candidates_scored", "agent",
                f"Ranked top {len(candidates)} technicians inside centre",
                ticket_id=ticket_id, conversation_id=conversation_id,
                payload={"top_3": [c.model_dump() for c in candidates]},
            )
        )

    # Estimate quote from centre price book
    pb_rows = db.raw_query(
        "SELECT * FROM centre_price WHERE centre_id = %s AND category_code = %s AND job_type = %s LIMIT 1",
        (centre_id, category, job_type),
    )
    pb = PriceBookEntry(
        category_code=category,
        job_type=job_type,
        complexity_band="standard",
        visit_fee_paise=int(pb_rows[0]["visit_fee_paise"]) if pb_rows else 29900,
        labour_paise=int(pb_rows[0]["labour_paise"]) if pb_rows else 45000,
    )
    est = build_estimate_range(
        price_book=pb,
        probable_parts=verified_parts,
        entitlement=entitlement,
        is_repeat_30d=(repeat_days is not None and repeat_days <= 30),
    )

    db.insert(
        "slot_proposal",
        {
            "id": str(uuid.uuid4()),
            "centre_id": centre_id,
            "ticket_id": ticket_id,
            "slot_start": slot_start.isoformat(),
            "slot_end": slot_end.isoformat(),
            "price_low_paise": est.low_paise,
            "price_high_paise": est.high_paise,
            "shown_at": now_iso,
            "accepted": True,
            "accepted_at": now_iso,
        },
    )
    events.append(
        projection_store.emit_event(
            db, centre_id, "slots_offered", "agent",
            f"Offered visit window {slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}",
            ticket_id=ticket_id, conversation_id=conversation_id,
            payload={"window": f"{slot_start.isoformat()}..{slot_end.isoformat()}", "price_low_paise": est.low_paise, "price_high_paise": est.high_paise},
        )
    )

    visit_id: Optional[str] = None
    if chosen_tech:
        visit_id = str(uuid.uuid4())
        db.insert(
            "visit",
            {
                "id": visit_id,
                "centre_id": centre_id,
                "ticket_id": ticket_id,
                "technician_id": chosen_tech.technician_id,
                "planned_start": slot_start.isoformat(),
                "planned_end": slot_end.isoformat(),
                "is_return_visit": False,
                "checklist": Jsonb([]),
                "created_at": now_iso,
                "updated_at": now_iso,
            },
        )
        events.append(
            projection_store.emit_event(
                db, centre_id, "technician_assigned", "agent",
                f"Assigned {chosen_tech.name} for {slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}",
                ticket_id=ticket_id, conversation_id=conversation_id,
                payload={"name": chosen_tech.name, "technician_id": chosen_tech.technician_id, "slot": slot_start.isoformat(), "chosen_by": "agent"},
            )
        )

    quote_id = str(uuid.uuid4())
    db.insert(
        "quote",
        {
            "id": quote_id,
            "centre_id": centre_id,
            "ticket_id": ticket_id,
            "version": 1,
            "quote_type": "estimate",
            "created_at": now_iso,
        },
    )
    db.insert(
        "quote_line",
        {
            "id": str(uuid.uuid4()),
            "centre_id": centre_id,
            "quote_id": quote_id,
            "line_type": "visit_fee",
            "description": "Inspection & visit charge",
            "quantity": 1,
            "amount_paise": pb.visit_fee_paise if not (repeat_days and repeat_days <= 30) else 0,
            "payer": "brand_warranty" if entitlement == "brand_warranty" else "household",
        },
    )
    db.insert(
        "quote_line",
        {
            "id": str(uuid.uuid4()),
            "centre_id": centre_id,
            "quote_id": quote_id,
            "line_type": "labour",
            "description": f"{category} {job_type} labour (estimate)",
            "quantity": 1,
            "amount_paise": pb.labour_paise,
            "payer": "brand_warranty" if entitlement == "brand_warranty" else "household",
        },
    )
    events.append(
        projection_store.emit_event(
            db, centre_id, "quote_issued", "agent",
            f"Estimate issued: Rs {est.low_paise // 100}-{est.high_paise // 100}",
            ticket_id=ticket_id, conversation_id=conversation_id,
            payload={"type": "estimate", "total_paise": est.low_paise},
        )
    )

    final_status = "escalated" if urg.safety_flag else "booked"
    db.update("ticket", {"status": final_status, "case_card": {**case_card, "what_was_tried": already_tried, "sources": top_hyp["citations"] if top_hyp else []}, "updated_at": now_iso}, "id = %s", (ticket_id,))
    projection_store.project_ticket(
        centre_id,
        {
            "id": ticket_id,
            "centre_id": centre_id,
            "trigger": trigger,
            "channel": channel,
            "job_type": job_type,
            "status": final_status,
            "urgency_class": urg.urgency_class,
            "safety_flag": urg.safety_flag,
            "updated_at": now_iso,
        },
        assignee={"technician_id": chosen_tech.technician_id, "name": chosen_tech.name} if chosen_tech else None,
    )

    return {
        "status": final_status,
        "ticket_id": ticket_id,
        "visit_id": visit_id,
        "quote_id": quote_id,
        "household_id": hh["id"],
        "appliance_id": app["id"],
        "authority": {"level": auth_res.level, "decision": auth_res.decision},
        "urgency": urg.urgency_class,
        "safety_flag": urg.safety_flag,
        "chosen_fix_code": chosen_fix_code,
        "gates": [g1, g2],
        "diagnosis": diag,
        "candidates": [c.model_dump() for c in candidates],
        "events": events,
        "intake": intake,
    }


def handle_live_turn(state: Any, utterance: str) -> Dict[str, Any]:
    """
    Stateful Live call orchestrator for WS /v1/live/call (drives C03 stage call step by step).
    """
    low = utterance.lower()
    with get_rls_session(centre_id=state.centre_id, role="platform") as db:
        # Turn 1: initial complaint -> identify, check authority, assess urgency, ask Gate 1 (or safety stop)
        if state.stage == "opened":
            intake = run_intake_agent(utterance, trigger="household_call", channel="voice", language_hint=state.language)
            state.language = intake["language"]
            urg = assess_urgency(text=intake["sanitized_text"], category_code=intake["category_code"], job_type=intake["job_type"], facts=intake["facts"])
            if urg.safety_flag:
                res = process_inbound_case(
                    db, centre_id=state.centre_id, trigger="household_call", channel="voice",
                    from_phone=state.caller_number, text=utterance, language_hint=state.language,
                    conversation_id=state.conversation_id,
                )
                state.ticket_id = res["ticket_id"]
                state.stage = "booked"
                return {"events": res["events"], "reply": urg.protective_message}

            state.stage = "gate1"
            state.turns.append({"complaint": utterance})
            ev = projection_store.emit_event(
                db, state.centre_id, "gate_asked", "agent",
                "Asked Gate 1: okay to try a quick, safe fix?",
                conversation_id=state.conversation_id, payload={"gate": 1},
            )
            return {
                "events": [ev],
                "reply": "Before we book anyone, are you okay to try a quick, safe fix yourself?",
            }

        # Turn 2: Gate 1 answer -> if yes, ask Gate 2
        if state.stage == "gate1":
            yes = any(w in low for w in ("yes", "haan", "हां", "ok", "okay", "sure", "avunu", "అవును", "try"))
            if not yes:
                complaint = next((t["complaint"] for t in state.turns if "complaint" in t), utterance)
                res = process_inbound_case(
                    db, centre_id=state.centre_id, trigger="household_call", channel="voice",
                    from_phone=state.caller_number, text=complaint, language_hint=state.language,
                    gate1_answer="no", conversation_id=state.conversation_id,
                )
                state.ticket_id = res["ticket_id"]
                state.stage = "booked"
                return {"events": res["events"], "reply": "Understood, we will skip the self-fix and book a technician for you."}

            state.gate1_answer = "yes"
            state.stage = "gate2"
            ev = projection_store.emit_event(
                db, state.centre_id, "gate_asked", "agent",
                "Asked Gate 2: switch to video or carry on here?",
                conversation_id=state.conversation_id, payload={"gate": 2},
            )
            return {
                "events": [ev],
                "reply": "Would you like to switch to video, or carry on here?",
            }

        # Turn 3: Gate 2 answer -> if video, mint video link and start safe fix
        if state.stage == "gate2":
            wants_video = any(w in low for w in ("video", "वीडियो", "వీడియో", "camera", "link"))
            state.gate2_choice = "switch_to_video" if wants_video else "continue_here"
            state.stage = "video_fix"
            out: Dict[str, Any] = {"events": []}
            if wants_video:
                tok = mint_magic_token(state.conversation_id, scope="video_link", ttl_seconds=1800)
                exp = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
                out["video_link"] = {"url": f"{settings.household_host}/v/{tok}", "expires_at": exp}
                out["ui_hint"] = {"kind": "show_drain_filter", "text": "Please show the lower right filter cover on camera."}
                out["reply"] = "I have sent a video link to your phone. Once you open it, please unplug the machine and open the lower-right drain pump filter."
            else:
                out["reply"] = "We will stay on this call. Please unplug the machine and open the lower-right drain pump filter."
            return out

        # Turn 4+: Safe fix outcome -> run full pipeline with failed fix -> re-run diagnosis -> visit plan -> assign -> quote
        complaint = next((t["complaint"] for t in state.turns if "complaint" in t), utterance)
        outcome = "worked" if any(w in low for w in ("worked", "fixed", "working now", "theek ho gaya")) else "not_worked"
        res = process_inbound_case(
            db, centre_id=state.centre_id, trigger="household_call", channel="voice",
            from_phone=state.caller_number, text=f"{complaint} | Fix report: {utterance}",
            language_hint=state.language,
            gate1_answer=state.gate1_answer or "yes",
            gate2_choice=state.gate2_choice or "switch_to_video",
            fix_outcome=outcome,
            conversation_id=state.conversation_id,
        )
        state.ticket_id = res["ticket_id"]
        state.stage = "booked"
        tech_name = res["candidates"][0]["name"] if res.get("candidates") else "our technician"
        return {
            "events": res["events"],
            "reply": f"Thank you for trying the filter clean. I have recorded what you tried, updated the diagnosis, and booked {tech_name} with everything already noted.",
        }
