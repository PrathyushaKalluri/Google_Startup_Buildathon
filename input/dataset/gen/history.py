"""Past jobs (Sep 2025 - Nov 2026): tickets, visits, quotes, settlements, feedback, routes, experience cases.
First-visit success is driven by hidden technician skill and part availability, so metrics have genuine signal."""
import math
from common import *
from catalogue import *
from world import *
from people import *
from stories import STORIES

SK = {}
def index_skills():
    PLAN_KIND.update({p["id"]: p for p in TABLES["coverage_plan"]})
    for r in TABLES["technician_skill"]:
        k = (r["technician_id"], r["category_code"], r["fault_class"])
        SK[k] = max(SK.get(k, 0), r["level"])
RATE = {}
def index_rates():
    for r in TABLES["rate_card"]:
        RATE.setdefault((r["category_code"], r["job_type"], r["complexity_band"]), []).append(r)
CUR_CENTRE = [None]
def set_centre(c):
    CUR_CENTRE[0] = c
def rate_for(cat, jt, band, d):
    """Visit fee and labour for the centre currently being priced (each centre's own price list; see world.PRICE_FACTOR)."""
    base = None
    for r in RATE.get((cat, jt, band), []):
        if r["valid_from"] <= d and (r["valid_to"] is None or d < r["valid_to"]):
            base = r; break
    base = base or RATE[(cat, jt, band)][-1]
    f = PRICE_FACTOR.get(CUR_CENTRE[0], 1.0)
    return dict(base, visit_fee_paise=int(round(base["visit_fee_paise"] * f / 1000) * 1000), labour_paise=int(round(base["labour_paise"] * f / 1000) * 1000))

TECHS_BY_CENTRE = {}
BUSY = {}   # tech id -> [(start, end)]
PLAN_KIND = {p["id"]: p for p in TABLES["coverage_plan"]}
PARTROW = {}
def index_parts():
    for p in TABLES["part_catalogue"]:
        PARTROW[p["id"]] = p
TICKETS_OF_APP = {}
TICKET_FAULT = {}
VISITS = []        # internal visit records for routes/metrics
EXP_CASES = []

def auth_level(ckey, brand, d):
    for b, lvl, vf, vt in AUTH[ckey]:
        if b == brand and vf <= d and (vt is None or d < vt):
            return lvl
    return None

def pick_centre(app, hh, jt, entitlement, d, force=None):
    if force:
        return force
    pin = hh["pincode"] or LOC[hh["locality"]][2]
    cands, weights = [], []
    for key, name, loc, cats, pins, hours, comm in CENTRES:
        if pin not in pins or app["cat"] not in cats:
            continue
        lvl = auth_level(key, app["brand"], d)
        if lvl is None:
            continue
        if lvl == "installation_only" and jt != "installation":
            continue
        if entitlement == "brand_warranty" and lvl not in ("authorised_service",):
            continue
        w = {"authorised_service": 3.0, "independent": 1.4, "installation_only": 4.0}[lvl]
        if jt == "installation" and lvl == "installation_only":
            w = 5
        cands.append(key); weights.append(w)
    if not cands:  # fall back to any independent centre that serves the category
        for key, name, loc, cats, pins, hours, comm in CENTRES:
            if app["cat"] in cats and auth_level(key, app["brand"], d) in ("independent", "authorised_service"):
                cands.append(key); weights.append(1)
    return weighted(cands, weights)

def pick_tech(ckey, cat, cls, need_lvl, gas, d):
    ts = [t for t, m in TECH_META.items() if m["centre"] == ckey and m["active"] and (m["verified"] or rng.random() < 0.2)]
    if not ts:
        ts = [t for t, m in TECH_META.items() if m["centre"] == ckey]
    good = []
    for t in ts:
        lvl = SK.get((t, cat, cls), TECH_META[t]["base"] - 2)
        if gas and "gas" not in TECH_META[t]["certs"]:
            continue
        good.append((t, lvl))
    if not good:
        good = [(t, SK.get((t, cat, cls), 1)) for t in ts]
    ws = [max(0.2, 1 + (l - need_lvl) * 0.5) for t, l in good]
    t = weighted([g[0] for g in good], ws)
    return t, dict(good)[t]

def free_slot(tid, earliest, minutes):
    """First conflict-free start at or after `earliest` inside the technician's shift (mostly Mon-Sat)."""
    m = TECH_META[tid]
    s0 = dt.datetime.strptime(m["shift"][0], "%H:%M").time(); s1 = dt.datetime.strptime(m["shift"][1], "%H:%M").time()
    t = earliest
    for _ in range(200):
        if t.weekday() == 6 and rng.random() < 0.85:
            t = (t + dt.timedelta(days=1)).replace(hour=s0.hour, minute=s0.minute)
        day_start = t.replace(hour=s0.hour, minute=s0.minute, second=0, microsecond=0)
        day_end = t.replace(hour=s1.hour, minute=s1.minute, second=0, microsecond=0)
        if t < day_start:
            t = day_start
        t = t.replace(minute=(t.minute // 15) * 15, second=0, microsecond=0)
        end = t + dt.timedelta(minutes=minutes)
        if end > day_end:
            t = (t + dt.timedelta(days=1)).replace(hour=s0.hour, minute=s0.minute)
            continue
        if all(end <= a or t >= b for a, b in BUSY.get(tid, [])):
            BUSY.setdefault(tid, []).append((t, end + dt.timedelta(minutes=20)))
            return t
        t += dt.timedelta(minutes=30)
    return earliest

def haversine(a, b):
    R = 6371.0
    lon1, lat1, lon2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))

# ------------------------------------------------------------------ entitlement and money
def entitlement_on(app, fault, d):
    """Returns (entitlement, parts_only_brand) for a date."""
    brand = app["brand"]
    if app["comp_end"] and d <= app["comp_end"]:
        return "brand_warranty", False
    if fault and fault["cls"] == "compressor":
        po = WARRANTY[brand]["parts_only"]
        key = "compressor" if app["cat"] == "air_conditioner" else "fridge_compressor" if brand == "zenith" else "compressor"
        if key in po and app["start"] and d <= add_months(app["start"], po[key]):
            return "brand_warranty", True
    if app["plan_id"] and app["plan_id"] != uid("plan", f"warranty-{brand}"):
        pk = PLAN_KIND[app["plan_id"]]
        if pk["kind"] == "extended_warranty" and app["comp_end"] and d > app["comp_end"] and app["w_end"] and d <= app["w_end"]:
            return "extended_warranty", False
        if pk["kind"] == "amc" and app["w_end"] and app["w_end"] - dt.timedelta(days=365) <= d <= app["w_end"]:
            return "amc", False
    return "paid", False

