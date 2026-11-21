"""Supply side and households: localities, communities, service centres, technicians, parts centres, stock."""
from common import *
from catalogue import *

# name: (lat, lon, pincode)
LOC = {
    "Gachibowli": (17.4401, 78.3489, "500032"), "Financial District": (17.4166, 78.3436, "500032"),
    "Kondapur": (17.4610, 78.3650, "500084"), "Madhapur": (17.4486, 78.3910, "500081"),
    "HITEC City": (17.4435, 78.3772, "500081"), "Manikonda": (17.4035, 78.3850, "500089"),
    "Kokapet": (17.3930, 78.3340, "500075"), "Narsingi": (17.3868, 78.3570, "500075"),
    "Miyapur": (17.4967, 78.3565, "500049"), "Kukatpally": (17.4947, 78.3996, "500085"),
    "Nallagandla": (17.4745, 78.3060, "500019"), "Lingampally": (17.4930, 78.3180, "500019"),
    "Tolichowki": (17.4019, 78.4104, "500008"), "Jubilee Hills": (17.4325, 78.4070, "500033"),
    "Banjara Hills": (17.4126, 78.4482, "500034"), "Begumpet": (17.4440, 78.4676, "500016"),
    "Shamshabad": (17.2403, 78.4294, "501218"),   # deliberately outside every service area
}
def jitter(loc, sd=0.0055):
    lat, lon, pin = LOC[loc]
    return lon + rng.gauss(0, sd), lat + rng.gauss(0, sd)

COMMUNITIES = [  # fictional gated communities
    ("Lakeview Heights", "Gachibowli", 14), ("Orchid Meadows", "Kondapur", 12), ("Skyline Residency", "Madhapur", 22),
    ("Emerald Courts", "Manikonda", 9), ("Sai Greens", "Miyapur", 7), ("Palm Terrace", "Kokapet", 18),
    ("Silver Oak Enclave", "Nallagandla", 8), ("Raintree Towers", "HITEC City", 26), ("Jasmine Gardens", "Kukatpally", 6),
    ("Harbour Point", "Financial District", 24), ("Maple Woods", "Tolichowki", 5), ("Cedar Park", "Jubilee Hills", 6),
]

