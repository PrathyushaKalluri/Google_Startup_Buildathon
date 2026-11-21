"""Households, members, appliances, consent. Story households come from stories.py; the rest are random but realistic."""
from common import *
from catalogue import *
from world import *
from stories import STORIES

HH = {}     # key -> dict
APPS = {}   # key -> dict
FEMALE = ["Lakshmi", "Padmaja", "Swathi", "Divya", "Anusha", "Sravani", "Kavitha", "Sireesha", "Deepika", "Nandini", "Radhika", "Sunitha", "Pallavi", "Jyothi",
          "Madhavi", "Rekha", "Shruthi", "Bhavana", "Aparna", "Sowmya", "Vani", "Archana", "Neelima", "Geetha", "Preethi", "Ayesha", "Farah", "Shabana", "Anita", "Pooja"]
MALE = ["Ramakrishna", "Satyanarayana", "Venkatesh", "Chaitanya", "Srikanth", "Vamsi", "Rohit", "Aditya", "Nikhil", "Praveen", "Sai Kiran", "Teja", "Mohan", "Rahul",
        "Vinay", "Kalyan", "Abhishek", "Tarun", "Mohammed Ali", "Zubair", "Imtiyaz", "Gopal", "Sunil", "Deepak", "Hemanth", "Jagadish", "Uday", "Varun", "Karan", "Sameer"]
SURN = ["Reddy", "Rao", "Naidu", "Sharma", "Iyer", "Nair", "Menon", "Gupta", "Agarwal", "Khan", "Shaik", "Patel", "Varma", "Chowdary", "Kulkarni", "Joshi", "Das", "Sen", "Pillai", "Murthy", "Bhat", "Singh", "Yadav", "Goud", "Rajan"]
LOC_W = [("Gachibowli", 8), ("Kondapur", 8), ("Madhapur", 8), ("HITEC City", 6), ("Manikonda", 6), ("Financial District", 5), ("Kokapet", 4), ("Narsingi", 3),
         ("Miyapur", 5), ("Kukatpally", 6), ("Nallagandla", 4), ("Lingampally", 3), ("Tolichowki", 3), ("Jubilee Hills", 4), ("Banjara Hills", 3), ("Begumpet", 3)]
COMM_BY_LOC = {}
for n, l, fl in COMMUNITIES:
    COMM_BY_LOC.setdefault(l, []).append((n, fl))

def comm_row(name):
    return next((c for c in TABLES["community"] if c["name"] == name), None)

def parse_point(wkt):
    inside = wkt.split("(")[1].rstrip(")")
    lon, lat = inside.split()
    return float(lon), float(lat)

def warranty_end(brand, start):
    m = WARRANTY[brand]["comp"]
    y = start.year + (start.month - 1 + m) // 12
    mo = (start.month - 1 + m) % 12 + 1
    import calendar
    d = min(start.day, calendar.monthrange(y, mo)[1])
    return dt.date(y, mo, d)

def add_months(d, m):
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    return dt.date(y, mo, min(d.day, 28))