def mrp(part_id):
    return PARTROW[part_id]["mrp_paise"]

def lines_for(app, jt, band, parts, entitlement, parts_only, d, extra_labour=0):
    """Quote lines with a payer per line. parts: list of (part_id, qty)."""
    r = rate_for(app["cat"], jt if jt in ("installation", "preventive_service", "uninstall_reinstall", "inspection_advice") else "repair", band, d)
    plan_id = app["plan_id"]
    pay_visit = pay_labour = pay_part = "household"
    if entitlement == "brand_warranty":
        pay_visit = pay_labour = "household" if parts_only else "brand_warranty"
        pay_part = "brand_warranty"
    elif entitlement == "extended_warranty":
        pay_visit = pay_labour = pay_part = "extended_warranty"
    elif entitlement == "amc":
        pay_visit = pay_labour = "amc"
    L = []
    if r["visit_fee_paise"]:
        L.append(dict(line_type="visit_fee", description="Visit and inspection", part_id=None, quantity=1, amount_paise=r["visit_fee_paise"], payer=pay_visit, plan_id=plan_id if pay_visit != "household" else None))
    L.append(dict(line_type="labour", description={"installation": "Installation labour", "preventive_service": "Preventive service labour"}.get(jt, "Repair labour"),
                  part_id=None, quantity=1, amount_paise=r["labour_paise"] + extra_labour, payer=pay_labour, plan_id=plan_id if pay_labour != "household" else None))
    for pid, q in parts:
        L.append(dict(line_type="part", description=PARTROW[pid]["name"], part_id=pid, quantity=q, amount_paise=mrp(pid) * q, payer=pay_part,
                      plan_id=plan_id if pay_part != "household" else None))
    by = {}
    for l in L:
        by[l["payer"]] = by.get(l["payer"], 0) + l["amount_paise"]
    for payer, amt in by.items():
        L.append(dict(line_type="tax", description="GST 18%", part_id=None, quantity=1, amount_paise=int(round(amt * 0.18)), payer=payer,
                      plan_id=plan_id if payer != "household" else None))
    return L

def write_quote(tid, ver, qtype, lines, created, valid_until=None, approved_at=None, channel=None):
    qid = uid("quote", f"{tid}-{ver}")
    add("quote", id=qid, ticket_id=tid, version=ver, quote_type=qtype, valid_until=valid_until, approved_at=approved_at,
        approval_channel=channel, approval_ref=f"wamid.{rng.randint(10**9, 10**10 - 1)}" if approved_at else None, created_at=created)
    for i, l in enumerate(lines):
        add("quote_line", id=uid("qline", f"{qid}-{i}"), quote_id=qid, **l)
    return qid

# ------------------------------------------------------------------ one ticket
CHECKLIST = {
    "air_conditioner": ["indoor filters cleaned", "indoor coil inspected", "drain line checked", "outdoor unit inspected", "refrigerant pressure checked", "electrical terminals tightened", "cooling performance verified"],
    "refrigerator": ["door seal checked", "condenser cleaned", "temperature verified after 30 min", "defrost system checked", "compressor current measured"],
    "washing_machine": ["drain filter cleaned", "inlet filter checked", "drum spin test", "levelling verified", "test wash cycle run"],
    "water_purifier": ["input TDS recorded", "output TDS recorded", "flow rate measured", "leak check at fittings", "filters inspected"],
    "water_heater": ["earthing verified", "insulation resistance measured", "thermostat tested", "leak check", "heat-up test"],
}
SYM_FLAVOUR = {"te": [" chala ibbandi ga undi", " rendu rojula nundi", " tondaraga randi"], "hi": [" do din se hai", " jaldi bhejiye", " kal se problem hai"], "en": [" please come asap", "", "", " since yesterday"],
               "ta": [" rendu naal ah", ""], "ml": [" randu divasam aayi", ""], "bn": [" dui din dhore", ""]}