CENTRES = [  # key, name, locality, categories, pincodes, hours, commission
    ("c_av", "Aerovane Authorised Service, Gachibowli", "Gachibowli", ["air_conditioner"], ["500032", "500084", "500081", "500089", "500075"], ("09:00", "18:30"), 0.10),
    ("c_zn", "Zenith Care Hub, Kondapur", "Kondapur", ["air_conditioner", "refrigerator", "washing_machine"], ["500084", "500081", "500032", "500019", "500049", "500075"], ("09:00", "19:00"), 0.10),
    ("c_fw", "Frost and Wave Service Point, Kukatpally", "Kukatpally", ["refrigerator", "washing_machine"], ["500085", "500049", "500019", "500072", "500084"], ("09:30", "18:30"), 0.12),
    ("c_cc", "Cool Craft Appliance Services, Madhapur", "Madhapur", ["air_conditioner", "refrigerator", "washing_machine"], ["500081", "500033", "500032", "500084", "500034", "500075", "500008"], ("08:30", "20:00"), 0.15),
    ("c_aq", "AquaCare RO and Geyser Services, Manikonda", "Manikonda", ["water_purifier", "water_heater"], ["500089", "500032", "500075", "500008"], ("09:00", "18:00"), 0.15),
    ("c_mh", "Metro Home Appliance Care, Miyapur", "Miyapur", ["air_conditioner", "refrigerator", "washing_machine", "water_purifier", "water_heater"], ["500049", "500085", "500019", "500084", "500072"], ("08:00", "20:30"), 0.15),
    ("c_ip", "InstallPro Mounting Services, Tolichowki", "Tolichowki", ["air_conditioner"], ["500008", "500033", "500034", "500032", "500089", "500075"], ("08:00", "19:00"), 0.12),
    ("c_ls", "Lakeshore Service Centre, Jubilee Hills", "Jubilee Hills", ["washing_machine", "refrigerator", "water_heater"], ["500033", "500034", "500008", "500016", "500081"], ("09:30", "19:00"), 0.12),
    ("c_hw", "Heatwell Authorised Service, Banjara Hills", "Banjara Hills", ["water_heater"], ["500034", "500033", "500016", "500008"], ("09:30", "18:00"), 0.10),
]
# centre -> [(brand, level, valid_from, valid_to)]
AUTH = {
    "c_av": [("aerovane", "authorised_service", dt.date(2024, 1, 1), None)],
    "c_zn": [("zenith", "authorised_service", dt.date(2024, 1, 1), None)],
    "c_fw": [("frostline", "authorised_service", dt.date(2024, 1, 1), None), ("wavecrest", "authorised_service", dt.date(2024, 6, 1), None)],
    "c_cc": [("aerovane", "independent", dt.date(2025, 9, 1), None), ("zenith", "independent", dt.date(2025, 9, 1), None),
             ("frostline", "independent", dt.date(2025, 9, 1), None), ("wavecrest", "independent", dt.date(2025, 9, 1), None)],
    "c_aq": [("purelo", "authorised_service", dt.date(2024, 3, 1), None), ("heatwell", "independent", dt.date(2025, 9, 1), dt.date(2026, 9, 1)),
             ("heatwell", "authorised_service", dt.date(2026, 9, 1), None)],
    "c_mh": [("aerovane", "independent", dt.date(2025, 9, 1), None), ("zenith", "independent", dt.date(2025, 9, 1), dt.date(2026, 10, 1)),
             ("frostline", "independent", dt.date(2025, 9, 1), None), ("wavecrest", "independent", dt.date(2025, 9, 1), None),
             ("purelo", "independent", dt.date(2025, 9, 1), None), ("heatwell", "independent", dt.date(2025, 9, 1), None)],
    "c_ip": [("aerovane", "installation_only", dt.date(2025, 9, 1), None), ("zenith", "installation_only", dt.date(2025, 9, 1), None)],
    "c_ls": [("wavecrest", "authorised_service", dt.date(2025, 2, 1), None), ("frostline", "independent", dt.date(2025, 9, 1), None),
             ("heatwell", "independent", dt.date(2025, 9, 1), None), ("zenith", "independent", dt.date(2025, 9, 1), None)],
    "c_hw": [("heatwell", "authorised_service", dt.date(2024, 1, 1), None)],
}
CENTRE_TECHS = {"c_av": 5, "c_zn": 5, "c_fw": 4, "c_cc": 4, "c_aq": 4, "c_mh": 5, "c_ip": 3, "c_ls": 4, "c_hw": 3}
CENTRE_SPEC = {  # specialisation categories of technicians in the centre
    "c_av": ["air_conditioner"], "c_zn": ["air_conditioner", "refrigerator", "washing_machine"],
    "c_fw": ["refrigerator", "washing_machine"], "c_cc": ["air_conditioner", "refrigerator", "washing_machine"],
    "c_aq": ["water_purifier", "water_heater"], "c_mh": ["air_conditioner", "refrigerator", "washing_machine", "water_purifier", "water_heater"],
    "c_ip": ["air_conditioner"], "c_ls": ["washing_machine", "refrigerator", "water_heater"], "c_hw": ["water_heater"],
}
PARTS_CENTRES = [  # key, name, locality, authorised brands, independent?
    ("p_ht", "Hitech Cooling Spares", "Madhapur", []),
    ("p_gb", "Gachibowli Appliance Parts Mart", "Gachibowli", []),
    ("p_kp", "KPHB Spares and Services", "Kukatpally", []),
    ("p_tl", "Tolichowki Parts Depot", "Tolichowki", []),
    ("p_bg", "Begumpet Electro Spares", "Begumpet", []),
    ("p_mn", "Manikonda Spares Corner", "Manikonda", []),
    ("p_av", "Aerovane Parts Depot, Gachibowli", "Gachibowli", ["aerovane"]),
    ("p_zn", "Zenith Parts Depot, Kondapur", "Kondapur", ["zenith"]),
]
FIRST = ["Ravi", "Suresh", "Venkat", "Srinivas", "Naresh", "Mahesh", "Ramesh", "Anil", "Kiran", "Prasad", "Sudhir", "Nagaraju", "Raju", "Harish",
         "Mohd Irfan", "Imran", "Salman", "Afsar", "Arjun", "Vikram", "Manoj", "Satish", "Rakesh", "Santosh", "Shiva", "Balaji", "Murali", "Karthik",
         "Sandeep", "Dinesh", "Ganesh", "Yadagiri", "Bhaskar", "Lokesh", "Pavan", "Rajesh", "Naveen", "Ashok", "Jagan", "Bharath"]
