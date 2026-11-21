"""Forward-looking state at 21 Nov 2026 08:00 IST: in-flight jobs already booked, technician calendars, part reservations.
These are inputs the live app must respect. Offers, visit plans and rankings are NOT seeded."""
from common import *
from catalogue import *
from world import *
from people import *
from history import *
from stories import STORIES

DAYS = [SIM_NOW.date() + dt.timedelta(days=i) for i in range(0, 8)]    # 21 Nov .. 28 Nov

def build_inflight(n=26):
    story_keys = {a["key"] for s in STORIES if s["existing"] for a in s["appliances"]}
    pool = [a for k, a in APPS.items() if k not in story_keys and a["cat"] in ("air_conditioner", "washing_machine", "water_purifier", "water_heater", "refrigerator")]
    rng.shuffle(pool)
    out = []
    for app in pool[:n]:
        hh = HH[app["hh"]]
        d = SIM_NOW.date()
        fam_faults = [f for f in FAULTS if f["cat"] == app["cat"] and app["fam"] in f["fams"] and f["cls"] != "service"]
        jt = "preventive_service" if rng.random() < 0.3 and app["cat"] != "refrigerator" else "repair"
        fault = rng.choice(fam_faults) if jt == "repair" else None
        created = SIM_NOW - dt.timedelta(hours=rng.randint(10, 70))
        ent, po = entitlement_on(app, fault, d) if jt == "repair" else ("paid", False)
        centre = pick_centre(app, hh, jt, ent if jt == "repair" else None, d)
        set_centre(centre)
        cls = fault["cls"] if fault else "service"
        tid, skill = pick_tech(centre, app["cat"], cls, fault["lvl"] if fault else 1, bool(fault and fault["gas"]), d)
        dur = fault["dur"][0] if fault else 65
        start = free_slot(tid, SIM_NOW + dt.timedelta(hours=weighted([rng.randint(2, 10), rng.randint(20, 34), rng.randint(40, 60), rng.randint(60, 100)], [25, 30, 30, 15])), int(dur * 1.15) + 25)
        tk = uid("ticket", f"inflight-{app['key']}")
        code = ""
        sym = (rng.choice(fault["sym"]).replace("{code}", rng.choice(fault["codes"].get(app["brand"], [""]) or [""]) or "an error") if fault else "Service due, please schedule")
        status = "scheduled"
        add("ticket", id=tk, centre_id=uid("centre", centre), household_id=hh["id"], appliance_id=app["id"], job_type="coverage_claim" if ent == "brand_warranty" and jt == "repair" and rng.random() < 0.6 else jt,
            _channel="whatsapp", raw_inputs=[{"type": "text", "text": sym}], case_card={}, _urgency="standard", safety_flag=False, safety_reason=None, entitlement=ent,
            coverage_plan_id=app["plan_id"] if ent != "paid" else None, visit_address=hh["addr"], visit_location=geo(hh["lon"], hh["lat"]), status=status,
            first_visit_by=created + dt.timedelta(hours=72), _brand_ref=None, created_at=created, updated_at=created + dt.timedelta(hours=1), closed_at=None)
        vid = uid("visit", f"{tk}-1")
        plan_min = int(round(dur * 1.15 / 15) * 15)
        add("visit", id=vid, ticket_id=tk, technician_id=tid, centre_id=uid("centre", centre), planned_start=start, planned_end=start + dt.timedelta(minutes=plan_min),
            is_return_visit=False, parent_visit_id=None, check_in_at=None, check_in_location=None, check_out_at=None, checklist=[], outcome=None, outcome_notes=None,
            root_cause_confirmed=None, closure_otp_ref=None, closure_confirmed_at=None, rating=None, created_at=created + dt.timedelta(hours=1), updated_at=created + dt.timedelta(hours=1))
        # estimate approved when the household chose the slot
        parts = []
        if fault:
            for abbr, prob, (qlo, qhi) in fault["parts"]:
                if app["fam"] in PART_SPEC[abbr][2] and prob >= 0.5:
                    c = part_ids_for(abbr, app["model"])
                    if c:
                        parts.append((c[0]["id"], qlo))
        lines = lines_for(app, jt if jt == "preventive_service" else "repair", fault["band"] if fault else "basic", parts, ent, po, d)
        write_quote(tk, 1, "estimate" if jt == "repair" else "firm", lines, created + dt.timedelta(minutes=30), valid_until=created + dt.timedelta(days=3),
                    approved_at=created + dt.timedelta(minutes=rng.randint(40, 300)), channel="whatsapp")
        out.append(dict(tk=tk, vid=vid, tid=tid, start=start, end=start + dt.timedelta(minutes=plan_min), parts=parts, centre=centre, app=app, fault=fault))
    # a few visits wait on a part held at a parts centre
    pc_keys = [k for k, *_ in PARTS_CENTRES]
    for o in out:
        if o["fault"] and o["parts"] and rng.random() < 0.28:
            pid, q = o["parts"][0]
            holders = [s for s in TABLES["stock"] if s["holder_type"] == "parts_centre" and s["part_id"] == pid and s["quantity"] > 0]
            if holders:
                h = rng.choice(holders)
                add("reservation", id=uid("resv", o["vid"]), centre_id=uid("centre", o["centre"]), part_id=pid, quantity=q, holder_type="parts_centre", holder_id=h["holder_id"], visit_id=o["vid"],
                    ready_by=o["start"] - dt.timedelta(hours=rng.randint(2, 18)), status="confirmed", created_at=SIM_NOW - dt.timedelta(hours=rng.randint(2, 30)))
    return out