def sim_ticket(app, fault, created, jt="repair", force=None, rating_override=None):
    force = force or {}
    hh = HH[app["hh"]]
    d = created.date()
    cat = app["cat"]
    tkid = uid("ticket", f"{app['key']}-{created.isoformat()}-{jt}")
    ent, parts_only = entitlement_on(app, fault, d) if jt not in ("installation", "preventive_service") else (
        ("brand_warranty" if jt == "installation" and False else "paid"), False)
    if jt == "preventive_service":
        ent, parts_only = entitlement_on(app, None, d)
        if ent == "brand_warranty":
            ent = "paid"           # warranty does not cover routine service
    centre = pick_centre(app, hh, jt, ent if jt == "repair" else None, d, force.get("centre"))
    if jt == "repair" and ent == "brand_warranty" and rng.random() < 0.6:
        jt_ticket = "coverage_claim"
    else:
        jt_ticket = jt
    set_centre(centre)
    need_lvl = fault["lvl"] if fault else 1
    cls = fault["cls"] if fault else ("install" if jt == "installation" else "service")
    gas = bool(fault and fault["gas"]) or (jt == "installation" and cat == "air_conditioner")
    tid, skill = pick_tech(centre, cat, cls if not (jt == "installation" and cat == "air_conditioner") else "install", need_lvl, gas, d) if not force.get("tech") else (force["tech"], SK.get((force["tech"], cat, cls), 3))
    tm = TECH_META[tid]
    # ---- parts needed (truth) and what is on hand
    parts_needed = []
    if fault:
        for abbr, prob, (qlo, qhi) in fault["parts"]:
            spec = PART_SPEC[abbr]
            if app["fam"] in spec[2] and rng.random() < prob:
                cands = part_ids_for(abbr, app["model"])
                if cands:
                    p = cands[0]
                    if ent == "paid" and len(cands) > 1 and rng.random() < 0.35:
                        p = next((c for c in cands if c["kind"] == "aftermarket"), cands[0])
                    parts_needed.append((p, rng.randint(qlo, qhi), abbr))
    if force.get("parts") is not None:
        parts_needed = []
        for abbr, q in force["parts"]:
            cands = part_ids_for(abbr, app["model"])
            parts_needed.append((cands[0], q, abbr))
    # ---- about 5% of requests are cancelled before any visit
    if not force and jt == "repair" and rng.random() < 0.05:
        ctk = add("ticket", id=tkid, centre_id=uid("centre", centre), household_id=hh["id"], appliance_id=app["id"], job_type="repair", _channel="whatsapp",
                  raw_inputs=[{"type": "text", "text": rng.choice(fault["sym"]).replace("{code}", "an error") if fault else "Please check"}], case_card={},
                  _urgency="standard", safety_flag=False, safety_reason=None, entitlement=ent, coverage_plan_id=app["plan_id"] if ent != "paid" else None,
                  visit_address=hh["addr"], visit_location=geo(hh["lon"], hh["lat"]), status="cancelled", first_visit_by=created + dt.timedelta(hours=72),
                  _brand_ref=None, created_at=created, updated_at=created + dt.timedelta(hours=rng.randint(2, 40)), closed_at=created + dt.timedelta(hours=rng.randint(2, 40)))
        return tkid
    # ---- ticket
    symptom = rng.choice(fault["sym"]) if fault else {"preventive_service": "Service due, please schedule", "installation": "New appliance installation"}.get(jt, "Please check")
    codes = fault["codes"].get(app["brand"], []) if fault else []
    code = rng.choice(codes) if codes else ""
    symptom = symptom.replace("{code}", code or "an error").strip()
    text = symptom + rng.choice(SYM_FLAVOUR.get(hh["lang"], [""]))
    urgency = "urgent" if (fault and (fault["safety"] or (cat == "refrigerator" and fault["cls"] in ("cooling", "compressor")))) or rng.random() < 0.06 else "planned" if jt in ("preventive_service", "installation") else "standard"
    lag_h = {"urgent": rng.uniform(3, 20), "standard": rng.uniform(20, 70), "planned": rng.uniform(48, 170)}[urgency]
    earliest = created + dt.timedelta(hours=lag_h)
    dur_p50, spread = (fault["dur"] if fault else ({"installation": (120, 30), "preventive_service": (65, 15)}.get(jt, (60, 15))))
    plan_min = int(round(dur_p50 * 1.15 / 15) * 15)
    start = free_slot(tid, earliest, plan_min + 25) if not force.get("start") else force["start"]
    band = fault["band"] if fault else "standard" if jt == "installation" else "basic"
    # estimate quote: planned (most likely) parts at MRP, labour by band
    est_parts = [(p["id"], q) for p, q, a in parts_needed] if parts_needed else []
    if fault and rng.random() < 0.38 and not force.get("parts"):
        mode = rng.choice(["drop", "drop", "add", "qty"])
        if mode == "drop" and est_parts:
            est_parts = []
        elif mode == "add":
            extra_c = [part_ids_for(a2, app["model"]) for a2, pr, qq in fault["parts"] if app["fam"] in PART_SPEC[a2][2]]
            extra_c = [c[0] for c in extra_c if c]
            if extra_c:
                pick = rng.choice(extra_c)
                if pick["id"] not in [e[0] for e in est_parts]:
                    est_parts = est_parts + [(pick["id"], 1)]
        elif mode == "qty" and est_parts:
            est_parts = [(pid, max(1, q - 1)) for pid, q in est_parts]
    lines_est = lines_for(app, jt_ticket if jt_ticket in ("installation", "preventive_service") else "repair", band, est_parts, ent, parts_only, d)
    safety = bool(fault and fault["safety"])
    brand_ref = f"BRC-{rng.randint(100000, 999999)}" if jt_ticket == "coverage_claim" else None
    tick = add("ticket", id=tkid, centre_id=uid("centre", centre), household_id=hh["id"], appliance_id=app["id"], job_type=jt_ticket, _channel=weighted(["whatsapp", "reminder", "app", "centre"], [85, 10 if jt == "preventive_service" else 1, 3, 2]) if jt != "preventive_service" else weighted(["reminder", "whatsapp", "app"], [60, 36, 4]),
               raw_inputs=[{"type": "text", "text": text}], case_card={}, _urgency=urgency, safety_flag=safety,
               safety_reason="current leakage at tap or body" if safety else None, entitlement=ent if jt != "installation" else "paid",
               coverage_plan_id=app["plan_id"] if ent != "paid" else None, visit_address=hh["addr"], visit_location=geo(hh["lon"], hh["lat"]),
               status="closed", first_visit_by=created + dt.timedelta(hours={"urgent": 24, "standard": 72, "planned": 168}[urgency]),
               _brand_ref=brand_ref, created_at=created, updated_at=created, closed_at=None)
    TICKETS_OF_APP.setdefault(app["key"], []).append(tkid)
    TICKET_FAULT[tkid] = fault
    # ---- visit 1
    skill_gap = skill - need_lvl
    p_diag = min(0.97, max(0.25, 0.76 + 0.09 * skill_gap + (0.05 if auth_level(centre, app["brand"], d) == "authorised_service" else 0)))
    diag_ok = rng.random() < p_diag
    def avail(abbr):
        p = 0.82 if abbr in POPULAR else 0.25 if abbr in RARE else 0.50
        if auth_level(centre, app["brand"], d) == "authorised_service":
            p += 0.1
        return rng.random() < min(0.95, p)
    parts_ok = all(avail(a) for p, q, a in parts_needed)
    outcome, second = "fixed", False
    if force.get("outcome"):
        outcome = force["outcome"]; second = outcome != "fixed"
    elif rng.random() < 0.02:
        outcome, second = "no_access", True
    elif fault and fault["cls"] == "compressor" and app["purchase"] and (SIM_NOW.date() - app["purchase"]).days > 365 * 7 and rng.random() < 0.18:
        outcome, second = "not_repairable", False
    elif not diag_ok:
        outcome, second = ("partial", True) if not parts_needed or rng.random() < 0.6 else ("needs_part", True)
    elif parts_needed and not parts_ok:
        outcome, second = "needs_part", True
    delay = rng.uniform(0, 18) if rng.random() < tm["reliability"] else rng.uniform(25, 95)
    ci = start + dt.timedelta(minutes=delay)
    actual = max(15, int(rng.lognormvariate(math.log(dur_p50), 0.25)))
    if outcome in ("partial", "needs_part"):
        actual = int(actual * rng.uniform(0.5, 0.9))
    co = ci + dt.timedelta(minutes=actual)
    v1 = make_visit(tkid, tid, centre, start, plan_min, ci, co, outcome, app, hh, fault, parts_needed, ent, False, None, cat, jt_ticket)
    final_visit, last_co, outcome_final = v1, co, outcome
    parts_used = parts_needed if outcome in ("fixed", "not_repairable") else ([] if outcome == "no_access" else [pn for pn in parts_needed if outcome == "partial" and rng.random() < 0.3])
    if second:
        gap = dt.timedelta(days=rng.choice([1, 2, 2, 3, 4]), hours=rng.randint(-2, 4))
        tid2 = tid if rng.random() < 0.7 else pick_tech(centre, cat, cls, need_lvl, gas, d)[0]
        s2 = free_slot(tid2, co + gap, 75)
        ci2 = s2 + dt.timedelta(minutes=rng.uniform(0, 20)); actual2 = max(20, int(rng.lognormvariate(math.log(dur_p50 * 0.7), 0.25)))
        co2 = ci2 + dt.timedelta(minutes=actual2)
        out2 = "fixed" if rng.random() < 0.93 else "not_repairable"
        # after a wrong first diagnosis the part set can change
        parts2 = parts_needed
        v2 = make_visit(tkid, tid2, centre, s2, 75, ci2, co2, out2, app, hh, fault, parts2, ent, True, v1["id"], cat, jt_ticket)
        final_visit, last_co, outcome_final, parts_used = v2, co2, out2, (parts2 if out2 == "fixed" else [])
        tid = tid2
    # ---- firm quote (v2) vs estimate (v1)
    final_parts = [(p["id"], q) for p, q, a in parts_used]
    extra = 0
    if rng.random() < 0.16 and fault:
        extra = rng.choice([150, 300, 450, 600]) * 100
    lines_fin = lines_for(app, jt_ticket if jt_ticket in ("installation", "preventive_service") else "repair", band, final_parts, ent, parts_only, d, extra_labour=extra)
    if jt in ("preventive_service", "installation"):
        qa = write_quote(tkid, 1, "firm", lines_fin, created + dt.timedelta(minutes=rng.randint(2, 40)), valid_until=created + dt.timedelta(days=5),
                         approved_at=created + dt.timedelta(minutes=rng.randint(5, 120)), channel="whatsapp")
        lines_used = lines_fin
    else:
        write_quote(tkid, 1, "estimate", lines_est, created + dt.timedelta(minutes=rng.randint(2, 40)), valid_until=created + dt.timedelta(days=3))
        t0 = v1["check_in_at"] or v1["planned_start"]
        qa = write_quote(tkid, 2, "firm", lines_fin, t0 + dt.timedelta(minutes=rng.randint(10, 35)),
                         valid_until=t0 + dt.timedelta(days=1), approved_at=t0 + dt.timedelta(minutes=rng.randint(36, 60)), channel=rng.choice(["whatsapp", "whatsapp", "in_person"]))
        lines_used = lines_fin
    tick["status"] = "closed"; tick["closed_at"] = last_co + dt.timedelta(minutes=rng.randint(3, 600)); tick["updated_at"] = tick["closed_at"]
    settle(tkid, lines_used, centre, parts_used, tick["closed_at"], app, hh, ent)
    feedback_for(tkid, final_visit, v1, outcome_final, second, tm, rating_override)
    events_for(app, tkid, jt, fault, parts_used, final_visit, outcome_final)
    if jt == "repair" and outcome_final == "fixed" and fault:
        EXP_CASES.append(dict(app=app, fault=fault, code=code, parts=parts_used, dur=actual, cost=sum(l["amount_paise"] for l in lines_used), first=not second, d=d,
                              src=final_visit["id"], pin=hh["pincode"], symptom=text))
    return tkid