LAST = ["Reddy", "Goud", "Yadav", "Kumar", "Rao", "Naidu", "Shaik", "Khan", "Verma", "Chary", "Patel", "Mudiraj", "Prasad", "Singh", "Babu", "Raj"]
LANGS_BY = [("te", "hi", "en"), ("te", "en"), ("te", "hi", "ur"), ("hi", "en"), ("te", "ta", "en"), ("te", "hi")]

# -------------------------------------------------------------------------
def build_coverage_and_policy():
    """coverage_plan rows (kb doc ids resolved by key) and scoring_config."""
    W = WARRANTY
    for brand, w in W.items():
        add("coverage_plan", id=uid("plan", f"warranty-{brand}"), kind="brand_warranty", provider_name=brand.capitalize(),
            brand_id=uid("brand", brand), terms_doc_id=uid("kbdoc", "warranty_terms_brands"),
            covers={"comprehensive_months": w["comp"], "labour_months": w["labour"], "parts_only_months": w["parts_only"],
                    "consumables_covered": False, "exclusions": w["exclusions"]}, created_at=ist(2025, 8, 1, 10))
    add("coverage_plan", id=uid("plan", "ext-assurenest"), kind="extended_warranty", provider_name="AssureNest Extended Care",
        brand_id=None, terms_doc_id=uid("kbdoc", "ext_warranty_assurenest"),
        covers={"extension_months": 24, "labour": True, "parts": True, "excludes": ["consumables", "cosmetic damage", "pre-existing faults"],
                "claim_via": "plan provider helpline, claim number mandatory before visit", "visit_cap_per_year": 3}, created_at=ist(2025, 8, 1, 10))
    for key, prov, cats in (("amc-coolcraft", "Cool Craft AMC Gold", ["air_conditioner", "refrigerator"]),
                            ("amc-aquacare", "AquaCare RO Care Plan", ["water_purifier"]),
                            ("amc-metro", "Metro Home Care AMC", ["air_conditioner", "washing_machine", "water_heater"])):
        add("coverage_plan", id=uid("plan", key), kind="amc", provider_name=prov, brand_id=None,
            terms_doc_id=uid("kbdoc", "amc_" + key.split("-")[1]),
            covers={"categories": cats, "services_per_year": 2 if "aquacare" not in key else 3, "labour": True,
                    "parts": "consumables and minor parts excluded unless listed", "priority_visit_hours": 48}, created_at=ist(2025, 8, 1, 10))
    # starting weights from the design doc; the app reads these rows, so they can change without a migration
    add("scoring_config", id=uid("cfg", "assign-v1"), kind="assignment", name="assignment_v1",
        weights={"fix_confidence": 30, "parts_readiness": 25, "time_to_visit": 20, "route_cost": 15, "reliability": 5, "household_fit": 5},
        params={"price_scored": False, "scope": "technicians inside the receiving centre", "hypothesis": True}, valid_from=ist(2025, 9, 1, 0), created_by="keepwell-product")
    add("scoring_config", id=uid("cfg", "parts-v1"), kind="parts_ranking", name="parts_ranking_v1",
        weights={"ready_by": 35, "reliability": 25, "price": 20, "part_warranty": 20}, params={"anchor": "technician_route_anchor", "ladder": ["van", "centre", "parts_centre"], "hypothesis": True},
        valid_from=ist(2025, 9, 1, 0), created_by="keepwell-product")
    add("scoring_config", id=uid("cfg", "batch-v1"), kind="batching", name="batching_v1", weights={},
        params={"window_days": 3, "never_for": ["safety", "urgent"], "applies_at": "slot shaping", "hypothesis": True}, valid_from=ist(2025, 9, 1, 0), created_by="keepwell-product")
    add("scoring_config", id=uid("cfg", "urgency-v1"), kind="urgency", name="urgency_v1", weights={},
        params={"classes": ["safety", "urgent", "standard", "planned"], "fact_questions": 3, "household_asked_how_urgent": False,
                "urgent_capacity_holdback_slots": 1, "food_at_risk_hours": 12, "standard_first_visit_days": 3, "planned_first_visit_days": 14,
                "hypothesis": True, "sourced": False}, valid_from=ist(2025, 9, 1, 0), created_by="keepwell-product")