def build_calendars(inflight):
    booked = {}
    for o in inflight:
        booked.setdefault((o["tid"], o["start"].date()), []).append(o)
    for tid, m in TECH_META.items():
        if not m["active"]:
            continue
        s0 = dt.datetime.strptime(m["shift"][0], "%H:%M").time(); s1 = dt.datetime.strptime(m["shift"][1], "%H:%M").time()
        leave = set(rng.sample(DAYS, k=1)) if rng.random() < 0.12 else set()
        for d in DAYS:
            sunday = d.weekday() == 6
            if sunday and rng.random() < 0.65:
                continue
            if d == SIM_NOW.date() and False:
                continue
            wins = [(dt.datetime.combine(d, s0, IST), dt.datetime.combine(d, dt.time(13, 0), IST)),
                    (dt.datetime.combine(d, dt.time(14, 0), IST), dt.datetime.combine(d, s1, IST))]
            if sunday:
                wins = [wins[0]]
            if d in leave:
                for a, b in wins:
                    add("technician_availability", id=uid("avail", f"{tid}-{a.isoformat()}"), technician_id=tid, centre_id=uid("centre", m["centre"]), slot_start=a, slot_end=b, status="blocked", held_until=None, visit_id=None)
                continue
            for a, b in wins:
                cur = a
                for o in sorted(booked.get((tid, d), []), key=lambda x: x["start"]):
                    bs, be = o["start"], o["end"] + dt.timedelta(minutes=20)
                    if be <= a or bs >= b:
                        continue
                    bs, be = max(bs, a), min(be, b)
                    if bs > cur:
                        add("technician_availability", id=uid("avail", f"{tid}-{cur.isoformat()}"), technician_id=tid, centre_id=uid("centre", m["centre"]), slot_start=cur, slot_end=bs, status="open", held_until=None, visit_id=None)
                    add("technician_availability", id=uid("avail", f"{tid}-{bs.isoformat()}"), technician_id=tid, centre_id=uid("centre", m["centre"]), slot_start=bs, slot_end=be, status="booked", held_until=None, visit_id=o["vid"])
                    cur = be
                if cur < b:
                    add("technician_availability", id=uid("avail", f"{tid}-{cur.isoformat()}"), technician_id=tid, centre_id=uid("centre", m["centre"]), slot_start=cur, slot_end=b, status="open", held_until=None, visit_id=None)