def make_visit(tkid, tid, centre, start, plan_min, ci, co, outcome, app, hh, fault, parts, ent, is_return, parent, cat, jt):
    vid = uid("visit", f"{tkid}-{1 if not is_return else 2}")
    ends = start + dt.timedelta(minutes=plan_min)
    nci = outcome != "no_access"
    cause = rng.choice(fault["cause"]) if fault else None
    notes = {"fixed": "Fault rectified and tested with household present.", "partial": "Fault not fully resolved; further checks needed.",
             "needs_part": "Part not available on van; revisit once part arrives.", "not_repairable": "Repair not economical; replacement advised.",
             "no_access": "Household not available at the address."}[outcome]
    closed = outcome in ("fixed", "partial", "not_repairable", "needs_part")
    cs = ci if False else None
    row = add("visit", id=vid, ticket_id=tkid, technician_id=tid, centre_id=uid("centre", centre), planned_start=start, planned_end=ends,
              is_return_visit=is_return, parent_visit_id=parent, check_in_at=ci if nci else None,
              check_in_location=geo(hh["lon"] + rng.gauss(0, 0.0002), hh["lat"] + rng.gauss(0, 0.0002)) if nci else None,
              check_out_at=co if nci else None,
              checklist=[{"item": c, "done": rng.random() < (0.97 if outcome == "fixed" else 0.7)} for c in rng.sample(CHECKLIST[cat], k=min(len(CHECKLIST[cat]), rng.randint(3, len(CHECKLIST[cat]))))] if nci else [],
              outcome=outcome, outcome_notes=notes, root_cause_confirmed=cause if outcome == "fixed" else None,
              closure_otp_ref=None, closure_confirmed_at=None, rating=None, created_at=start - dt.timedelta(days=1), updated_at=co)
    if outcome in ("fixed", "not_repairable") and nci and closed:
        row["closure_otp_ref"] = f"otp_{rng.randint(10**7, 10**8 - 1):x}"
        row["closure_confirmed_at"] = co + dt.timedelta(minutes=rng.choice([2, 3, 4, 6, 9, 15, 40, 180]))
    VISITS.append(dict(id=vid, tech=tid, date=start.date(), start=start, ci=ci, outcome=outcome, centre=centre, cat=cat, row=row, hh=hh,
                       return_visit=is_return, ticket=tkid))
    for p, q, abbr in (parts if outcome in ("fixed", "not_repairable", "partial") else []):
        if outcome == "partial" and rng.random() > 0.3:
            continue
        src = weighted(["van", "centre", "parts_centre", "courier"], [58 if abbr in POPULAR else 12, 24, 14 if abbr not in RARE else 40, 4 if abbr not in RARE else 30]) if not is_return else weighted(["parts_centre", "courier", "centre"], [55, 25, 20])
        add("visit_part_used", id=uid("vpu", f"{vid}-{p['id']}"), visit_id=vid, part_id=p["id"], serial_no=f"SN{rng.randint(10**8, 10**9)}" if p["kind"] == "genuine" and rng.random() < 0.7 else None,
            quantity=q, source_type=src)
    return row