WARRANTY = {
    "aerovane": dict(comp=12, labour=12, parts_only={"compressor": 60, "indoor_pcb": 24},
                     exclusions=["consumables", "gas refill unless leak repaired under warranty", "damage from supply outside 170-270 V", "unauthorised repair"]),
    "zenith": dict(comp=24, labour=24, parts_only={"compressor": 120, "inverter_module": 36, "fridge_compressor": 120, "washer_motor": 60},
                   exclusions=["consumables", "damage from supply outside 170-270 V", "unauthorised repair", "installation not by authorised or Keepwell-approved installer"]),
    "frostline": dict(comp=12, labour=12, parts_only={"compressor": 120, "main_pcb": 24},
                      exclusions=["consumables", "door gasket after 12 months", "damage from supply outside 170-270 V", "unauthorised repair"]),
    "wavecrest": dict(comp=24, labour=24, parts_only={"motor": 60, "main_pcb": 36},
                      exclusions=["consumables", "hoses", "damage from foreign objects in drain", "unauthorised repair"]),
    "purelo": dict(comp=12, labour=12, parts_only={}, exclusions=["filters and membrane (consumables)", "damage from input water above 2000 TDS", "UV lamp after 6 months"]),
    "heatwell": dict(comp=24, labour=24, parts_only={"inner_tank": 60, "heating_element": 24},
                     exclusions=["scale damage in hard water areas", "unearthed installation", "anode rod (consumable)"]),
}