def make_household(key, locality, community, flat, floor, lift, lang, parking, members, created_at, story=None, verified_loc=False, pincode_missing=False, share_override=None):
    hid = uid("household", key)
    ph = unique_phone()
    lat0, lon0, pin = LOC[locality]
    if community and comm_row(community):
        lon, lat = parse_point(comm_row(community)["location"])
        lon += rng.gauss(0, 0.0007); lat += rng.gauss(0, 0.0007)
    else:
        lon, lat = jitter(locality, 0.004)
    addr = ", ".join(x for x in [flat, community, locality, "Hyderabad"] if x)
    prefs = {"channel": "whatsapp", "max_non_urgent_per_month": rng.choice([1, 2, 2, 3]),
             "quiet_hours": "21:00-08:00", "reminder_lead_days": rng.choice([3, 5, 7])}
    if rng.random() < 0.25:
        prefs["preferred_days"] = rng.choice([["sat", "sun"], ["sun"], ["mon", "tue", "wed", "thu", "fri"]])
    slots = {"days": rng.choice([["sat", "sun"], ["mon", "tue", "wed", "thu", "fri", "sat"], ["sun"]]),
             "window": rng.choice(["09:00-13:00", "10:00-14:00", "14:00-18:00", "08:30-11:30"]),
             "note": rng.choice(["call before arriving", "work from home on weekdays", "someone is home all day", "elderly parents at home", None])}
    row = add("household", id=hid, phone_enc=phone_enc(ph), phone_hash=phone_hash(ph), phone_verified_at=created_at + dt.timedelta(minutes=2), verified_via=rng.choice(["call_line", "otp", "otp"]), language=lang, address_line=addr,
              pincode=None if pincode_missing else pin, location=geo(lon, lat), location_verified=verified_loc,
              community_id=uid("community", community) if community and comm_row(community) else None,
              access_notes={k: v for k, v in dict(floor=floor, lift=lift, parking=parking).items() if v is not None},
              preferred_slots=slots, status="active", merged_into_id=None, created_at=created_at, updated_at=created_at)
    HH[key] = dict(id=hid, phone=ph, lon=lon, lat=lat, locality=locality, pincode=pin if not pincode_missing else None, lang=lang,
                   created=created_at, members=[], apps=[], diligent=rng.random() < 0.6, key=key, story=story, addr=addr)
    for i, (mname, role) in enumerate(members):
        mph = ph if i == 0 else unique_phone()
        add("household_member", id=uid("member", f"{key}-{i}"), household_id=hid, name=mname, phone_enc=phone_enc(mph), phone_hash=phone_hash(mph),
            role=role, may_raise_ticket=not (role == "family" and rng.random() < 0.15), created_at=created_at)
        HH[key]["members"].append(dict(name=mname, role=role, phone=mph))
    # consent ledger
    purposes = [("memory", 1.0), ("share_technical_history", 0.8), ("service_reminders", 0.82), ("warranty_alerts", 0.62), ("follow_up", 0.86),
                ("photos_voice", 0.78), ("video_diagnosis", 0.4), ("frame_retention", 0.3), ("analytics", 0.5)]
    for p, prob in purposes:
        if share_override is not None and p == "share_technical_history":
            prob = 1.0 if share_override else 0.0
        if rng.random() < prob:
            add("consent_ledger", id=uid("consent", f"{key}-{p}"), subject_type="household", subject_id=hid, purpose=p, scope_centre_id=None, notice_version="v1.0",
                granted_at=created_at + dt.timedelta(minutes=rng.randint(1, 9)), channel="whatsapp",
                withdrawn_at=None, evidence={"message": "tapped Agree on consent card", "language": lang})
    return HH[key]

def make_appliance(hh, key, model_code, purchase, install, serial, source, room, verified, model_text=None, installed_by=None, plan=None, plan_end=None,
                   true_model=None, created=None, hide_model=False):
    mc = true_model or model_code
    m = MODEL_BY_CODE[mc]
    brand, cat = m[0], m[1]
    aid = uid("appliance", key)
    start = install or purchase
    plan_id, w_end = None, None
    if start:
        comp_end = warranty_end(brand, start)
        w_end = comp_end
        if comp_end >= SIM_NOW.date():
            plan_id = uid("plan", f"warranty-{brand}")
        elif plan:
            plan_id = uid("plan", plan); w_end = plan_end
        elif rng.random() < 0.16:
            ext_end = add_months(comp_end, 24)
            if ext_end >= SIM_NOW.date():
                plan_id = uid("plan", "ext-assurenest"); w_end = ext_end
    elif plan:
        plan_id = uid("plan", plan); w_end = plan_end
    if plan and plan_id != uid("plan", plan) and plan_end and plan_end >= SIM_NOW.date() and brand != "zenith":
        pass
    usage = {"family_size": len(hh["members"]) or rng.randint(2, 5)}
    if cat == "air_conditioner":
        usage["hours_per_day"] = rng.choice([4, 6, 8, 10, 12])
    if cat == "water_purifier":
        usage["water_source"] = rng.choice(["municipal", "borewell", "tanker mix"])
    if cat == "washing_machine":
        usage["loads_per_week"] = rng.choice([3, 4, 5, 7])
    row = add("appliance", id=aid, household_id=hh["id"], category_code=cat, brand_id=uid("brand", brand),
              model_id=None if hide_model or model_code is None else uid("model", model_code), model_text=model_text or (model_code if rng.random() < 0.4 else None),
              serial_no=serial, purchase_date=purchase, purchase_source=source, invoice_file_ref=None, install_date=install,
              installed_by=installed_by, warranty_start=start, warranty_end=w_end, coverage_plan_id=plan_id, usage_profile=usage, room=room,
              care_index=None, care_index_reasons=[], care_index_updated_at=None, last_service_at=None, last_served_centre_id=None, next_due_at=None,
              serial_norm=(serial or "").replace(" ", "").replace("-", "").upper() or None, identity_status="verified" if (verified and serial) else "provisional", merged_into_id=None,
              first_seen_via="household", first_seen_centre_id=None, status="active", created_at=created or hh["created"], updated_at=created or hh["created"])
    APPS[key] = dict(id=aid, hh=hh["key"], model=mc, brand=brand, cat=cat, fam=m[5], purchase=purchase, install=install, start=start,
                     plan_id=plan_id, w_end=w_end, comp_end=warranty_end(brand, start) if start else None, row=row, plan_key=plan, key=key,
                     serial=serial, year_from=m[4])
    hh["apps"].append(key)
    return APPS[key]