def settle(tkid, lines, centre, parts_used, closed_at, app, hh, ent):
    by = {}
    for l in lines:
        by[l["payer"]] = by.get(l["payer"], 0) + l["amount_paise"]
    ck = dict((c[0], c[6]) for c in CENTRES)[centre]
    labour_visit = sum(l["amount_paise"] for l in lines if l["line_type"] in ("visit_fee", "labour"))
    part_sum = sum(l["amount_paise"] for l in lines if l["line_type"] == "part")
    old = (SIM_NOW - closed_at).days
    for payer, amt in by.items():
        ptype = {"household": "household", "brand_warranty": "brand", "extended_warranty": "plan_provider", "amc": "plan_provider"}[payer]
        pid = hh["id"] if payer == "household" else uid("brand", app["brand"]) if payer == "brand_warranty" else app["plan_id"]
        lag = {"household": 0, "brand_warranty": rng.randint(30, 60), "extended_warranty": rng.randint(25, 50), "amc": rng.randint(0, 15)}[payer]
        status = "paid" if old > lag else "pending"
        if payer == "household" and rng.random() < 0.02:
            status = "failed" if old > 2 else "pending"
        add("settlement_line", id=uid("settle", f"{tkid}-r-{payer}"), ticket_id=tkid, party_type=ptype, party_id=pid, direction="receivable", amount_paise=amt,
            status=status, payment_ref=f"pay_{rng.randint(10**9, 10**10)}" if status == "paid" else None, due_at=closed_at + dt.timedelta(days=lag or 1),
            settled_at=closed_at + dt.timedelta(days=lag, hours=rng.randint(0, 20)) if status == "paid" else None)
    fee = int(round(ck * (labour_visit + part_sum * 0.15)))
    centre_pay = labour_visit - int(round(ck * labour_visit)) + int(part_sum * 0.12)
    old_c = old - 7
    add("settlement_line", id=uid("settle", f"{tkid}-p-centre"), ticket_id=tkid, party_type="centre", party_id=uid("centre", centre), direction="payable",
        amount_paise=max(0, centre_pay), status="paid" if old_c > 0 else "pending", payment_ref=f"po_{rng.randint(10**9, 10**10)}" if old_c > 0 else None,
        due_at=closed_at + dt.timedelta(days=7), settled_at=closed_at + dt.timedelta(days=7, hours=rng.randint(1, 20)) if old_c > 0 else None)
    pc_amt = sum(int(mrp(p["id"]) * q * (0.72 if p["kind"] == "genuine" else 0.62)) for p, q, a in parts_used if a not in POPULAR and rng.random() < 0.6)
    if pc_amt:
        pk = rng.choice(PARTS_CENTRES)[0]
        add("settlement_line", id=uid("settle", f"{tkid}-p-pc"), ticket_id=tkid, party_type="parts_centre", party_id=uid("pcentre", pk), direction="payable",
            amount_paise=pc_amt, status="paid" if old_c > 0 else "pending", payment_ref=f"po_{rng.randint(10**9, 10**10)}" if old_c > 0 else None,
            due_at=closed_at + dt.timedelta(days=7), settled_at=closed_at + dt.timedelta(days=7) if old_c > 0 else None)
    add("settlement_line", id=uid("settle", f"{tkid}-r-keepwell"), ticket_id=tkid, party_type="keepwell", party_id=None, direction="receivable", amount_paise=fee,
        status="paid" if old_c > 0 else "pending", payment_ref=None, due_at=closed_at + dt.timedelta(days=7), settled_at=closed_at + dt.timedelta(days=7) if old_c > 0 else None)

def feedback_for(tkid, final_visit, v1, outcome, second, tm, rating_override):
    late = (v1["check_in_at"] - v1["planned_start"]).total_seconds() / 60 > 25 if v1["check_in_at"] else False
    base = 4.5 - 0.9 * second - 0.5 * late - (1.2 if outcome == "not_repairable" else 0) + rng.gauss(0, 0.5)
    rating = rating_override or int(min(5, max(1, round(base))))
    if outcome == "no_access":
        return
    if rng.random() < 0.72 or rating_override:
        reasons = []
        if rating >= 4:
            reasons += rng.sample(["on_time", "polite", "explained_well", "clean_work", "fixed_first_time" if not second else "good_follow_up"], k=2)
        else:
            reasons += rng.sample([r for r in ["late", "repeat_visit" if second else "unclear_pricing", "part_unavailable" if second else "rushed", "price_higher_than_estimate"]], k=2)
        disp = rating <= 2 and rng.random() < 0.35
        add("feedback", id=uid("fb", f"{tkid}-h"), ticket_id=tkid, visit_id=final_visit["id"], from_type="household", rating=rating, reason_codes=pgarray(reasons),
            comment=rng.choice([None, None, "Good service", "Took too long", "Technician explained everything", "Had to wait for the part", "Fine"]), is_dispute=disp,
            resolution="Visit fee waived on next service" if disp else None, created_at=final_visit["check_out_at"] + dt.timedelta(hours=rng.randint(1, 40)) if final_visit["check_out_at"] else (final_visit["planned_end"] + dt.timedelta(hours=rng.randint(1, 40))))
        final_visit["rating"] = rating
    if second and rng.random() < 0.25:
        add("feedback", id=uid("fb", f"{tkid}-t"), ticket_id=tkid, visit_id=v1["id"], from_type="technician", rating=None, reason_codes=pgarray(["part_not_stocked"]),
            comment="Part not on van, parts centre did not have it in stock", is_dispute=False, resolution=None, created_at=v1["check_out_at"] or v1["check_in_at"] or v1["planned_end"])