CENTRE_NUMBERS = {}
def build_supply():
    """Communities, service centres, technicians, parts centres, stock. Returns hidden-truth stock rows."""
    for key, *_ in CENTRES:
        CENTRE_NUMBERS[key] = (unique_phone(), unique_phone())     # (voice line, WhatsApp number): one of each per centre
    for name, loc, floors in COMMUNITIES:
        lon, lat = jitter(loc, 0.002)
        add("community", id=uid("community", name), name=name, pincode=LOC[loc][2], location=geo(lon, lat),
            contact_ref=f"committee-{name.lower().split()[0]}", created_at=ist(2025, 8, 20, 11))

    centre_loc = {}
    for key, name, loc, cats, pins, (h0, h1), comm in CENTRES:
        lon, lat = jitter(loc, 0.002)
        centre_loc[key] = (lon, lat)
        add("service_centre", id=uid("centre", key), name=name, address_line=f"{rng.randint(1, 9)}-{rng.randint(1, 99)}/{rng.randint(1, 40)}, Main Road, {loc}, Hyderabad",
            pincode=LOC[loc][2], location=geo(lon, lat), service_pincodes=pgarray(pins), categories=pgarray(cats),
            hours={"mon_sat": [h0, h1], "sun": "closed" if rng.random() < 0.6 else ["10:00", "14:00"]},
            default_language="te" if key in ("c_fw", "c_mh", "c_ls") else "hi" if key in ("c_ip",) else "en",
            onboarding_status="active", created_at=ist(2025, 8, 25, 10), updated_at=ist(2025, 8, 25, 10))
        add("centre_commercial", centre_id=uid("centre", key), commission_terms={"keepwell_fee_pct": int(comm * 100), "payout_cycle_days": 7}, payout_ref=f"acct_ref_{key}")
        add("centre_channel", id=uid("chan", f"{key}-voice"), centre_id=uid("centre", key), channel="voice", number_ref=CENTRE_NUMBERS[key][0], provider_ref=f"tel-{key}", status="active")
        add("centre_channel", id=uid("chan", f"{key}-wa"), centre_id=uid("centre", key), channel="whatsapp", number_ref=CENTRE_NUMBERS[key][1], provider_ref=f"wa-{key}", status="active")
        for ch, num in (("centre_voice", CENTRE_NUMBERS[key][0]), ("centre_whatsapp", CENTRE_NUMBERS[key][1])):
            add("external_ref", id=uid("xref", f"{key}-{ch}"), entity_type="centre", entity_id=uid("centre", key), ref_type="whatsapp_number" if "whatsapp" in ch else "phone",
                ref_norm=num.replace("+", "").replace(" ", ""), owner_type="centre", owner_id=uid("centre", key), verified=True, first_seen_at=ist(2025, 9, 1, 9))
        for brand, level, vf, vt in AUTH[key]:
            add("centre_brand_authorisation", id=uid("auth", f"{key}-{brand}-{level}-{vf}"), centre_id=uid("centre", key),
                brand_id=uid("brand", brand), level=level, valid_from=vf, valid_to=vt, evidence_ref=f"doc-{key}-{brand}")
        base = CENTRE_TECHS[key]
        for cat in cats:
            for jt in ("repair", "preventive_service", "coverage_claim", "installation"):
                if jt == "installation" and cat not in ("air_conditioner", "water_purifier", "washing_machine", "water_heater"):
                    continue
                if jt == "installation" and key not in ("c_ip", "c_zn", "c_av", "c_mh", "c_aq", "c_cc", "c_fw", "c_ls", "c_hw"):
                    continue
                slots = max(1, int(base * (0.7 if jt == "repair" else 0.35 if jt == "preventive_service" else 0.2 if jt == "coverage_claim" else 0.3)))
                if key == "c_ip" and jt != "installation":
                    continue
                add("centre_capacity", id=uid("cap", f"{key}-{cat}-{jt}"), centre_id=uid("centre", key), category_code=cat, job_type=jt, daily_slots=slots, urgent_holdback=(1 if (jt == "repair" and slots >= 3) else 0))

    # ---- technicians
    names_used = set()
    for key, name, loc, cats, pins, hours, comm in CENTRES:
        specs = CENTRE_SPEC[key]
        for i in range(CENTRE_TECHS[key]):
            while True:
                nm = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                if nm not in names_used:
                    names_used.add(nm); break
            tid = uid("tech", f"{key}-{i}")
            ph = unique_phone()
            exp_years = rng.choice([1, 2, 3, 4, 5, 7, 9, 12])
            base = 2 if exp_years < 3 else 3 if exp_years < 7 else 4
            if exp_years >= 9 and rng.random() < 0.6:
                base = 5
            primary = rng.choice(specs)
            home_loc = rng.choice(list(pins_to_loc(pins)))
            hlon, hlat = jitter(home_loc, 0.01)
            anchor_type = "home" if rng.random() < 0.6 else "centre"
            alon, alat = (hlon, hlat) if anchor_type == "home" else centre_loc[key]
            certs = []
            if any(c in ("air_conditioner", "refrigerator") for c in specs) and base >= 3:
                certs.append("gas")
            if key == "c_ip":
                certs += ["work_at_height", "gas"]
            if "water_heater" in specs and base >= 3:
                certs.append("electrical")
            toolkit = ["multimeter", "screwdriver_set", "clamp_meter"]
            if primary == "air_conditioner" or key == "c_ip":
                toolkit += ["vacuum_pump", "gas_gauge", "jet_pump", "flaring_tool", "pipe_cutter"]
            if primary == "refrigerator":
                toolkit += ["gas_gauge", "brazing_kit", "vacuum_pump"] if "gas" in certs else []
            if primary == "water_purifier":
                toolkit += ["tds_meter", "pressure_gauge", "filter_wrench"]
            if primary == "water_heater":
                toolkit += ["insulation_tester", "earth_tester"]
            shift = rng.choice([("09:00", "18:00"), ("09:00", "18:00"), ("08:30", "17:30"), ("10:00", "19:00")])
            active = not (rng.random() < 0.04)
            verified = not (rng.random() < 0.06)
            add("technician", id=tid, centre_id=uid("centre", key), name=nm, phone_enc=phone_enc(ph), phone_hash=phone_hash(ph),
                languages=pgarray(list(rng.choice(LANGS_BY))), shift_start=shift[0], shift_end=shift[1], route_anchor_type=anchor_type,
                route_anchor=geo(alon, alat), vehicle_type=rng.choice(["bike", "bike", "scooter", "scooter", "car"]),
                tool_kit=pgarray(sorted(set(toolkit))), identity_verified=verified, safety_certs=pgarray(sorted(set(certs))),
                active=active, created_at=ist(2025, 9, 2, 10), updated_at=ist(2025, 9, 2, 10))
            TECH_META[tid] = dict(centre=key, base=base, primary=primary, specs=specs, exp=exp_years, anchor=(alon, alat), shift=shift,
                                  certs=certs, active=active, verified=verified, phone=ph, name=nm, reliability=rng.uniform(0.72, 0.97))
            build_skills(tid, key, base, specs, primary)
    # ---- parts centres
    for key, name, loc, auth in PARTS_CENTRES:
        lon, lat = jitter(loc, 0.002)
        authorised = bool(auth)
        fill = rng.uniform(0.9, 0.97) if authorised else rng.uniform(0.7, 0.88)
        acc = rng.uniform(0.86, 0.95) if authorised else rng.uniform(0.55, 0.82)
        add("parts_centre", id=uid("pcentre", key), name=name, address_line=f"{rng.randint(1, 20)}-{rng.randint(1, 99)}, Spares Lane, {loc}, Hyderabad",
            pincode=LOC[loc][2], location=geo(lon, lat), hours={"mon_sat": ["09:30", "20:00"], "sun": "closed"},
            pickup_supported=True, delivery_supported=rng.random() < 0.4, fill_rate=round(fill, 4), stock_accuracy=round(acc, 4),
            active=True, created_at=ist(2025, 9, 3, 10), updated_at=ist(2025, 9, 3, 10))
        PCENTRE_META[key] = dict(authorised=auth, fill=fill, acc=acc)
        for b in ("aerovane", "zenith", "frostline", "wavecrest", "purelo", "heatwell"):
            add("parts_centre_brand", parts_centre_id=uid("pcentre", key), brand_id=uid("brand", b), is_authorised=(b in auth))
    return build_stock()

