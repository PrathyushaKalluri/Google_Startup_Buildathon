"""Turns the simulated history into the platform model: triggers, conversations, consent gates, self-fix attempts, urgency assessments,
centre links, global-id aliases, brand and retailer records, centre_id on every operational row.
Runs after history, schedule and experience cases are built, before the CSVs are written.

What is seeded: records of what already happened (closed jobs and their conversations, gates and fix attempts since the agent went live
on 1 Mar 2026). What is NOT seeded: anything the app produces for today's 20 cases or for tomorrow's work
(visit_plan, plan_hypothesis, plan_part, assignment_candidate, slot_proposal, visit_media, access_log)."""
import random
from common import *
from catalogue import *
from world import *
from people import *
import history as H
import safefix

AGENT_LIVE = dt.datetime(2026, 3, 1, tzinfo=IST)

FIX_FOR_FAULT = {   # fault key -> candidate safe-fix codes (brand-specific variants are filtered by brand)
    "ac_dirty": ["SF-AC-FILTER-AV", "SF-AC-FILTER-ZN"], "ac_lowgas": ["SF-AC-FILTER-AV", "SF-AC-FILTER-ZN"], "ac_drain": ["SF-AC-DRAINLOOK"],
    "ac_pcb": ["SF-AC-RESET"], "ac_odu_pcb": ["SF-AC-RESET"], "ac_remote": ["SF-AC-RESET"], "ac_volt": ["SF-AC-RESET"],
    "wm_drain": ["SF-WM-DRAINFILTER-WC", "SF-WM-DRAINFILTER-ZN", "SF-WM-HOSE"], "wm_lid": ["SF-WM-LID"], "wm_lock": ["SF-WM-LID"],
    "fr_defrost": ["SF-FR-SEAL-FL", "SF-FR-SEAL-ZN"], "fr_ptc": ["SF-ANY-POWER"], "fr_gasket": ["SF-FR-SEAL-FL", "SF-FR-SEAL-ZN"], "fr_fan": ["SF-FR-SEAL-FL", "SF-FR-SEAL-ZN"],
    "fr_comp": ["SF-ANY-POWER"], "fr_pcb": ["SF-ANY-POWER"],
    "ro_service": ["SF-RO-FLOW"], "ro_pump": ["SF-RO-FLOW"], "ro_membrane": ["SF-RO-FLOW"],
    "gy_element": ["SF-GY-SWITCH"], "gy_thermo": ["SF-GY-SWITCH"], "gy_misc": ["SF-GY-SWITCH"],
}
# faults a household can plausibly cure with the matching fix (used for the extra self-fix tickets)
CURABLE = {"ac_dirty": 0.55, "ac_drain": 0.2, "wm_drain": 0.38, "wm_lid": 0.3, "fr_gasket": 0.0, "ro_service": 0.35, "gy_misc": 0.45, "ac_pcb": 0.15, "ac_remote": 0.2}
FIXROW = {}
def fix_row(code):
    if not FIXROW:
        for r in TABLES["safe_fix_catalogue"]:
            FIXROW[r["code"]] = r
    return FIXROW[code]

def fix_valid(code, d):
    r = fix_row(code)
    return r["status"] != "retired" and r["reviewed_on"] <= d <= r["review_due"]

DEFAULT_FIX = {"air_conditioner": ["SF-AC-FILTER-AV", "SF-AC-FILTER-ZN", "SF-AC-RESET"], "washing_machine": ["SF-WM-HOSE"], "refrigerator": ["SF-ANY-POWER"],
               "water_purifier": ["SF-RO-FLOW"], "water_heater": ["SF-GY-SWITCH"]}
def pick_fix(app, fault, d):
    if not fault:
        return None
    for code in FIX_FOR_FAULT.get(fault["key"], []) + DEFAULT_FIX.get(app["cat"], []):
        r = fix_row(code)
        if r["category_code"] != app["cat"]:
            continue
        if r["brand_id"] and r["brand_id"] != uid("brand", app["brand"]):
            continue
        if fix_valid(code, d):
            return code
    return None

RETAILERS = [("Digital Plaza Electronics", "Hyderabad"), ("Sri Sai Electronics, Kukatpally", "Hyderabad"), ("Mega Electronics, Kondapur", "Hyderabad"),
             ("Sree Electronics, Kondapur", "Hyderabad"), ("Bharat Home Mart", "Hyderabad")]
UNSAFE_FACTS = {"safety": {"unsafe_now": True}, "urgent": {"unsafe_now": False, "at_risk_if_waits": ["food"]}, "standard": {"unsafe_now": False, "at_risk_if_waits": []},
                "planned": {"unsafe_now": False, "at_risk_if_waits": []}}