def events_for(app, tkid, jt, fault, parts_used, visit, outcome):
    if outcome in ("no_access",):
        return
    at = visit["check_out_at"] or visit["planned_end"]
    et = {"installation": "install", "preventive_service": "service"}.get(jt, "repair")
    add("appliance_event", id=uid("event", f"{tkid}-main"), appliance_id=app["id"], event_type=et, occurred_at=at, ticket_id=tkid,
        details={"outcome": outcome, "fault": fault["name"] if fault else None, "centre_visit": visit["id"]})
    for p, q, a in parts_used:
        add("appliance_event", id=uid("event", f"{tkid}-{p['id']}"), appliance_id=app["id"], event_type="part_replaced", occurred_at=at, ticket_id=tkid,
            details={"part_no": p["part_no"], "qty": q, "kind": p["kind"]})
    if et in ("service", "repair") and outcome in ("fixed",):
        app["row"]["last_service_at"] = at.date() if (app["row"]["last_service_at"] is None or at.date() > app["row"]["last_service_at"]) else app["row"]["last_service_at"]

# ------------------------------------------------------------------ driver over the whole history
def season_w(fault, month):
    return SEASON[fault["season"]][month - 1]

def rand_created(d):
    hr = weighted(list(range(7, 24)), [3, 8, 9, 7, 5, 5, 5, 5, 5, 6, 7, 8, 8, 7, 5, 3, 1])
    return ist(d.year, d.month, d.day, hr, rng.randint(0, 59))

def simulate_history():
    index_skills(); index_rates(); index_parts()
    story_keys = {a["key"] for s in STORIES if s["existing"] for a in s["appliances"]}
    for key, app in list(APPS.items()):
        if key in story_keys:
            continue
        hh = HH[app["hh"]]
        w0 = max(HISTORY_START, hh["created"].date(), (app["install"] or app["purchase"] or HISTORY_START))
        w1 = (SIM_NOW - dt.timedelta(days=4)).date()
        if w1 <= w0:
            continue
        years = (w1 - w0).days / 365
        # installation inside the Keepwell era
        if app["install"] and app["install"] >= max(HISTORY_START, hh["created"].date()) and app["install"] <= w1:
            created = rand_created(app["install"] - dt.timedelta(days=rng.randint(1, 4)))
            sim_ticket(app, None, created, jt="installation")
        # repairs
        fam_faults = [f for f in FAULTS if f["cat"] == app["cat"] and app["fam"] in f["fams"]]
        age = ((SIM_NOW.date() - (app["purchase"] or SIM_NOW.date() - dt.timedelta(days=900))).days) / 365
        rate = {"air_conditioner": 1.15, "refrigerator": 0.5, "washing_machine": 0.7, "water_purifier": 0.85, "water_heater": 0.6}[app["cat"]] * (1 + 0.1 * age)
        n = 0
        L = rate * years
        while True:
            L -= rng.expovariate(1)
            if L < 0:
                break
            n += 1
        for _ in range(n):
            f = weighted(fam_faults, [x["w"] * season_w(x, 6) / 8 * 0 + x["w"] for x in fam_faults])
            for _try in range(30):
                d = w0 + dt.timedelta(days=rng.randint(0, (w1 - w0).days))
                if rng.random() < season_w(f, d.month) / max(SEASON[f["season"]]):
                    break
            if f["cls"] == "service":
                continue
            sim_ticket(app, f, rand_created(d))
        # preventive services
        interval = {"air_conditioner": 190, "water_purifier": 125, "water_heater": 365, "washing_machine": 365, "refrigerator": 0}[app["cat"]]
        if interval and (hh["diligent"] or rng.random() < 0.12):
            d = w0 + dt.timedelta(days=rng.randint(20, max(21, interval)))
            while d <= w1:
                if app["cat"] == "air_conditioner" and d.month in (8, 9, 10, 11, 12, 1) and rng.random() < 0.6:
                    d += dt.timedelta(days=45); continue
                sim_ticket(app, None, rand_created(d), jt="preventive_service")
                d += dt.timedelta(days=int(interval * rng.uniform(0.85, 1.25)))
    # ~5% of tickets are cancelled before a visit
    for t in rng.sample([t for t in TABLES["ticket"]], k=0):
        pass

def purge_future():
    """History must not contain events later than SIM_NOW: drop simulated tickets whose slots or settlement spilled past it."""
    cut = SIM_NOW - dt.timedelta(hours=1)
    bad = {t["id"] for t in TABLES["ticket"] if t.get("closed_at") and t["closed_at"] > cut}
    bad |= {v["ticket_id"] for v in TABLES["visit"] if (v["planned_end"] and v["planned_end"] > cut) or (v["check_out_at"] and v["check_out_at"] > cut)}
    bad_visits = {v["id"] for v in TABLES["visit"] if v["ticket_id"] in bad}
    bad_quotes = {q["id"] for q in TABLES["quote"] if q["ticket_id"] in bad}
    keep = lambda t, f: TABLES.__setitem__(t, [r for r in TABLES[t] if f(r)])
    keep("quote_line", lambda r: r["quote_id"] not in bad_quotes)
    keep("quote", lambda r: r["id"] not in bad_quotes)
    for t, col in (("visit_media", "visit_id"), ("visit_part_used", "visit_id"), ("reservation", "visit_id"), ("route_stop", "visit_id")):
        keep(t, lambda r, col=col: r[col] not in bad_visits)
    for t in ("appliance_event", "settlement_line", "feedback"):
        keep(t, lambda r: r.get("ticket_id") not in bad)
    keep("feedback", lambda r: not (r["created_at"] and r["created_at"] > SIM_NOW))
    for r in TABLES["reminder"]:
        if r.get("ticket_id") in bad:
            r["ticket_id"] = None
    keep("visit", lambda r: r["id"] not in bad_visits)
    keep("ticket", lambda r: r["id"] not in bad)
    VISITS[:] = [v for v in VISITS if v["id"] not in bad_visits]
    last = {}
    for e in TABLES["appliance_event"]:
        if e["event_type"] in ("service", "repair") and (e.get("details") or {}).get("outcome") == "fixed":
            d = e["occurred_at"].date(); last[e["appliance_id"]] = max(d, last.get(e["appliance_id"], d))
    for a in APPS.values():
        a["row"]["last_service_at"] = last.get(a["id"])
    return len(bad)