def tech_of(ckey, i=0):
    return uid("tech", f"{ckey}-{i}")

def build_story_households():
    for s in STORIES:
        if not s["existing"]:
            continue
        h = s["hh"]
        created = ist(2025, rng.randint(10, 12), rng.randint(1, 27), rng.randint(9, 20), rng.randint(0, 59)) if rng.random() < 0.6 else ist(2026, rng.randint(1, 8), rng.randint(1, 27), rng.randint(9, 20), rng.randint(0, 59))
        if s.get('prior_service') or s.get('prior_repair') or s['id'] in ('C01', 'C08'):
            created = ist(2025, 9, rng.randint(3, 20), rng.randint(9, 20), rng.randint(0, 59))
        hh = make_household(f"hh_{s['id'].lower()}", h["locality"], h["community"], h["flat"], h["floor"], h["lift"], h["lang"], h["parking"], h["members"], created, story=s["id"], verified_loc=rng.random() < 0.4,
                            share_override=(False if s.get("share_consent") is False else True if s["id"] == "C19" else None))
        for a in s["appliances"]:
            installed_by = tech_of(a["installed_by"], 0) if a.get("installed_by") else None
            make_appliance(hh, a["key"], a["model"], a["purchase"], a["install"], a["serial"], a["source"], a["room"], a["verified"], model_text=a.get("model_text"),
                           installed_by=installed_by, plan=a.get("plan"), plan_end=a.get("plan_end"), true_model=a.get("true_model"), created=created, hide_model=a["model"] is None)
            # backfilled lifecycle events
            if a.get("purchase"):
                add("appliance_event", id=uid("event", f"{a['key']}-purchase"), appliance_id=APPS[a["key"]]["id"], event_type="purchase",
                    occurred_at=ist(a["purchase"].year, a["purchase"].month, a["purchase"].day, 12), ticket_id=None,
                    details={"source": "invoice" if a.get("invoice") else "household_recall", "retailer": a.get("source")})
            if a.get("install"):
                add("appliance_event", id=uid("event", f"{a['key']}-install"), appliance_id=APPS[a["key"]]["id"], event_type="install",
                    occurred_at=ist(a["install"].year, a["install"].month, a["install"].day, 15), ticket_id=None,
                    details={"source": "household_recall"})