TECH_META, PCENTRE_META = {}, {}
PRICE_FACTOR = {}

def build_centre_prices():
    """Each centre's own price list: the platform benchmark scaled by a centre factor. Private to the centre."""
    import random as _r
    for key, name, loc, cats, pins, hours, comm in CENTRES:
        f = _r.Random(f'price-{key}').uniform(0.92, 1.18)
        PRICE_FACTOR[key] = f
        for r in TABLES['rate_card']:
            if r['category_code'] not in cats:
                continue
            add('centre_price', id=uid('cprice', f"{key}-{r['id']}"), centre_id=uid('centre', key), category_code=r['category_code'], job_type=r['job_type'],
                complexity_band=r['complexity_band'], visit_fee_paise=int(round(r['visit_fee_paise'] * f / 1000) * 1000), labour_paise=int(round(r['labour_paise'] * f / 1000) * 1000),
                valid_from=r['valid_from'], valid_to=r['valid_to'])

def pins_to_loc(pins):
    out = [l for l, (_, _, p) in LOC.items() if p in pins and l != "Shamshabad"]
    return out or ["Gachibowli"]

CLASS_BY_CAT = {
    "air_conditioner": ["cooling", "electrical", "drainage", "sensor", "mechanical", "compressor", "settings"],
    "refrigerator": ["cooling", "electrical", "mechanical", "door", "sensor", "compressor"],
    "washing_machine": ["drainage", "door", "water", "electrical", "mechanical"],
    "water_purifier": ["quality", "service", "electrical", "water"],
    "water_heater": ["heating", "leak", "service", "electrical", "safety"],
}
def build_skills(tid, ckey, base, specs, primary):
    auth_brands = [b for b, lvl, vf, vt in AUTH[ckey] if lvl == "authorised_service" and (vt is None)]
    for cat in specs:
        is_primary = cat == primary
        for cls in CLASS_BY_CAT[cat]:
            lvl = base + (1 if is_primary and rng.random() < 0.4 else 0) - (0 if is_primary else 1)
            if cls in ("compressor", "safety"):
                lvl -= 1
            if cls in ("settings", "service", "drainage", "door"):
                lvl += 1
            lvl = max(1, min(5, lvl + rng.choice([-1, 0, 0, 0, 1]) if rng.random() < 0.3 else lvl))
            brands = [None]
            if auth_brands:
                abr = [b for b in auth_brands if any(m[0] == b and m[1] == cat for m in MODELS)]
                if abr:
                    brands = abr
            for b in brands:
                add("technician_skill", id=uid("skill", f"{tid}-{b}-{cat}-{cls}"), technician_id=tid, centre_id=uid("centre", ckey),
                    brand_id=uid("brand", b) if b else None, category_code=cat, fault_class=cls,
                    level=max(1, min(5, lvl + (1 if b and rng.random() < 0.5 else 0))),
                    certified_on=dt.date(rng.choice([2021, 2022, 2023, 2024, 2025]), rng.randint(1, 12), rng.randint(1, 27)) if b else None,
                    certificate_ref=f"CERT-{rng.randint(10000, 99999)}" if b else None)
        if cat == "air_conditioner":
            lvl = base + (1 if ckey == "c_ip" else 0)
            add("technician_skill", id=uid("skill", f"{tid}-None-{cat}-install"), technician_id=tid, centre_id=uid("centre", ckey), brand_id=None, category_code=cat,
                fault_class="install", level=min(5, max(1, lvl)), certified_on=None, certificate_ref=None)