def story_history():
    """Controlled past events for story households: only what the scenarios need."""
    def A(k): return APPS[k]
    # C12: drain motor replaced 18 days ago at the centre, now failing again
    created = ist(2026, 11, 3, 9, 20)
    sim_ticket(A("a_c12"), FAULT_BY_KEY["wm_drain"], created, jt="repair", force=dict(centre="c_ls", parts=[("DMOT", 1)], outcome="fixed", start=ist(2026, 11, 3, 14, 0)), rating_override=4)
    # C04: filters replaced 4 months ago (membrane left as is)
    sim_ticket(A("a_c04"), None, ist(2026, 7, 18, 10, 30), jt="preventive_service", force=dict(centre="c_aq"))
    # C08: three ACs serviced earlier at different times
    sim_ticket(A("a_c08a"), None, ist(2025, 10, 12, 18, 5), jt="preventive_service", force=dict(centre="c_cc"))
    sim_ticket(A("a_c08b"), None, ist(2026, 2, 14, 12, 40), jt="preventive_service", force=dict(centre="c_cc"))
    sim_ticket(A("a_c08c"), None, ist(2026, 4, 20, 19, 15), jt="preventive_service", force=dict(centre="c_cc"))
    # C01: installed through Keepwell in December 2025 (backfilled as a closed installation job)
    sim_ticket(A("a_c01"), None, ist(2025, 12, 11, 20, 10), jt="installation", force=dict(centre="c_ip", start=ist(2025, 12, 14, 10, 30)))
    TABLES["appliance_event"][:] = [e for e in TABLES["appliance_event"] if not (e["appliance_id"] == A("a_c01")["id"] and e["event_type"] == "install" and e["ticket_id"] is None)]
    # C19: serviced earlier by Heatwell Authorised Service (c_hw); the brand now routes a claim to another centre
    sim_ticket(A("a_c19"), None, SIM_NOW - dt.timedelta(days=190, hours=3), jt="preventive_service", force=dict(centre="c_hw"))
    # C08: yesterday's reminder that the household is replying to
    for k in ("a_c08a", "a_c08b", "a_c08c"):
        add("reminder", id=uid("reminder", f"{k}-nov"), household_id=A(k)["hh"] and HH[A(k)["hh"]]["id"], appliance_id=A(k)["id"], reminder_type="service_due",
            due_on=dt.date(2026, 11, 20), template_name="service_due_v2", whatsapp_category="utility", status="read", scheduled_at=ist(2026, 11, 20, 18, 0),
            sent_at=ist(2026, 11, 20, 18, 0, ), delivered_at=ist(2026, 11, 20, 18, 0) + dt.timedelta(seconds=rng.randint(2, 40)), read_at=ist(2026, 11, 20, 20, 41) + dt.timedelta(minutes=rng.randint(-35, 70), seconds=rng.randint(0, 59)), action_taken=None, ticket_id=None,
            created_at=ist(2026, 11, 13, 6, 0))

def historic_reminders():
    """Past reminder log (sent and acted on). Future reminders are created by the app, not seeded."""
    for key, app in APPS.items():
        hh = HH[app["hh"]]
        if app["cat"] == "refrigerator":
            continue
        interval = {"air_conditioner": 180, "water_purifier": 120, "water_heater": 365, "washing_machine": 365}[app["cat"]]
        cons = [c for c in TABLES["consent_ledger"] if c["subject_id"] == hh["id"] and c["purpose"] == "service_reminders" and c["withdrawn_at"] is None]
        if not cons:
            continue
        d = max(hh["created"].date(), HISTORY_START) + dt.timedelta(days=rng.randint(30, interval))
        n = 0
        while d < SIM_NOW.date() - dt.timedelta(days=3) and n < 4:
            st = weighted(["acted", "read", "delivered", "snoozed", "suppressed", "failed"], [22, 38, 22, 9, 6, 3])
            sent = ist(d.year, d.month, d.day, rng.choice([9, 10, 11, 18, 19]), rng.randint(0, 59))
            tmpl = rng.choice(["service_due_v2", "service_due_v2", "seasonal_prep_v1"])
            cat = "marketing" if tmpl.startswith("seasonal") else "utility"
            add("reminder", id=uid("reminder", f"{key}-{d}"), household_id=hh["id"], appliance_id=app["id"], reminder_type="seasonal" if tmpl.startswith("seasonal") else "service_due",
                due_on=d, template_name=tmpl, whatsapp_category=cat, status=st, scheduled_at=sent,
                sent_at=None if st in ("suppressed",) else sent, delivered_at=None if st in ("suppressed", "failed") else sent + dt.timedelta(seconds=rng.randint(2, 60)),
                read_at=sent + dt.timedelta(minutes=rng.randint(3, 600)) if st in ("read", "acted", "snoozed") else None,
                action_taken={"acted": "booked_service", "snoozed": "snooze_14d"}.get(st), ticket_id=None, created_at=sent - dt.timedelta(days=7))
            d += dt.timedelta(days=int(interval * rng.uniform(0.9, 1.2))); n += 1