OBS = {
    "air_conditioner": ["indoor unit seen, filter mesh visible", "ice on the thin copper pipe", "display shows an error code", "outdoor fan not turning (seen from balcony)", "water line below the unit"],
    "refrigerator": ["freezer vents covered with frost", "door seal gap at the bottom edge", "set-point dial at mid", "display shows a code"],
    "washing_machine": ["drum holds water", "drain filter cover found bottom right", "display shows E21", "coins in the filter"],
    "water_purifier": ["tap flow normal", "adaptor light on", "cartridge housing dry"],
    "water_heater": ["indicator light off", "dial at mid setting", "no leak at the pipes"],
}

def build_adaptation():
    hh_by_id = {h["id"]: h for h in HH.values()}
    app_by_id = {a["id"]: a for a in APPS.values()}
    tickets = TABLES["ticket"]
    visits_by_ticket = {}
    for v in TABLES["visit"]:
        visits_by_ticket.setdefault(v["ticket_id"], []).append(v)
    retailer_ids = {}
    for name, city in RETAILERS:
        retailer_ids[name] = uid("retailer", name)
        add("retailer", id=retailer_ids[name], name=name, city=city, created_at=ist(2025, 9, 5, 10))

    # ------------------------------------------------------------------ 1. extra tickets resolved by a self-fix (no visit)
    extra = []
    pool = [a for a in APPS.values() if a["key"] not in {x["key"] for s in STORIES_EX for x in s["appliances"]} and a["start"]]
    rng.shuffle(pool)
    tries = 0
    for app in pool:
        if len(extra) >= 48:
            break
        hh = hh_by_id[app["hh"] if app["hh"] in hh_by_id else HH[app["hh"]]["id"]] if False else HH[app["hh"]]
        cands = [f for f in FAULTS if f["cat"] == app["cat"] and app["fam"] in f["fams"] and f["key"] in CURABLE]
        if not cands:
            continue
        f = weighted(cands, [max(0.02, CURABLE[x["key"]]) for x in cands])
        d0 = max(AGENT_LIVE.date(), hh["created"].date() + dt.timedelta(days=5), app["start"] + dt.timedelta(days=30))
        d1 = (SIM_NOW - dt.timedelta(days=4)).date()
        if d0 >= d1:
            continue
        d = d0 + dt.timedelta(days=rng.randint(0, (d1 - d0).days))
        code = pick_fix(app, f, d)
        if not code:
            continue
        H.set_centre(None)
        centre = H.pick_centre(app, hh, "repair", "paid", d)
        extra.append((app, hh, f, code, d, centre))
    for i, (app, hh, f, code, d, centre) in enumerate(extra):
        created = H.rand_created(d)
        tkid = uid("ticket", f"selffix-{app['key']}-{created.isoformat()}")
        closed = created + dt.timedelta(minutes=rng.randint(14, 52))
        add("ticket", id=tkid, centre_id=uid("centre", centre), household_id=hh["id"], appliance_id=app["id"], job_type="repair", _channel="whatsapp",
            raw_inputs=[{"type": "text", "text": rng.choice(f["sym"]).replace("{code}", "an error").strip()}], case_card={}, _urgency="standard", safety_flag=False, safety_reason=None,
            entitlement=None, coverage_plan_id=None, visit_address=hh["addr"], visit_location=geo(hh["lon"], hh["lat"]), status="closed", first_visit_by=created + dt.timedelta(hours=72),
            _brand_ref=None, created_at=created, updated_at=closed, closed_at=closed)
        H.TICKET_FAULT[tkid] = f
        tickets_extra = TABLES["ticket"][-1]
        tickets_extra["_selffix"] = code
    tickets = TABLES["ticket"]

    # ------------------------------------------------------------------ 2. tickets: trigger, channel, urgency class, closure
    brand_n = 0
    for t in tickets:
        hh = hh_by_id[t["household_id"]]
        app = app_by_id.get(t["appliance_id"])
        ch = t.pop("_channel"); urg = t.pop("_urgency"); bref = t.pop("_brand_ref"); selffix = t.pop("_selffix", None)
        jt = t["job_type"]
        trigger, channel = None, None
        if bref and rng.random() < 0.78:
            trigger, channel = "brand_forward", "brand_api"
        elif jt == "installation" and rng.random() < 0.55:
            trigger, channel = "retailer_handover", "retailer_api"
        else:
            r = rng.random()
            if ch == "centre":
                trigger, channel = "household_message", "centre_console"
            elif ch == "app":
                trigger, channel = "household_message", "app"
            elif r < 0.34:
                trigger, channel = "household_call", "voice"
            else:
                trigger, channel = "household_message", "whatsapp"
        t["trigger"], t["channel"] = trigger, channel
        t["brand_referral_id"] = None; t["retailer_handover_id"] = None; t["origin_reminder_id"] = None
        t["urgency_class"] = "safety" if t["safety_flag"] else ("urgent" if urg == "urgent" else "planned" if urg == "planned" else "standard")
        t["needed_by"] = (t["created_at"] + dt.timedelta(days=rng.randint(2, 9))) if rng.random() < 0.22 else None
        # resolution and closure
        vs = sorted(visits_by_ticket.get(t["id"], []), key=lambda v: v["planned_start"])
        if t["status"] == "cancelled":
            t["resolution"] = "cancelled"; t["closure_otp_ref"] = None; t["closure_confirmed_at"] = None
        elif selffix:
            t["resolution"] = "self_fix"
            t["closure_otp_ref"] = f"otp_{rng.randint(10**7, 10**8 - 1):x}"; t["closure_confirmed_at"] = t["closed_at"] - dt.timedelta(minutes=rng.randint(1, 6))
        elif t["status"] == "closed":
            t["resolution"] = "visit"
            fin = next((v for v in reversed(vs) if v["closure_confirmed_at"]), None)
            if fin:
                t["closure_otp_ref"] = fin["closure_otp_ref"]; t["closure_confirmed_at"] = fin["closure_confirmed_at"]
            else:
                t["closure_otp_ref"] = f"otp_{rng.randint(10**7, 10**8 - 1):x}"; t["closure_confirmed_at"] = t["closed_at"]
        else:
            t["resolution"] = None; t["closure_otp_ref"] = None; t["closure_confirmed_at"] = None
        if t["needed_by"] and vs and vs[0]["planned_start"] > t["needed_by"]:
            t["needed_by"] = vs[0]["planned_start"] + dt.timedelta(hours=random.Random(f"nb-{t['id']}").randint(2, 30))
        if t["closure_confirmed_at"] and t["closed_at"] and t["closure_confirmed_at"] > t["closed_at"]:
            t["closed_at"] = t["closure_confirmed_at"] + dt.timedelta(minutes=1)
            t["updated_at"] = t["closed_at"]
        t["_trigger"] = trigger; t["_bref"] = bref; t["_selffix_code"] = selffix

    # ------------------------------------------------------------------ 3. brand referrals and retailer handovers for those triggers
    for t in tickets:
        centre_key = next(k for k, *_ in CENTRES if uid("centre", k) == t["centre_id"])
        app = app_by_id.get(t["appliance_id"])
        hh = hh_by_id[t["household_id"]]
        if t["_trigger"] == "brand_forward":
            ref = t["_bref"] or f"BRC-{rng.randint(100000, 999999)}"
            brid = uid("bref", ref)
            lvl = H.auth_level(centre_key, app["brand"], t["created_at"].date())
            add("brand_referral", id=brid, centre_id=t["centre_id"], brand_id=uid("brand", app["brand"]), brand_request_ref=ref, received_at=t["created_at"],
                payload={"customer": {"phone_hash": None, "city": "Hyderabad"}, "complaint": (t["raw_inputs"][0]["text"] if t["raw_inputs"] else ""), "serial": app.get("serial")},
                claimed_entitlement=t["entitlement"] if t["entitlement"] in ("brand_warranty", "extended_warranty", "amc") else "brand_warranty", authority_checked=lvl or "none",
                household_contacted_at=t["created_at"] + dt.timedelta(minutes=rng.randint(2, 25)), status="case_opened")
            t["brand_referral_id"] = brid
            add("external_ref", id=uid("xref", f"{brid}"), entity_type="ticket", entity_id=t["id"], ref_type="brand_case_id", ref_norm=ref, owner_type="brand",
                owner_id=uid("brand", app["brand"]), verified=True, first_seen_at=t["created_at"])
            brand_n += 1
        elif t["_trigger"] == "retailer_handover":
            rn = rng.choice(RETAILERS)[0]
            oref = f"ORD-{rng.randint(10**6, 10**7)}"
            rid = uid("rhand", t["id"])
            add("retailer_handover", id=rid, centre_id=t["centre_id"], retailer_id=retailer_ids[rn], order_ref=oref, invoice_no=f"INV/{t['created_at'].year}/{rng.randint(10000, 99999)}",
                purchase_date=(app["purchase"] or t["created_at"].date()), requested_job="installation", payload={"preferred_window": rng.choice(["weekday morning", "weekend", "any"])},
                received_at=t["created_at"], status="case_opened")
            t["retailer_handover_id"] = rid
            add("external_ref", id=uid("xref", rid), entity_type="ticket", entity_id=t["id"], ref_type="order_id", ref_norm=oref, owner_type="retailer", owner_id=retailer_ids[rn],
                verified=True, first_seen_at=t["created_at"])
    # referrals that the receiving centre could not act on (brand routed to a centre without authority) -- no ticket
    declined = 0
    for k in range(14):
        ckey = rng.choice([c for c in ("c_cc", "c_mh", "c_ls", "c_ip")])
        brands = [b for b in ("aerovane", "zenith", "wavecrest", "heatwell") if H.auth_level(ckey, b, dt.date(2026, 6, 1)) in (None, "independent", "installation_only")]
        if not brands:
            continue
        b = rng.choice(brands)
        ref = f"{BRAND_CODE[b]}-SRQ-{rng.randint(100000, 999999)}"
        recv = SIM_NOW - dt.timedelta(days=rng.randint(5, 220), hours=rng.randint(0, 20))
        add("brand_referral", id=uid("bref", ref), centre_id=uid("centre", ckey), brand_id=uid("brand", b), brand_request_ref=ref, received_at=recv,
            payload={"customer": {"city": "Hyderabad"}, "complaint": rng.choice(["not cooling", "water leak", "no hot water", "noise"])}, claimed_entitlement="brand_warranty",
            authority_checked=H.auth_level(ckey, b, recv.date()) or "none", household_contacted_at=recv + dt.timedelta(minutes=rng.randint(3, 40)), status="declined")
        declined += 1

    # ------------------------------------------------------------------ 4. conversations, gates, fix attempts, urgency, clarifying questions, video sessions
    consent_by_hh = {}
    for c in TABLES["consent_ledger"]:
        if c["withdrawn_at"] is None:
            consent_by_hh.setdefault(c["subject_id"], set()).add(c["purpose"])
    for t in tickets:
        hh = hh_by_id[t["household_id"]]
        app = app_by_id.get(t["appliance_id"])
        fault = H.TICKET_FAULT.get(t["id"])
        created = t["created_at"]
        modality = "voice" if t["channel"] == "voice" else "text"
        chan = {"voice": "voice", "whatsapp": "whatsapp", "app": "app", "centre_console": "voice", "brand_api": "voice", "retailer_api": "voice"}[t["channel"]]
        cid = uid("conv", f"{t['id']}-1")
        end = created + dt.timedelta(minutes=rng.randint(6, 18) if t["resolution"] != "self_fix" else rng.randint(14, 40))
        add("conversation", id=cid, centre_id=t["centre_id"], ticket_id=t["id"], household_id=t["household_id"], channel=chan, modality=modality, parent_conversation_id=None,
            language=hh["lang"], started_at=created, ended_at=end, end_reason="completed", recording_consent="photos_voice" in consent_by_hh.get(hh["id"], set()),
            transcript_uri=None, summary=(t["raw_inputs"][0]["text"] if t["raw_inputs"] else None))
        if created < AGENT_LIVE:
            continue
        repair = t["job_type"] in ("repair", "coverage_claim")
        cls = t["urgency_class"]
        rules = {"safety": ["SAF-SMOKE-BURN" if (fault and fault["key"] == "wm_motor_sa") else "SAF-SHOCK"], "urgent": ["URG-FOOD-RISK" if app and app["cat"] == "refrigerator" else "URG-VULNERABLE-HEAT"],
                 "standard": ["STD-DEFAULT"], "planned": ["PLN-INSTALL" if t["job_type"] == "installation" else "PLN-SERVICE"]}[cls]
        facts = dict(UNSAFE_FACTS[cls]); facts["stopped_or_partial"] = rng.choice(["stopped", "partial"]) if repair else "not_applicable"
        add("urgency_assessment", id=uid("urg", t["id"]), centre_id=t["centre_id"], ticket_id=t["id"], **{"class": cls}, rule_codes=pgarray(rules), facts=facts, assessed_by="agent",
            reason={"safety": "Rule fired on a safety fact", "urgent": "Something at risk if it waits", "standard": "Nothing unsafe, nothing at risk", "planned": "Planned job"}[cls],
            protective_steps_sent=(cls in ("safety", "urgent") and repair), created_at=created + dt.timedelta(minutes=2))
        # clarifying questions (repair only)
        if repair:
            qs = [("What does the appliance do now?", "text" if modality == "text" else "voice"), ("Is anything unsafe: smell, smoke, shock, water near sockets?", "text" if modality == "text" else "voice"),
                  ("When did it start?", "text" if modality == "text" else "voice")]
            for i, (q, src) in enumerate(qs, 1):
                add("clarifying_qa", id=uid("qa", f"{t['id']}-{i}"), centre_id=t["centre_id"], ticket_id=t["id"], conversation_id=cid, seq=i, question=q,
                    answer=rng.choice(["Since yesterday", "A few days now", "No, nothing unsafe", "It stopped completely", "Works a little then stops"]), answer_source=src,
                    asked_at=created + dt.timedelta(minutes=1 + i))
        if not repair:
            continue
        # gates
        sf = t["resolution"] == "self_fix"
        code = None
        if t["safety_flag"]:
            for g in (1, 2):
                add("consent_gate", id=uid("gate", f"{t['id']}-{g}"), centre_id=t["centre_id"], ticket_id=t["id"], conversation_id=cid, gate=g, asked_at=created + dt.timedelta(minutes=3),
                    answer="not_asked", answered_at=None, choice=None, not_asked_reason="safety_flag")
            continue
        r = rng.random()
        g1 = "yes" if (sf or r < 0.66) else "no" if r < 0.88 else "silence"
        add("consent_gate", id=uid("gate", f"{t['id']}-1"), centre_id=t["centre_id"], ticket_id=t["id"], conversation_id=cid, gate=1, asked_at=created + dt.timedelta(minutes=4),
            answer=g1, answered_at=None if g1 == "silence" else created + dt.timedelta(minutes=4, seconds=rng.randint(8, 50)), choice=None, not_asked_reason=None)
        if g1 != "yes":
            add("consent_gate", id=uid("gate", f"{t['id']}-2"), centre_id=t["centre_id"], ticket_id=t["id"], conversation_id=cid, gate=2, asked_at=created + dt.timedelta(minutes=4),
                answer="not_asked", answered_at=None, choice=None, not_asked_reason="gate1_not_yes")
            continue
        video = (rng.random() < (0.52 if sf else 0.34)) and "video_diagnosis" in consent_by_hh.get(hh["id"], set()) | ({"video_diagnosis"} if rng.random() < 0.5 else set())
        add("consent_gate", id=uid("gate", f"{t['id']}-2"), centre_id=t["centre_id"], ticket_id=t["id"], conversation_id=cid, gate=2, asked_at=created + dt.timedelta(minutes=5),
            answer="yes", answered_at=created + dt.timedelta(minutes=5, seconds=rng.randint(6, 40)), choice="switch_to_video" if video else "continue_here", not_asked_reason=None)
        # which fix
        code = t.get("_selffix_code")
        if sf:
            code = t["_selffix_code"]
        else:
            code = pick_fix(app, fault, created.date())
        sid = None
        vid_conv = None
        if video:
            vid_conv = uid("conv", f"{t['id']}-2")
            dur = rng.randint(70, 110) if rng.random() < 0.35 else rng.randint(130, 430)
            start = created + dt.timedelta(minutes=7)
            add("conversation", id=vid_conv, centre_id=t["centre_id"], ticket_id=t["id"], household_id=t["household_id"], channel="video", modality="video", parent_conversation_id=cid,
                language=hh["lang"], started_at=start, ended_at=start + dt.timedelta(seconds=dur), end_reason="completed", recording_consent=False, transcript_uri=None,
                summary="Video diagnosis")
            sid = uid("diag", t["id"])
            frames = "frame_retention" in consent_by_hh.get(hh["id"], set()) and rng.random() < 0.9
            add("diagnosis_session", id=sid, centre_id=t["centre_id"], ticket_id=t["id"], conversation_id=vid_conv, provider="gemini_live", model="gemini-live", link_route=weighted(["whatsapp_link", "same_session", "in_app", "sms_link"], [55, 15, 20, 10]),
                started_at=start, ended_at=start + dt.timedelta(seconds=dur), duration_s=dur, video_on=True, compression_on=dur > 120 or rng.random() < 0.8, resumptions=1 if dur > 300 and rng.random() < 0.5 else 0,
                frames_consent=frames, end_reason=weighted(["completed", "household_stopped", "connection_lost", "timeout"], [82, 7, 8, 3]),
                observations=[{"t_s": rng.randint(5, max(6, dur - 10)), "note": n} for n in rng.sample(OBS[app["cat"]], k=2)])
            if frames and (SIM_NOW - start).days <= 30:
                for n in range(rng.randint(2, 4)):
                    add("diagnosis_media", id=uid("dmedia", f"{sid}-{n}"), centre_id=t["centre_id"], session_id=sid, kind="frame", storage_uri=f"gs://keepwell-sim/diag/{sid}/f{n}.jpg",
                        retain_until=(start + dt.timedelta(days=30)).date(), created_at=start + dt.timedelta(seconds=n * 15))
        if code:
            fr = fix_row(code)
            if sf:
                out, done = "worked", fr["step_count"]
            else:
                out = weighted(["not_worked", "abandoned", "safety_stop"], [82, 15, 3])
                done = fr["step_count"] if out == "not_worked" else rng.randint(1, max(1, fr["step_count"] - 1))
            off = created + dt.timedelta(minutes=8)
            add("fix_attempt", id=uid("fix", t["id"]), centre_id=t["centre_id"], ticket_id=t["id"], catalogue_id=fr["id"], conversation_id=vid_conv or cid, session_id=sid, offered_at=off,
                started_at=off + dt.timedelta(seconds=40), ended_at=off + dt.timedelta(minutes=fr["est_minutes"] + rng.randint(0, 4)), steps_done=done, outcome=out,
                household_report={"worked": "Working now", "not_worked": "Same problem", "abandoned": "Could not do that step", "safety_stop": "Smelled something, stopped"}[out],
                observed_on_video=bool(sid))
            if sf:
                add("appliance_event", id=uid("event", f"{t['id']}-selffix"), appliance_id=app["id"], centre_id=t["centre_id"], event_type="self_fix", visibility="technical", occurred_at=t["closed_at"], ticket_id=t["id"],
                    details={"fix": code, "outcome": "worked"})

    # ------------------------------------------------------------------ 5. appliance events: centre and visibility
    tcentre = {t["id"]: t["centre_id"] for t in TABLES["ticket"]}
    for e in TABLES["appliance_event"]:
        e["centre_id"] = tcentre.get(e.get("ticket_id")) if e.get("centre_id") is None else e["centre_id"]
        e.setdefault("visibility", "technical")
        e["visibility"] = "technical"
    # ------------------------------------------------------------------ 6. centre_id on child tables
    vcentre = {v["id"]: v["centre_id"] for v in TABLES["visit"]}
    qcentre = {}
    for q in TABLES["quote"]:
        q["centre_id"] = tcentre[q["ticket_id"]]; qcentre[q["id"]] = q["centre_id"]
    for l in TABLES["quote_line"]:
        l["centre_id"] = qcentre[l["quote_id"]]
    for tname in ("visit_part_used", "visit_media", "reservation"):
        for r in TABLES[tname]:
            if r.get("centre_id") is None:
                r["centre_id"] = vcentre[r["visit_id"]]
    for r in TABLES["settlement_line"]:
        r["centre_id"] = tcentre[r["ticket_id"]]
    for r in TABLES["feedback"]:
        r["centre_id"] = tcentre[r["ticket_id"]]
    tech_centre = {t["id"]: t["centre_id"] for t in TABLES["technician"]}
    for r in TABLES["technician_metrics"]:
        r["centre_id"] = tech_centre[r["technician_id"]]
    for r in TABLES["route"]:
        r["centre_id"] = tech_centre[r["technician_id"]]
    rcentre = {r["id"]: r["centre_id"] for r in TABLES["route"]}
    for r in TABLES["route_stop"]:
        r["centre_id"] = rcentre[r["route_id"]]

    # ------------------------------------------------------------------ 7. links, last served, aliases
    link = {}
    for t in TABLES["ticket"]:
        k = (t["household_id"], t["centre_id"])
        l = link.setdefault(k, dict(first=t["created_at"], last=None, n=0))
        l["first"] = min(l["first"], t["created_at"]); l["n"] += 1
        if t["status"] == "closed" and t["resolution"] in ("visit", "self_fix"):
            l["last"] = max(l["last"], t["closed_at"]) if l["last"] else t["closed_at"]
    story_centre = {f"hh_{s['id'].lower()}": s["centre"] for s in STORIES_EX if s["existing"]}
    for key, h in HH.items():
        if not any(k[0] == h["id"] for k in link):
            if key in story_centre:
                ck = story_centre[key]
            else:
                pin = h["pincode"] or LOC[h["locality"]][2]
                opts = [c[0] for c in CENTRES if pin in c[4]] or ["c_mh"]
                ck = rng.choice(opts)
            link[(h["id"], uid("centre", ck))] = dict(first=h["created"], last=None, n=1)
    for s in STORIES_EX:     # a household that arrives on a new centre's line is linked only when the app creates the link; the receiving centre is not pre-linked for cross-centre cases
        if s["existing"] and s["id"] in ("C19",):
            link.pop((HH[f"hh_{s['id'].lower()}"]["id"], uid("centre", s["centre"])), None)
    for (hid, cid), l in link.items():
        add("household_centre_link", household_id=hid, centre_id=cid, first_contact_at=l["first"], last_served_at=l["last"], contact_count=l["n"])
    centres_of_hh = {}
    for (hid, cid), l in link.items():
        centres_of_hh.setdefault(hid, []).append((cid, l))
    last_c = {}
    first_c = {}
    for t in sorted(TABLES["ticket"], key=lambda x: x["created_at"]):
        if t["appliance_id"]:
            first_c.setdefault(t["appliance_id"], t["centre_id"])
            if t["status"] == "closed" and t["resolution"] in ("visit", "self_fix"):
                last_c[t["appliance_id"]] = t["centre_id"]
    last_ev = {}
    for e in TABLES["appliance_event"]:
        if e["event_type"] in ("service", "repair", "install", "self_fix") and e.get("details", {}).get("outcome", "fixed") == "fixed":
            last_ev[e["appliance_id"]] = max(e["occurred_at"], last_ev.get(e["appliance_id"], e["occurred_at"]))
    for a in TABLES["appliance"]:
        a["last_served_centre_id"] = last_c.get(a["id"])
        a["first_seen_centre_id"] = first_c.get(a["id"]) or (centres_of_hh.get(a["household_id"], [(None, None)])[0][0])
        if a["id"] in last_ev:
            a["last_service_at"] = last_ev[a["id"]].date()
        # next due from the category interval
        cat_norm = {"air_conditioner": 6, "refrigerator": 12, "washing_machine": 12, "water_purifier": 4, "water_heater": 12}[a["category_code"]]
        base = a["last_service_at"] or a["install_date"] or a["purchase_date"]
        a["next_due_at"] = None
        if base and a["category_code"] != "refrigerator":
            y = base.year + (base.month - 1 + cat_norm) // 12; m = (base.month - 1 + cat_norm) % 12 + 1
            a["next_due_at"] = dt.date(y, m, min(base.day, 28))
    # reminders: only the centre that last served the appliance may send them, with consent for that centre
    app_last = {a["id"]: a["last_served_centre_id"] for a in TABLES["appliance"]}
    kept = []
    for r in TABLES["reminder"]:
        c = app_last.get(r["appliance_id"])
        if c:
            r["centre_id"] = c; kept.append(r)
    TABLES["reminder"][:] = kept
    for c in TABLES["consent_ledger"]:
        if c["purpose"] in ("service_reminders", "warranty_alerts") and c["subject_type"] == "household":
            cs = centres_of_hh.get(c["subject_id"])
            if cs:
                latest = max(cs, key=lambda x: (x[1]["last"] or dt.datetime(2000, 1, 1, tzinfo=IST), x[1]["first"]))
                c["scope_centre_id"] = latest[0]
    # centre console reclassifications: the centre disagrees with the agent's urgency class. Each is a training signal.
    ua_by_ticket = {u["ticket_id"]: u for u in TABLES["urgency_assessment"]}
    tix = {t["id"]: t for t in TABLES["ticket"]}
    pool = sorted(u["ticket_id"] for u in TABLES["urgency_assessment"] if u["class"] in ("standard", "urgent") and not tix[u["ticket_id"]]["safety_flag"] and tix[u["ticket_id"]]["status"] == "closed")
    random.Random("console-reclass").shuffle(pool)
    for tid in pool[:9]:
        t = tix[tid]; u = ua_by_ticket[tid]
        new_cls = "urgent" if u["class"] == "standard" else "standard"
        why = ("Centre reclassified: elderly or young children at home, household cannot wait" if new_cls == "urgent" else "Centre reclassified: household has a working alternative, can wait for the planned slot")
        add("urgency_assessment", id=uid("urg2", tid), centre_id=t["centre_id"], ticket_id=tid, **{"class": new_cls}, rule_codes=pgarray([]), facts=u["facts"], assessed_by="centre_console",
            reason=why, protective_steps_sent=False, created_at=u["created_at"] + dt.timedelta(minutes=random.Random(f"cr-{tid}").randint(25, 90)))
        t["urgency_class"] = new_cls
    # scheduled reminders: appliances now due, sent by the centre that last served them, only with consent in force for that centre
    cons_ok = {(c["subject_id"], c["scope_centre_id"]) for c in TABLES["consent_ledger"] if c["purpose"] == "service_reminders" and c["subject_type"] == "household" and c["withdrawn_at"] is None}
    recent = {(r["appliance_id"]) for r in TABLES["reminder"] if r["due_on"] >= SIM_NOW.date() - dt.timedelta(days=75)}
    open_t = {t["appliance_id"] for t in TABLES["ticket"] if t["status"] not in ("closed", "cancelled", "completed")}
    sent_nov = {}
    for r in TABLES["reminder"]:
        if r["status"] in ("sent", "delivered", "read", "acted") and r["sent_at"] and r["sent_at"] >= ist(2026, 11, 1):
            sent_nov[r["household_id"]] = sent_nov.get(r["household_id"], 0) + 1
    due = [a for a in TABLES["appliance"] if a["status"] == "active" and a["last_served_centre_id"] and a["next_due_at"] and a["next_due_at"] <= SIM_NOW.date()
           and a["id"] not in recent and a["id"] not in open_t and (a["household_id"], a["last_served_centre_id"]) in cons_ok and sent_nov.get(a["household_id"], 0) < 2]
    due.sort(key=lambda a: a["id"])
    random.Random("sched-rem").shuffle(due)
    for a in due[:16]:
        add("reminder", id=uid("reminder", f"sched-{a['id']}"), centre_id=a["last_served_centre_id"], household_id=a["household_id"], appliance_id=a["id"], reminder_type="service_due",
            due_on=max(a["next_due_at"], SIM_NOW.date() - dt.timedelta(days=21)), template_name="service_due_v2", whatsapp_category="utility", status="scheduled",
            scheduled_at=ist(2026, 11, 21, 10, 0), sent_at=None, delivered_at=None, read_at=None, action_taken=None, ticket_id=None, created_at=SIM_NOW - dt.timedelta(days=7))
    # external refs: household phones, member phones, serials, centre customer numbers
    seen = set()
    for h in TABLES["household"]:
        add("external_ref", id=uid("xref", f"ph-{h['id']}"), entity_type="household", entity_id=h["id"], ref_type="phone", ref_norm=h["phone_hash"].hex(), owner_type="keepwell", owner_id=None, verified=True, first_seen_at=h["created_at"])
    for m in TABLES["household_member"]:
        if m["phone_hash"] == next((h["phone_hash"] for h in TABLES["household"] if h["id"] == m["household_id"]), None):
            continue
        add("external_ref", id=uid("xref", f"mph-{m['id']}"), entity_type="household", entity_id=m["household_id"], ref_type="phone", ref_norm=m["phone_hash"].hex(), owner_type="keepwell", owner_id=None, verified=True, first_seen_at=m["created_at"])
    for a in TABLES["appliance"]:
        if a["serial_norm"]:
            add("external_ref", id=uid("xref", f"sn-{a['id']}"), entity_type="appliance", entity_id=a["id"], ref_type="serial", ref_norm=a["serial_norm"], owner_type="keepwell", owner_id=None, verified=a["identity_status"] == "verified", first_seen_at=a["created_at"])
    n = 0
    for (hid, cid), l in sorted(link.items(), key=lambda x: (x[0][1], x[1]["first"])):
        n += 1
        ck = next(k for k, *_ in CENTRES if uid("centre", k) == cid)
        add("external_ref", id=uid("xref", f"cust-{hid}-{cid}"), entity_type="household", entity_id=hid, ref_type="centre_customer_no", ref_norm=f"{ck.upper()}-{n:05d}", owner_type="centre", owner_id=cid, verified=True, first_seen_at=l["first"])

    # ------------------------------------------------------------------ 8. experience cases: self-fixes tried before the visit
    tried = {}
    tick_of_visit = {v["id"]: v["ticket_id"] for v in TABLES["visit"]}
    for f in TABLES["fix_attempt"]:
        tried.setdefault(f["ticket_id"], []).append(fix_row_by_id(f["catalogue_id"]))
    for e in TABLES["experience_case"]:
        e["self_fix_tried"] = pgarray(tried.get(tick_of_visit.get(e["source_visit_id"]), []))
    # ------------------------------------------------------------------ 9. strip internals
    for t in TABLES["ticket"]:
        for k in [k for k in t if k.startswith("_")]:
            t.pop(k)
    for h in TABLES["household"]:
        h.pop("reminder_prefs", None)
    return dict(self_fix=len(extra), declined_referrals=declined, brand_forwarded=brand_n)

def fix_row_by_id(fid):
    for r in TABLES["safe_fix_catalogue"]:
        if r["id"] == fid:
            return r["code"]

from stories import STORIES as STORIES_EX