POPULAR = {"CAPF", "CAPC", "THERM", "R32", "FLARE", "DRAINH", "REMOTE", "PTC", "DSW", "SNSFR", "INV", "HOSE", "SED", "CARB", "MEMB", "SMPS", "SOL",
           "FLT", "FRES", "FIT", "LAMP", "CORD", "TCO", "THS", "FLG", "STEP", "DEFT", "MCAP", "BELT", "LIDSW", "THSDC"}
RARE = {"COMP_INV", "COMP_FIX", "COMPFR", "PCBO", "PCBFR", "PCBW_FL", "PCBW_TL", "BEAR", "DISP", "SUSP"}

def stock_noise(true_q, acc):
    """What the system believes, given a centre's stock accuracy."""
    if rng.random() < acc:
        return true_q
    return max(0, true_q + rng.choice([-3, -2, -1, 1, 2, 3, -true_q]))

def build_stock():
    truth = []
    parts = TABLES["part_catalogue"]
    bname = {b["id"]: b["name"].lower() for b in TABLES["brand"]}
    # parts centres
    for key, name, loc, auth in PARTS_CENTRES:
        meta = PCENTRE_META[key]
        for p in parts:
            brand = bname[p["brand_id"]]
            abbr = p["part_no"].split("-", 2)[2].split("-")[0]
            if auth:
                if brand not in auth:
                    continue
                prob = 0.92 if abbr not in RARE else 0.8
            else:
                prob = (0.75 if abbr in POPULAR else 0.4 if abbr not in RARE else 0.18)
                if brand == "generic":
                    prob = 0.85 if abbr in POPULAR else 0.5
                elif p["kind"] == "genuine":
                    prob *= 0.6
            if rng.random() > prob:
                continue
            tq = rng.randint(3, 14) if abbr in POPULAR else rng.randint(1, 4) if abbr not in RARE else rng.randint(0, 2)
            src = weighted(["feed", "scan", "call", "manual"], [3, 3, 2, 4] if auth else [0, 2, 3, 5])
            age_days = {"feed": rng.randint(0, 1), "scan": rng.randint(0, 7), "call": rng.randint(1, 20), "manual": rng.randint(3, 45)}[src]
            conf = {"feed": 0.9, "scan": 0.8, "call": 0.6, "manual": 0.45}[src] - min(0.25, age_days * 0.01)
            rec = stock_noise(tq, meta["acc"])
            sid = uid("stock", f"pc-{key}-{p['id']}")
            add("stock", id=sid, holder_type="parts_centre", holder_id=uid("pcentre", key), centre_id=None, part_id=p["id"], quantity=rec,
                as_of=SIM_NOW - dt.timedelta(days=age_days, hours=rng.randint(0, 20)), source=src, confidence=round(max(0.2, conf), 2))
            truth.append(dict(holder_type="parts_centre", holder_key=key, part_no=p["part_no"], recorded=rec, true_quantity=tq))
    # service centre inventories and technician vans
    for key, name, loc, cats, pins, hours, comm in CENTRES:
        for p in parts:
            abbr = p["part_no"].split("-", 2)[2].split("-")[0]
            fam_ok = any(PART_SPEC[abbr][0] and CAT_ABBR[c] == p["part_no"].split("-")[1] for c in cats)
            if not fam_ok or abbr in RARE or rng.random() > (0.55 if abbr in POPULAR else 0.12):
                continue
            tq = rng.randint(2, 10) if abbr in POPULAR else rng.randint(1, 2)
            rec = stock_noise(tq, 0.8)
            add("stock", id=uid("stock", f"c-{key}-{p['id']}"), holder_type="centre", holder_id=uid("centre", key), centre_id=uid("centre", key), part_id=p["id"],
                quantity=rec, as_of=SIM_NOW - dt.timedelta(days=rng.randint(0, 10)), source=rng.choice(["scan", "manual"]), confidence=round(rng.uniform(0.55, 0.85), 2))
            truth.append(dict(holder_type="centre", holder_key=key, part_no=p["part_no"], recorded=rec, true_quantity=tq))
    for tid, m in TECH_META.items():
        if not m["active"]:
            continue
        cat = m["primary"]
        for p in parts:
            abbr = p["part_no"].split("-", 2)[2].split("-")[0]
            if CAT_ABBR[cat] != p["part_no"].split("-")[1] or abbr not in POPULAR or p["kind"] != "aftermarket" and rng.random() < 0.5:
                continue
            if rng.random() > 0.55:
                continue
            tq = rng.randint(1, 4) if abbr != "R32" else rng.randint(8, 30)
            rec = stock_noise(tq, 0.7)
            add("stock", id=uid("stock", f"v-{tid}-{p['id']}"), holder_type="van", holder_id=tid, centre_id=uid("centre", m["centre"]), part_id=p["id"], quantity=rec,
                as_of=SIM_NOW - dt.timedelta(days=rng.randint(0, 6)), source="scan", confidence=round(rng.uniform(0.6, 0.85), 2))
            truth.append(dict(holder_type="van", holder_key=tid, part_no=p["part_no"], recorded=rec, true_quantity=tq))
    return truth

if __name__ == "__main__":
    build_catalogue(); build_rates(); build_coverage_and_policy()
    truth = build_supply()
    print({k: len(v) for k, v in TABLES.items()})
    import collections
    print(collections.Counter(s["holder_type"] for s in TABLES["stock"]))