# ------------------------------------------------------------------ routes, metrics, experience cases
def build_routes():
    by = {}
    for v in VISITS:
        if v["row"]["check_in_at"] is None:
            continue
        by.setdefault((v["tech"], v["date"]), []).append(v)
    for (tid, d), vs in by.items():
        vs.sort(key=lambda x: x["start"])
        anchor = TECH_META[tid]["anchor"]
        pts = [anchor] + [(v["hh"]["lon"], v["hh"]["lat"]) for v in vs]
        km = sum(haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) * 1.35
        planned = int(km / 17 * 60)
        near = len(vs) > 1 and max(haversine((vs[0]["hh"]["lon"], vs[0]["hh"]["lat"]), (x["hh"]["lon"], x["hh"]["lat"])) for x in vs) < 5
        rid = uid("route", f"{tid}-{d}")
        add("route", id=rid, technician_id=tid, route_date=d, batched=bool(near), optimiser="manual", planned_travel_min=planned,
            actual_travel_min=int(planned * rng.uniform(0.85, 1.5)), created_at=ist(d.year, d.month, d.day, 8, 0))
        for i, v in enumerate(vs):
            add("route_stop", route_id=rid, seq=i + 1, visit_id=v["id"], planned_arrival=v["start"], actual_arrival=v["row"]["check_in_at"])

def build_metrics():
    end = SIM_NOW.date() - dt.timedelta(days=1)
    cut = end - dt.timedelta(days=180)
    by = {}
    firsts = {}
    for v in VISITS:
        if not v["return_visit"]:
            firsts[v["ticket"]] = v
    visits_per_ticket = {}
    for v in VISITS:
        visits_per_ticket[v["ticket"]] = visits_per_ticket.get(v["ticket"], 0) + 1
    for v in VISITS:
        if v["date"] < cut or v["return_visit"]:
            continue
        for cat in (v["cat"], "ALL"):
            by.setdefault((v["tech"], cat), []).append(v)
    for (tid, cat), vs in by.items():
        jobs = len(vs)
        ftf = sum(1 for v in vs if v["outcome"] == "fixed" and visits_per_ticket[v["ticket"]] == 1) / jobs
        ontime = sum(1 for v in vs if v["row"]["check_in_at"] and (v["row"]["check_in_at"] - v["start"]).total_seconds() <= 1800) / jobs
        rep = sum(1 for v in vs if visits_per_ticket[v["ticket"]] > 1) / jobs
        add("technician_metrics", technician_id=tid, category_code=cat, period_end=end, jobs=jobs, first_time_fix_rate=round(ftf, 4), on_time_rate=round(ontime, 4),
            repeat_visit_rate_30d=round(rep, 4), acceptance_rate=None, avg_quote_variance_pct=None, computed_at=ist(end.year, end.month, end.day, 23, 55) + dt.timedelta(minutes=30))

SYMPTOM_TECH = {  # technician-voice variations for imported job cards
    "prefix": ["", "", "Customer complaint: ", "Reported: "],
}
def build_experience(import_n=520):
    def row(fault, app_model, code, parts, dur, cost, first, d, src, pin, symptom, brand, cat, series):
        eid = uid("exp", f"{src or 'imp'}-{rng.random()}")
        add("experience_case", id=eid, source_visit_id=src, brand_id=uid("brand", brand), category_code=cat, model_series=series, pincode=pin,
            symptom_text=symptom, error_code=code or None, root_cause=rng.choice(fault["cause"]),
            parts=[{"part_no": p["part_no"], "qty": q} for p, q, a in parts], duration_min=dur, cost_paise=cost,
            outcome="fixed on first visit" if first else "fixed after part or second visit", verified_by_technician=rng.random() < 0.82 if src else True,
            embedding=None, created_at=ist(d.year, d.month, d.day, 18, 0))
    live_visits = {v["id"] for v in TABLES["visit"]}
    for e in EXP_CASES:
        if e["src"] not in live_visits:
            continue
        a = e["app"]; m = MODEL_BY_CODE[a["model"]]
        row(e["fault"], a["model"], e["code"], e["parts"], e["dur"], e["cost"], e["first"], e["d"], e["src"], e["pin"], clean_symptom(e["fault"], e["code"], a["brand"]), a["brand"], a["cat"], m[3])
    # job cards imported from partner centres before Keepwell existed
    fams_models = {}
    for m in MODELS:
        fams_models.setdefault(m[5], []).append(m)
    pins = ["500032", "500081", "500084", "500089", "500049", "500085", "500033", "500034", "500008", "500075", "500019", "500016"]
    for i in range(import_n):
        f = weighted(FAULTS, [x["w"] for x in FAULTS])
        fam = rng.choice(f["fams"])
        m = rng.choice(fams_models[fam])
        codes = f["codes"].get(m[0], [])
        code = rng.choice(codes) if codes else ""
        parts = []
        for abbr, prob, (qlo, qhi) in f["parts"]:
            if fam in PART_SPEC[abbr][2] and rng.random() < prob:
                c = part_ids_for(abbr, m[2])
                if c:
                    parts.append((rng.choice(c[:2]), rng.randint(qlo, qhi), abbr))
        cost = sum(mrp(p["id"]) * q for p, q, a in parts) + rate_for(m[1], "repair", f["band"], dt.date(2026, 1, 1))["labour_paise"] + rate_for(m[1], "repair", f["band"], dt.date(2026, 1, 1))["visit_fee_paise"]
        d = dt.date(2023, 4, 1) + dt.timedelta(days=rng.randint(0, 1250))
        row(f, m[2], code, parts, max(20, int(rng.lognormvariate(math.log(f["dur"][0]), 0.25))), int(cost * 1.18), rng.random() < 0.72, d, None, rng.choice(pins),
            clean_symptom(f, code, m[0]), m[0], m[1], m[3])

def clean_symptom(fault, code, brand):
    s = rng.choice(fault["sym"]).replace("{code}", code or "no code")
    return rng.choice(["", "", "", "Customer reports: "]) + s

if __name__ == "__main__":
    build_catalogue(); build_rates(); build_coverage_and_policy(); build_supply()
    build_story_households(); build_random_households()
    simulate_history(); story_history(); historic_reminders(); build_routes(); build_metrics(); build_experience()
    print({k: len(v) for k, v in TABLES.items() if k in ("ticket", "visit", "quote", "quote_line", "settlement_line", "feedback", "route", "route_stop",
                                                          "experience_case", "technician_metrics", "reminder", "appliance_event", "visit_part_used")})