def build_random_households(n=150):
    names = set()
    models_by_cat = {}
    for m in MODELS:
        models_by_cat.setdefault(m[1], []).append(m)
    for i in range(n):
        loc = weighted([l for l, w in LOC_W], [w for l, w in LOC_W])
        comm = None
        if loc in COMM_BY_LOC and rng.random() < 0.7:
            comm, fl = rng.choice(COMM_BY_LOC[loc])
            flat = f"Flat {rng.randint(1, fl)}{rng.randint(0, 1)}{rng.randint(1, 9)}, {rng.choice(['Block A', 'Block B', 'Tower 1', 'Tower 2', 'Block C'])}"
            floor = int(flat.split()[1][:-2] or 1)
            lift = floor > 3
        else:
            flat = f"{rng.randint(1, 60)}-{rng.randint(1, 99)}/{rng.randint(1, 20)}, {rng.choice(['Road No 3', 'Main Road', 'Lane 2', 'Colony Road'])}"
            floor, lift = rng.randint(0, 3), False
        lang = weighted(["te", "hi", "en", "ta", "ml", "bn"], [45, 20, 20, 6, 5, 4])
        while True:
            owner = f"{rng.choice(FEMALE + MALE)} {rng.choice(SURN)}"
            if owner not in names:
                names.add(owner); break
        members = [(owner, "owner")]
        for _ in range(rng.choice([0, 0, 1, 1, 2])):
            members.append((f"{rng.choice(FEMALE + MALE)} {owner.split()[-1]}", "family"))
        created = ist(2025, 9, 1) + dt.timedelta(days=int(rng.random() ** 0.8 * 440), hours=rng.randint(9, 20), minutes=rng.randint(0, 59))
        created = min(created, SIM_NOW - dt.timedelta(days=5))
        hh = make_household(f"hh_r{i:02d}", loc, comm, flat, floor, lift, lang, rng.choice(["basement", "stilt", "open parking", "visitor bay", None]), members, created,
                            verified_loc=rng.random() < 0.3, pincode_missing=rng.random() < 0.1)
        for j in range(weighted([1, 2, 3, 4], [30, 38, 24, 8])):
            cat = weighted(["air_conditioner", "refrigerator", "washing_machine", "water_purifier", "water_heater"], [42, 18, 18, 13, 9])
            m = rng.choice(models_by_cat[cat])
            age_y = min(7.0, max(0.2, rng.gammavariate(2.0, 1.3)))
            purchase = SIM_NOW.date() - dt.timedelta(days=int(age_y * 365))
            purchase = max(purchase, dt.date(m[4], 1, 15))
            if purchase > SIM_NOW.date() - dt.timedelta(days=20):
                purchase = SIM_NOW.date() - dt.timedelta(days=rng.randint(30, 400))
            install = purchase + dt.timedelta(days=rng.randint(0, 5)) if cat in ("air_conditioner", "water_purifier", "water_heater", "washing_machine") or rng.random() < 0.5 else None
            pc = BRAND_CODE[m[0]]
            serial = f"{pc}{str(purchase.year)[2:]}{m[2][3:5]}{rng.randint(1000000, 9999999)}" if rng.random() < 0.7 else None
            verified = serial is not None and rng.random() < 0.8
            model_text = None
            hide = False
            if not verified and rng.random() < 0.55:
                hide = True
                model_text = rng.choice([f"{m[0].capitalize()} {cat.replace('_', ' ')}", f"{m[0].capitalize()} {m[6].get('tonnage', m[6].get('litres', m[6].get('kg', '')))}", f"old {m[0].capitalize()}"])
            if rng.random() < 0.12:
                purchase_known = None
            else:
                purchase_known = purchase
            plan = None; plan_end = None
            if rng.random() < 0.12:
                plan = rng.choice([p for p in ("amc-coolcraft", "amc-aquacare", "amc-metro") if cat in next(c for c in TABLES["coverage_plan"] if c["id"] == uid("plan", p))["covers"]["categories"]] or [None])
                if plan:
                    plan_end = SIM_NOW.date() + dt.timedelta(days=rng.randint(40, 330))
            a = make_appliance(hh, f"a_r{i:02d}_{j}", m[2], purchase_known, install if purchase_known else None, serial,
                               rng.choice(["Retail store", "Online, brand store", "E-commerce marketplace", "Local dealer", "Brand dealer", None]),
                               rng.choice(["Bedroom", "Living room", "Kitchen", "Utility", "Master bedroom", "Kids room", "Bathroom 1"]), verified, model_text=model_text,
                               plan=plan, plan_end=plan_end, hide_model=hide)
            if purchase_known:
                add("appliance_event", id=uid("event", f"{a['key']}-purchase"), appliance_id=a["id"], event_type="purchase",
                    occurred_at=ist(purchase.year, purchase.month, purchase.day, 12), ticket_id=None,
                    details={"source": rng.choice(["invoice", "household_recall", "sticker"]), "retailer": a["row"]["purchase_source"]})
    # a few households withdrew reminder consent
    wd = [c for c in TABLES["consent_ledger"] if c["purpose"] == "service_reminders" and rng.random() < 0.06]
    for c in wd:
        c["withdrawn_at"] = c["granted_at"] + dt.timedelta(days=rng.randint(20, 200))
        if c["withdrawn_at"] > SIM_NOW:
            c["withdrawn_at"] = SIM_NOW - dt.timedelta(days=3)

if __name__ == "__main__":
    build_catalogue(); build_rates(); build_coverage_and_policy(); build_supply()
    build_story_households(); build_random_households()
    print({k: len(v) for k, v in TABLES.items() if k in ("household", "household_member", "appliance", "consent_ledger", "appliance_event")})
    import collections
    print(collections.Counter(a["cat"] for a in APPS.values()))
