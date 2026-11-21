"""Reference data: fictional brands, categories, models, parts, fault library, error codes.
All brands are fictional so no real manufacturer's codes, terms or prices are copied or invented.
Prices are plausible Indian retail MRP ranges (rupees) for each part class."""
from common import *

BRANDS = [  # name, code, categories
    ("Aerovane", "AV", ["air_conditioner"]),
    ("Zenith", "ZN", ["air_conditioner", "refrigerator", "washing_machine"]),
    ("Frostline", "FL", ["refrigerator"]),
    ("Wavecrest", "WC", ["washing_machine"]),
    ("Purelo", "PL", ["water_purifier"]),
    ("Heatwell", "HW", ["water_heater"]),
    ("Generic", "GN", []),                      # aftermarket parts
]
BRAND_CODE = {n.lower(): c for n, c, _ in BRANDS}

CATEGORIES = {  # code: (name, service_interval_months, typical_life_years)
    "air_conditioner": ("Split air conditioner", 6, 10),
    "refrigerator": ("Refrigerator", 12, 12),
    "washing_machine": ("Washing machine", 12, 9),
    "water_purifier": ("RO water purifier", 4, 8),
    "water_heater": ("Water heater (geyser)", 12, 8),
}
CAT_ABBR = {"air_conditioner": "AC", "refrigerator": "FR", "washing_machine": "WM",
            "water_purifier": "RO", "water_heater": "GY"}

# brand, category, model_code, series, year, family, specs
MODELS = [
    ("aerovane", "air_conditioner", "AV-VX18I3", "Vortex", 2023, "AC_INV", {"tonnage": 1.5, "star": 3, "type": "inverter split", "refrigerant": "R32"}),
    ("aerovane", "air_conditioner", "AV-VX12I3", "Vortex", 2023, "AC_INV", {"tonnage": 1.0, "star": 3, "type": "inverter split", "refrigerant": "R32"}),
    ("aerovane", "air_conditioner", "AV-SK18I5", "Sky", 2025, "AC_INV", {"tonnage": 1.5, "star": 5, "type": "inverter split", "refrigerant": "R32"}),
    ("aerovane", "air_conditioner", "AV-FL12N3", "Flow", 2020, "AC_FIX", {"tonnage": 1.0, "star": 3, "type": "fixed-speed split", "refrigerant": "R32"}),
    ("zenith", "air_conditioner", "ZN-CS15I3", "CoolSense", 2022, "AC_INV", {"tonnage": 1.5, "star": 3, "type": "inverter split", "refrigerant": "R32"}),
    ("zenith", "air_conditioner", "ZN-CS20I3", "CoolSense", 2022, "AC_INV", {"tonnage": 2.0, "star": 3, "type": "inverter split", "refrigerant": "R32"}),
    ("zenith", "air_conditioner", "ZN-AX15I5", "Aura", 2025, "AC_INV", {"tonnage": 1.5, "star": 5, "type": "inverter split", "refrigerant": "R32"}),
    ("frostline", "refrigerator", "FL-D260", "Duo", 2022, "FR_FF", {"litres": 260, "doors": 2, "type": "frost-free", "refrigerant": "R600a"}),
    ("frostline", "refrigerator", "FL-D340", "Duo", 2024, "FR_FF", {"litres": 340, "doors": 2, "type": "frost-free", "refrigerant": "R600a"}),
    ("frostline", "refrigerator", "FL-S190", "Solo", 2019, "FR_DC", {"litres": 190, "doors": 1, "type": "direct-cool", "refrigerant": "R600a"}),
    ("zenith", "refrigerator", "ZN-F300I", "Frost Inverter", 2023, "FR_FF", {"litres": 300, "doors": 2, "type": "frost-free inverter", "refrigerant": "R600a"}),
    ("wavecrest", "washing_machine", "WC-TL70", "TopWash", 2021, "WM_TL", {"kg": 7.0, "type": "fully-automatic top load"}),
    ("wavecrest", "washing_machine", "WC-FL85", "FrontWash", 2023, "WM_FL", {"kg": 8.0, "type": "fully-automatic front load"}),
    ("wavecrest", "washing_machine", "WC-SA65", "TwinTub", 2019, "WM_SA", {"kg": 6.5, "type": "semi-automatic"}),
    ("zenith", "washing_machine", "ZN-W75T", "AquaFlow", 2024, "WM_TL", {"kg": 7.5, "type": "fully-automatic top load"}),
    ("purelo", "water_purifier", "PL-A7", "Aqua", 2022, "RO_UV", {"tank_l": 7, "stages": "RO+UV", "membrane_gpd": 75}),
    ("purelo", "water_purifier", "PL-A8", "Aqua Plus", 2024, "RO_UF", {"tank_l": 8, "stages": "RO+UV+UF", "membrane_gpd": 75}),
    ("purelo", "water_purifier", "PL-M9", "Mineral", 2025, "RO_MIN", {"tank_l": 9, "stages": "RO+Mineraliser", "membrane_gpd": 75}),
    ("heatwell", "water_heater", "HW-S15", "Store", 2021, "GY_ST", {"litres": 15, "type": "storage", "power_w": 2000}),
    ("heatwell", "water_heater", "HW-S25", "Store", 2022, "GY_ST", {"litres": 25, "type": "storage", "power_w": 2000}),
    ("heatwell", "water_heater", "HW-I3", "Instant", 2023, "GY_IN", {"litres": 3, "type": "instant", "power_w": 3000}),
]
FAM_CAT = {"AC_INV": "air_conditioner", "AC_FIX": "air_conditioner", "FR_FF": "refrigerator", "FR_DC": "refrigerator",
           "WM_TL": "washing_machine", "WM_FL": "washing_machine", "WM_SA": "washing_machine",
           "RO_UV": "water_purifier", "RO_UF": "water_purifier", "RO_MIN": "water_purifier",
           "GY_ST": "water_heater", "GY_IN": "water_heater"}
MODEL_BY_CODE = {m[2]: m for m in MODELS}

# abbr, name, families, (lo, hi) rupees, warranty_months, aftermarket_ok, consumable, per_unit
PARTS = [
    # --- air conditioner
    ("CAPF", "Outdoor fan motor capacitor 2.5 uF", ["AC_FIX"], (180, 320), 6, True, False),
    ("CAPC", "Compressor run capacitor 35 uF", ["AC_FIX"], (420, 650), 6, True, False),
    ("FANO_AC", "Outdoor fan motor (AC induction)", ["AC_FIX"], (2200, 3200), 12, True, False),
    ("FANO_DC", "Outdoor fan motor (DC)", ["AC_INV"], (2600, 3700), 12, False, False),
    ("FANI_AC", "Indoor blower motor (AC)", ["AC_FIX"], (1800, 2700), 12, True, False),
    ("FANI_DC", "Indoor blower motor (DC)", ["AC_INV"], (2300, 3400), 12, False, False),
    ("PCBI", "Indoor main PCB", ["AC_INV"], (3800, 6500), 12, False, False),
    ("PCBI_FIX", "Indoor main PCB (fixed-speed)", ["AC_FIX"], (1900, 3100), 12, True, False),
    ("PCBO", "Outdoor inverter module PCB", ["AC_INV"], (6500, 9800), 12, False, False),
    ("THERM", "Room and pipe thermistor set", ["AC_INV", "AC_FIX"], (180, 340), 6, True, False),
    ("STEP", "Louvre stepper motor", ["AC_INV", "AC_FIX"], (380, 700), 6, True, False),
    ("COMP_INV", "Inverter rotary compressor", ["AC_INV"], (8500, 17000), 12, False, False),
    ("COMP_FIX", "Fixed-speed rotary compressor", ["AC_FIX"], (6800, 8200), 12, False, False),
    ("R32", "Refrigerant R32 (per 100 g)", ["AC_INV", "AC_FIX"], (150, 220), 0, True, True),
    ("FLARE", "Flare nut and copper joint kit", ["AC_INV", "AC_FIX"], (180, 320), 3, True, False),
    ("REMOTE", "Remote controller", ["AC_INV", "AC_FIX"], (380, 720), 3, True, False),
    ("DISP", "Display and receiver board", ["AC_INV"], (850, 1400), 6, False, False),
    ("DRAINH", "Drain hose 1.5 m", ["AC_INV", "AC_FIX"], (120, 220), 0, True, True),
    # --- refrigerator
    ("DEFH", "Defrost heater", ["FR_FF"], (620, 980), 6, False, False),
    ("DEFT", "Defrost thermostat (bimetal)", ["FR_FF"], (240, 420), 6, True, False),
    ("EVAF", "Evaporator fan motor", ["FR_FF"], (880, 1500), 6, True, False),
    ("PTC", "PTC start relay and overload protector", ["FR_FF", "FR_DC"], (330, 560), 6, True, False),
    ("COMPFR", "Compressor R600a", ["FR_FF", "FR_DC"], (3800, 7000), 12, False, False),
    ("GASK", "Door gasket (fresh-food door)", ["FR_FF", "FR_DC"], (650, 1500), 3, False, False),
    ("PCBFR", "Main control PCB", ["FR_FF"], (2800, 4800), 12, False, False),
    ("SNSFR", "Temperature sensor", ["FR_FF"], (190, 330), 6, True, False),
    ("THSDC", "Mechanical thermostat", ["FR_DC"], (420, 650), 6, True, False),
    ("DSW", "Door switch", ["FR_FF", "FR_DC"], (110, 190), 3, True, False),
    # --- washing machine
    ("DPUMP", "Drain pump", ["WM_FL"], (950, 1900), 6, True, False),
    ("DMOT", "Drain motor and valve", ["WM_TL"], (800, 1500), 6, True, False),
    ("DLOCK", "Door lock assembly", ["WM_FL"], (950, 1600), 6, False, False),
    ("INV", "Water inlet valve", ["WM_TL", "WM_FL"], (520, 900), 6, True, False),
    ("PCBW_TL", "Main PCB (top load)", ["WM_TL"], (2800, 4900), 12, False, False),
    ("PCBW_FL", "Main PCB (front load)", ["WM_FL"], (4200, 7500), 12, False, False),
    ("CBRUSH", "Motor carbon brush set", ["WM_FL"], (240, 450), 3, True, False),
    ("MCAP", "Motor run capacitor", ["WM_SA"], (330, 600), 6, True, False),
    ("BEAR", "Drum bearing and seal kit", ["WM_TL", "WM_FL"], (1800, 3200), 6, False, False),
    ("HOSE", "Inlet and outlet hose set", ["WM_TL", "WM_FL", "WM_SA"], (330, 650), 3, True, False),
    ("LIDSW", "Lid switch", ["WM_TL"], (190, 350), 3, True, False),
    ("SUSP", "Suspension rod set", ["WM_TL", "WM_FL"], (1150, 1800), 6, False, False),
    ("BELT", "Drive belt", ["WM_TL", "WM_SA"], (330, 560), 3, True, False),
    ("PRESS", "Water level pressure switch", ["WM_TL", "WM_FL"], (380, 650), 6, True, False),
    # --- water purifier
    ("MEMB", "RO membrane 75 GPD", ["RO_UV", "RO_UF", "RO_MIN"], (780, 1650), 6, True, True),
    ("SED", "Sediment filter", ["RO_UV", "RO_UF", "RO_MIN"], (140, 300), 0, True, True),
    ("CARB", "Carbon block filter", ["RO_UV", "RO_UF", "RO_MIN"], (240, 460), 0, True, True),
    ("UVL", "UV lamp and ballast", ["RO_UV", "RO_UF"], (540, 920), 6, True, False),
    ("SMPS", "SMPS adapter 24 V", ["RO_UV", "RO_UF", "RO_MIN"], (430, 760), 6, True, False),
    ("BPUMP", "Booster pump 24 V", ["RO_UV", "RO_UF", "RO_MIN"], (1050, 1850), 6, True, False),
    ("SOL", "Solenoid valve", ["RO_UV", "RO_UF", "RO_MIN"], (300, 560), 6, True, False),
    ("FLT", "Float switch", ["RO_UV", "RO_UF", "RO_MIN"], (140, 270), 3, True, False),
    ("FRES", "Flow restrictor", ["RO_UV", "RO_UF", "RO_MIN"], (70, 150), 0, True, True),
    ("FIT", "Tubing and fitting set", ["RO_UV", "RO_UF", "RO_MIN"], (120, 320), 0, True, True),
    ("UFM", "UF membrane", ["RO_UF"], (880, 1500), 6, False, True),
    ("MINC", "Mineraliser cartridge", ["RO_MIN"], (440, 720), 0, False, True),
    # --- water heater
    ("HEL_ST", "Heating element 2000 W", ["GY_ST"], (640, 1200), 12, True, False),
    ("HEL_IN", "Heating element 3000 W (instant)", ["GY_IN"], (520, 900), 12, True, False),
    ("THS", "Thermostat", ["GY_ST", "GY_IN"], (340, 660), 12, True, False),
    ("TCO", "Thermal cut-out", ["GY_ST", "GY_IN"], (170, 300), 12, True, False),
    ("ANODE", "Magnesium anode rod", ["GY_ST"], (340, 560), 6, True, True),
    ("PRV", "Pressure relief and non-return valve", ["GY_ST"], (300, 560), 6, True, False),
    ("CORD", "Power cord with earth pin", ["GY_ST", "GY_IN"], (240, 410), 3, True, False),
    ("LAMP", "Indicator lamp", ["GY_ST", "GY_IN"], (50, 90), 0, True, False),
    ("FLG", "Flange gasket", ["GY_ST"], (230, 400), 0, True, True),
]
PART_SPEC = {p[0]: p for p in PARTS}
PER_TONNAGE = {"COMP_INV"}               # compressor part per tonnage
PER_MODEL = {"GASK"}                     # fits exact model only
PCB_REVISED = {"PCBI"}                   # revision A / B

def build_catalogue():
    """Fills brand, appliance_category, category_norm, appliance_model, part_catalogue, part_compatibility."""
    for name, code, _ in BRANDS:
        add("brand", id=uid("brand", name.lower()), name=name, forwarding_enabled=(name.lower() in ("aerovane", "zenith", "wavecrest", "heatwell")), created_at=ist(2025, 8, 1, 10, 0))
    for code, (name, interval, life) in CATEGORIES.items():
        add("appliance_category", code=code, name=name)
        add("category_norm", id=uid("norm", code), category_code=code, service_interval_months=interval,
            typical_life_years=life, valid_from=dt.date(2025, 9, 1), valid_to=None)
    for brand, cat, code, series, year, fam, specs in MODELS:
        add("appliance_model", id=uid("model", code), brand_id=uid("brand", brand), category_code=cat,
            model_code=code, series=series, year_from=year, specs={**specs, "family": fam},
            created_at=ist(2025, 8, 1, 10, 0))
    rr = random.Random(SEED + 7)
    price_cache = {}
    def price(abbr, brand, tag=""):
        k = (abbr, brand, tag)
        if k not in price_cache:
            lo, hi = PART_SPEC[abbr][3]
            price_cache[k] = int(round(rr.uniform(lo, hi) / 5) * 5)
        return price_cache[k]
    def sub_group(abbr, fam_key):
        return f"SG-{abbr}-{fam_key}"

    seen = set()
    for abbr, pname, fams, (lo, hi), wmonths, aft_ok, consumable in PARTS:
        brands_by_fam = {}
        for brand, cat, code, series, year, fam, specs in MODELS:
            if fam in fams:
                brands_by_fam.setdefault(brand, []).append(MODEL_BY_CODE[code])
        for brand, models in brands_by_fam.items():
            bc = BRAND_CODE[brand]
            catabbr = CAT_ABBR[FAM_CAT[models[0][5]]]
            if abbr in PER_TONNAGE:
                groups = {}
                for m in models:
                    groups.setdefault(m[6]["tonnage"], []).append(m)
                for ton, ms in groups.items():
                    pno = f"{bc}-{catabbr}-{abbr}-{str(ton).replace('.', '')}T"
                    base = {1.0: 8500, 1.5: 10800, 2.0: 14200}[ton]
                    _emit_part(pno, f"{pname} {ton} T", brand, "genuine", int(round(base * rr.uniform(0.95, 1.12) / 5) * 5),
                               wmonths, sub_group(abbr, f"{ton}"), ms, "", seen)
            elif abbr in PER_MODEL:
                for m in models:
                    pno = f"{bc}-{catabbr}-{abbr}-{m[2].split('-')[1]}"
                    _emit_part(pno, f"{pname} for {m[2]}", brand, "genuine", price(abbr, brand, m[2]), wmonths,
                               sub_group(abbr, m[2]), [m], "", seen)
            elif abbr in PCB_REVISED:
                for rev in ("A", "B"):
                    pno = f"{bc}-{catabbr}-{abbr}-{rev}"
                    ms = models if rev == "A" else models
                    if rev == "A":
                        ms = [m for m in models if m[4] < 2025]
                    # revision B supersedes A: fits all, including older Vortex units
                    if not ms:
                        continue
                    _emit_part(pno, f"{pname} rev {rev}", brand, "genuine", price(abbr, brand, rev), wmonths,
                               sub_group(abbr, "all"), ms, rev, seen)
            else:
                pno = f"{bc}-{catabbr}-{abbr}"
                _emit_part(pno, pname, brand, "genuine", price(abbr, brand), wmonths,
                           sub_group(abbr, "all"), models, "", seen)
        if aft_ok:
            allm = [MODEL_BY_CODE[m[2]] for m in MODELS if m[5] in fams]
            catabbr = CAT_ABBR[FAM_CAT[fams[0]]]
            gp = round(price(abbr, "genuine-ref") * rr.uniform(0.42, 0.62) / 5) * 5
            _emit_part(f"GN-{catabbr}-{abbr}", f"{pname} (aftermarket)", "generic", "aftermarket", int(gp),
                       min(wmonths, 3), sub_group(abbr, "all"), allm, "", seen)

def _emit_part(pno, name, brand, kind, mrp, wmonths, sgroup, models, rev, seen):
    pid = uid("part", pno)
    if pid in seen:
        return
    seen.add(pid)
    add("part_catalogue", id=pid, brand_id=uid("brand", brand), part_no=pno, name=name, kind=kind,
        substitution_group=sgroup, mrp_paise=int(mrp) * 100, warranty_months=wmonths)
    for m in models:
        add("part_compatibility", part_id=pid, model_id=uid("model", m[2]), revision=rev or "")

def part_ids_for(abbr, model_code, prefer="genuine"):
    """Return part ids (genuine first) that fit a model for a part class."""
    cands = []
    for pc in TABLES["part_compatibility"]:
        if pc["model_id"] == uid("model", model_code):
            cands.append(pc["part_id"])
    out = []
    for p in TABLES["part_catalogue"]:
        if p["id"] in cands and f"-{abbr}" in p["part_no"] and (p["part_no"].split("-", 2)[2] == abbr or p["part_no"].split("-", 2)[2].startswith(abbr + "-")):
            out.append(p)
    out.sort(key=lambda p: (p["kind"] != prefer, p["part_no"]))
    return out

# -------------------------------------------------------------------------
# Error codes (fictional, brand specific; E5 means different things on purpose)
# -------------------------------------------------------------------------
ERROR_CODES = {
    ("aerovane", "air_conditioner"): [
        ("E1", "Room temperature sensor open or short", "Check sensor connector CN4; replace thermistor set"),
        ("E2", "Pipe temperature sensor open or short", "Check sensor connector CN5; replace thermistor set"),
        ("E3", "Indoor fan motor feedback lost", "Check motor connector; replace indoor blower motor"),
        ("E4", "Indoor to outdoor communication error", "Check interconnect wiring and terminal tightness; then outdoor board"),
        ("E5", "Compressor over-current or overload protection", "Check supply voltage, outdoor fan, condenser coil; then compressor"),
        ("E6", "Refrigerant pressure low protection", "Check for leak; recover, repair, evacuate and recharge to nameplate"),
        ("E7", "Outdoor fan motor fault", "Check fan blade and motor; replace outdoor motor"),
        ("H1", "Anti-ice (evaporator freeze) protection active", "Clean filters and coil; check airflow and charge"),
    ],
    ("zenith", "air_conditioner"): [
        ("F0", "Refrigerant shortage protection", "Check for leak; recharge to nameplate after repair"),
        ("F1", "Indoor room sensor fault", "Check connector; replace thermistor set"),
        ("F2", "Indoor coil sensor fault", "Check connector; replace thermistor set"),
        ("F3", "Outdoor ambient sensor fault", "Check connector; replace outdoor sensor"),
        ("F4", "Outdoor coil sensor fault", "Check connector; replace outdoor sensor"),
        ("F5", "Compressor drive over-current", "Check supply, outdoor fan and coil; then outdoor module"),
        ("E5", "Indoor to outdoor communication loss", "Check interconnect wiring; then indoor and outdoor boards"),
        ("E8", "Indoor fan stalled", "Check blower wheel for obstruction; replace indoor motor"),
        ("P1", "Drain water level protection", "Clear drain line; check drain pump if fitted"),
    ],
    ("frostline", "refrigerator"): [
        ("Er2", "Freezer sensor fault", "Check sensor connector; replace temperature sensor"),
        ("Er3", "Fridge compartment sensor fault", "Check sensor connector; replace temperature sensor"),
        ("Er4", "Defrost sensor fault or defrost failure", "Check defrost heater, bimetal thermostat and sensor"),
        ("Er5", "Compressor start failure", "Check PTC relay, overload protector, then compressor"),
        ("Er6", "Evaporator fan fault", "Check fan for ice or obstruction; replace fan motor"),
        ("Er7", "Main board to display communication error", "Check harness; replace main PCB"),
    ],
    ("zenith", "refrigerator"): [
        ("dF", "Defrost failure", "Check defrost heater and thermostat"),
        ("FS", "Freezer sensor fault", "Check sensor connector; replace sensor"),
        ("RS", "Fridge sensor fault", "Check sensor connector; replace sensor"),
        ("CE", "Compressor control error", "Check inverter drive board then compressor"),
    ],
    ("wavecrest", "washing_machine"): [
        ("E11", "Water inlet fault (no fill in 10 minutes)", "Check tap, inlet filter and inlet valve"),
        ("E21", "Drain failure (water not drained in 10 minutes)", "Clear drain filter and hose; check drain pump or motor"),
        ("E30", "Door lock fault (front load)", "Check door closure and lock assembly"),
        ("E41", "Motor feedback fault", "Check motor connector, carbon brushes; then PCB"),
        ("E60", "Water level sensor fault", "Check pressure switch tube and switch"),
        ("UE", "Unbalanced load", "Redistribute load; check levelling and suspension"),
    ],
    ("zenith", "washing_machine"): [
        ("nF", "No fill", "Check tap, inlet filter and valve"),
        ("nd", "No drain", "Clear drain filter and hose; check drain motor"),
        ("dE", "Lid or door switch fault", "Check lid switch and closure"),
        ("Ub", "Unbalance", "Redistribute load; check levelling and suspension"),
        ("E4", "Motor fault", "Check motor connector; then PCB"),
    ],
}

# -------------------------------------------------------------------------
# Fault library: drives past job history and realism of experience cases.
# parts: (abbr, probability, (qty lo, qty hi)).  dur = minutes on site (p50, spread)
# -------------------------------------------------------------------------
SEASON = {  # month 1..12 weights
    "ac":    [3, 4, 8, 14, 16, 12, 6, 5, 6, 6, 3, 3],
    "fridge": [4, 5, 8, 12, 14, 10, 6, 5, 5, 5, 4, 4],
    "flat":  [6, 6, 7, 7, 7, 7, 8, 8, 8, 8, 7, 7],
    "geyser": [14, 12, 6, 3, 2, 2, 3, 3, 4, 8, 12, 14],
}
FAULTS = [
    # ---- air conditioner
    dict(key="ac_lowgas", cat="air_conditioner", name="Low refrigerant (leak)", fams=["AC_INV", "AC_FIX"], w=22, cls="cooling", lvl=3, gas=True,
         dur=(100, 30), parts=[("R32", 0.97, (2, 5)), ("FLARE", 0.45, (1, 1))], band="standard", season="ac",
         codes={"aerovane": ["E6", "H1"], "zenith": ["F0"]},
         sym=["Cooling weak, ice on indoor pipe, outdoor pipe not cold", "Not cooling properly since last week, gas pressure low on gauge",
              "Cooling drops after 20 min, frost on valve, {code} shown"],
         cause=["Leak at indoor flare joint, repaired and recharged", "Micro leak at outdoor service valve cap, replaced cap and recharged",
                "Low charge after previous reinstallation, joint re-flared"]),
    dict(key="ac_cap", cat="air_conditioner", name="Capacitor failure", fams=["AC_FIX"], w=18, cls="electrical", lvl=2, gas=False,
         dur=(45, 15), parts=[("CAPF", 0.55, (1, 1)), ("CAPC", 0.45, (1, 1))], band="basic", season="ac", codes={},
         sym=["Outdoor fan not rotating, compressor humming then trips", "AC starts but no cooling, outdoor unit buzzing", "Outdoor fan needs push to start"],
         cause=["Fan capacitor weak, replaced", "Compressor run capacitor bulged, replaced"]),
    dict(key="ac_drain", cat="air_conditioner", name="Drain line choked / water leak", fams=["AC_INV", "AC_FIX"], w=16, cls="drainage", lvl=1, gas=False,
         dur=(45, 15), parts=[("DRAINH", 0.2, (1, 1))], band="basic", season="ac", codes={"zenith": ["P1"]},
         sym=["Water dripping from indoor unit onto floor", "Water leaking from AC on the wall, wall is wet", "Water drops from front panel when fan runs, {code} shown"],
         cause=["Drain line choked with algae, cleared with nitrogen and jet", "Drain hose sagging causing back-flow, re-sloped", "Drain tray clogged, cleaned"]),
    dict(key="ac_dirty", cat="air_conditioner", name="Dirty filters and coils (service due)", fams=["AC_INV", "AC_FIX"], w=13, cls="cooling", lvl=1, gas=False,
         dur=(70, 20), parts=[], band="basic", season="ac", codes={"aerovane": ["H1"]},
         sym=["Cooling poor and bad smell, not serviced for over a year", "Airflow weak, filters clogged, power bill high", "Smell from AC when started"],
         cause=["Indoor coil and filters heavily clogged, jet service done", "Outdoor condenser blocked with dust, cleaned"]),
    dict(key="ac_pcb", cat="air_conditioner", name="Indoor main PCB fault", fams=["AC_INV", "AC_FIX"], w=7, cls="electrical", lvl=3, gas=False,
         dur=(90, 25), parts=[("PCBI", 0.8, (1, 1)), ("PCBI_FIX", 0.8, (1, 1))], band="complex", season="flat",
         codes={"aerovane": ["E4"], "zenith": ["E5"]},
         sym=["AC switches off by itself, remote not responding, {code} displayed", "Display blank, no response to remote", "Random restarts, relay clicking"],
         cause=["Relay burnt on indoor board, board replaced", "Surge damage to main board, replaced"]),
    dict(key="ac_odu_pcb", cat="air_conditioner", name="Outdoor inverter module fault", fams=["AC_INV"], w=6, cls="electrical", lvl=4, gas=False,
         dur=(120, 30), parts=[("PCBO", 0.9, (1, 1))], band="complex", season="ac",
         codes={"aerovane": ["E5"], "zenith": ["F5"]},
         sym=["Compressor not starting, outdoor fan runs, {code} after 2 minutes", "Cooling stops after few minutes, {code} flashing"],
         cause=["IPM module failed, outdoor board replaced after supply surge", "Outdoor board burnt near compressor terminal, replaced"]),
    dict(key="ac_therm", cat="air_conditioner", name="Temperature sensor fault", fams=["AC_INV", "AC_FIX"], w=7, cls="sensor", lvl=2, gas=False,
         dur=(40, 10), parts=[("THERM", 0.9, (1, 1))], band="basic", season="flat", codes={"aerovane": ["E1", "E2"], "zenith": ["F1", "F2"]},
         sym=["Error code {code} on display, AC not starting", "AC cools too much then stops, {code} flashing"],
         cause=["Pipe sensor reading open, replaced thermistor set", "Room sensor connector loose and corroded, replaced set"]),
    dict(key="ac_fan_in", cat="air_conditioner", name="Indoor blower motor fault", fams=["AC_INV", "AC_FIX"], w=5, cls="mechanical", lvl=2, gas=False,
         dur=(70, 20), parts=[("FANI_DC", 0.85, (1, 1)), ("FANI_AC", 0.85, (1, 1))], band="standard", season="ac", codes={"aerovane": ["E3"], "zenith": ["E8"]},
         sym=["Indoor fan making loud noise then stops, {code}", "Air not blowing from indoor unit"],
         cause=["Blower motor bearing seized, replaced", "Motor winding open, replaced"]),
    dict(key="ac_fan_out", cat="air_conditioner", name="Outdoor fan motor fault", fams=["AC_INV", "AC_FIX"], w=4, cls="mechanical", lvl=2, gas=False,
         dur=(70, 20), parts=[("FANO_DC", 0.85, (1, 1)), ("FANO_AC", 0.85, (1, 1))], band="standard", season="ac", codes={"aerovane": ["E7", "E5"]},
         sym=["Outdoor fan not rotating, AC stops after 10 min, {code}", "Outdoor unit noisy and hot"],
         cause=["Outdoor fan motor seized, replaced", "Fan blade loose on shaft, motor replaced"]),
    dict(key="ac_comp", cat="air_conditioner", name="Compressor failure", fams=["AC_INV", "AC_FIX"], w=4, cls="compressor", lvl=4, gas=True,
         dur=(210, 50), parts=[("COMP_INV", 0.9, (1, 1)), ("COMP_FIX", 0.9, (1, 1)), ("R32", 0.95, (4, 8))], band="complex", season="ac",
         codes={"aerovane": ["E5"], "zenith": ["F5"]},
         sym=["No cooling at all, outdoor unit hot, compressor trips, {code} persistent", "Outdoor unit makes loud noise then no cooling"],
         cause=["Compressor seized after long low-gas operation, replaced", "Compressor winding short, replaced and recharged"]),
    dict(key="ac_remote", cat="air_conditioner", name="Remote / settings issue", fams=["AC_INV", "AC_FIX"], w=5, cls="settings", lvl=1, gas=False,
         dur=(25, 10), parts=[("REMOTE", 0.25, (1, 1))], band="basic", season="flat", codes={},
         sym=["Remote not working, AC not responding to commands", "AC stuck on one mode, cannot change temperature"],
         cause=["Remote batteries and IR window issue, remote replaced", "Settings reset, receiver cleaned"]),
    dict(key="ac_volt", cat="air_conditioner", name="Supply / MCB trip", fams=["AC_INV", "AC_FIX"], w=3, cls="electrical", lvl=2, gas=False,
         dur=(50, 20), parts=[], band="standard", season="ac", codes={"aerovane": ["E5"], "zenith": ["F5"]},
         sym=["MCB trips when AC starts", "AC works for few minutes then power trips"],
         cause=["Undersized MCB and loose terminal, corrected by electrician advice", "Loose neutral at outdoor isolator"]),
    # ---- refrigerator
    dict(key="fr_defrost", cat="refrigerator", name="Defrost system failure (frost build-up)", fams=["FR_FF"], w=26, cls="cooling", lvl=3, gas=False,
         dur=(80, 25), parts=[("DEFH", 0.7, (1, 1)), ("DEFT", 0.7, (1, 1)), ("SNSFR", 0.2, (1, 1))], band="standard", season="fridge",
         codes={"frostline": ["Er4"], "zenith": ["dF"]},
         sym=["Freezer full of ice, fridge section not cooling", "Ice on back wall of freezer, fridge warm", "Frost build-up, {code} on display"],
         cause=["Defrost heater open, replaced with thermostat", "Defrost bimetal stuck, replaced"]),
    dict(key="fr_ptc", cat="refrigerator", name="Compressor start relay failure", fams=["FR_FF", "FR_DC"], w=18, cls="electrical", lvl=2, gas=False,
         dur=(45, 15), parts=[("PTC", 0.85, (1, 1))], band="basic", season="fridge", codes={"frostline": ["Er5"]},
         sym=["Fridge not cooling, compressor clicks and stops", "Compressor not starting, clicking sound, {code}"],
         cause=["PTC relay burnt, replaced with overload", "Overload protector tripping, replaced"]),
    dict(key="fr_fan", cat="refrigerator", name="Evaporator fan fault", fams=["FR_FF"], w=14, cls="mechanical", lvl=2, gas=False,
         dur=(65, 20), parts=[("EVAF", 0.85, (1, 1))], band="standard", season="fridge", codes={"frostline": ["Er6"]},
         sym=["Noise from freezer and fridge section warm", "Freezer cold but fridge not cooling, fan not running", "Loud buzzing from back of freezer"],
         cause=["Evaporator fan motor seized by ice, replaced", "Fan blade touching ice, defrosted and motor replaced"]),
    dict(key="fr_gasket", cat="refrigerator", name="Door gasket worn", fams=["FR_FF", "FR_DC"], w=10, cls="door", lvl=1, gas=False,
         dur=(45, 10), parts=[("GASK", 0.9, (1, 1))], band="basic", season="flat", codes={},
         sym=["Door not sealing, water on floor, compressor runs all day", "Gasket torn near hinge, ice around door"],
         cause=["Gasket torn, replaced", "Gasket hardened, replaced"]),
    dict(key="fr_pcb", cat="refrigerator", name="Main PCB fault", fams=["FR_FF"], w=9, cls="electrical", lvl=3, gas=False,
         dur=(70, 20), parts=[("PCBFR", 0.85, (1, 1))], band="complex", season="flat", codes={"frostline": ["Er7"]},
         sym=["Display blank, fridge not cooling, {code}", "Cooling erratic, display shows random codes"],
         cause=["Voltage spike damaged main board, replaced", "Moisture damage on main board, replaced"]),
    dict(key="fr_sensor", cat="refrigerator", name="Temperature sensor fault", fams=["FR_FF"], w=8, cls="sensor", lvl=2, gas=False,
         dur=(40, 10), parts=[("SNSFR", 0.9, (1, 1))], band="basic", season="flat", codes={"frostline": ["Er2", "Er3"], "zenith": ["FS", "RS"]},
         sym=["Over-cooling and then stops, {code} on display", "Fridge temperature not controllable, {code}"],
         cause=["Sensor reading out of range, replaced", "Sensor wire damaged, replaced"]),
    dict(key="fr_comp", cat="refrigerator", name="Compressor failure / gas leak", fams=["FR_FF", "FR_DC"], w=5, cls="compressor", lvl=4, gas=True,
         dur=(200, 45), parts=[("COMPFR", 0.9, (1, 1))], band="complex", season="fridge", codes={"zenith": ["CE"]},
         sym=["No cooling at all, compressor running but body not cold", "Compressor hot, trips after few minutes"],
         cause=["Compressor valve failure, replaced with new drier", "Leak at evaporator, uneconomic to repair"]),
    dict(key="fr_thermdc", cat="refrigerator", name="Thermostat fault (direct-cool)", fams=["FR_DC"], w=10, cls="cooling", lvl=1, gas=False,
         dur=(40, 10), parts=[("THSDC", 0.9, (1, 1))], band="basic", season="fridge", codes={},
         sym=["Fridge over-cooling and freezing vegetables", "Fridge not cooling, thermostat knob has no click"],
         cause=["Thermostat stuck, replaced"]),
    # ---- washing machine
    dict(key="wm_drain", cat="washing_machine", name="Drain pump or motor fault", fams=["WM_FL", "WM_TL"], w=26, cls="drainage", lvl=2, gas=False,
         dur=(60, 20), parts=[("DPUMP", 0.55, (1, 1)), ("DMOT", 0.55, (1, 1))], band="standard", season="flat",
         codes={"wavecrest": ["E21"], "zenith": ["nd"]},
         sym=["Water not draining, machine stops with {code}", "Clothes soaked, drum has water after wash, {code}", "Drain noise then stops"],
         cause=["Drain filter choked with coins and lint, cleared", "Drain pump impeller broken, replaced", "Drain motor jammed, replaced"]),
    dict(key="wm_lock", cat="washing_machine", name="Door lock fault", fams=["WM_FL"], w=14, cls="door", lvl=2, gas=False,
         dur=(50, 15), parts=[("DLOCK", 0.8, (1, 1))], band="standard", season="flat", codes={"wavecrest": ["E30"]},
         sym=["Door does not lock, {code}, cycle will not start", "Door stays locked after wash"],
         cause=["Door lock bimetal failed, replaced", "Door catch misaligned and lock worn, replaced"]),
    dict(key="wm_inlet", cat="washing_machine", name="Inlet valve fault", fams=["WM_FL", "WM_TL"], w=12, cls="water", lvl=2, gas=False,
         dur=(45, 15), parts=[("INV", 0.65, (1, 1))], band="basic", season="flat", codes={"wavecrest": ["E11"], "zenith": ["nF"]},
         sym=["No water entering machine, {code}", "Machine fills very slowly, {code}"],
         cause=["Inlet filter choked with sediment, cleaned", "Inlet valve coil open, replaced"]),
    dict(key="wm_pcb", cat="washing_machine", name="Main PCB fault", fams=["WM_FL", "WM_TL"], w=9, cls="electrical", lvl=3, gas=False,
         dur=(70, 20), parts=[("PCBW_FL", 0.5, (1, 1)), ("PCBW_TL", 0.5, (1, 1))], band="complex", season="flat", codes={"wavecrest": ["E41"], "zenith": ["E4"]},
         sym=["Machine dead, no power light", "Cycle stops midway, panel unresponsive, {code}"],
         cause=["Burnt track on main board, replaced", "Moisture ingress on PCB, replaced"]),
    dict(key="wm_bearing", cat="washing_machine", name="Drum bearing wear", fams=["WM_FL", "WM_TL"], w=8, cls="mechanical", lvl=4, gas=False,
         dur=(210, 45), parts=[("BEAR", 0.9, (1, 1))], band="complex", season="flat", codes={},
         sym=["Loud grinding noise in spin, drum shaky", "Rumbling noise during spin, drum has play"],
         cause=["Drum bearing and seal worn, replaced"]),
    dict(key="wm_unbal", cat="washing_machine", name="Unbalance / levelling / suspension", fams=["WM_FL", "WM_TL"], w=9, cls="mechanical", lvl=1, gas=False,
         dur=(35, 10), parts=[("SUSP", 0.2, (1, 1))], band="basic", season="flat", codes={"wavecrest": ["UE"], "zenith": ["Ub"]},
         sym=["Machine shakes and walks during spin, {code}", "Stops in spin with {code} repeatedly"],
         cause=["Machine not levelled, feet adjusted", "Suspension rods worn, replaced"]),
    dict(key="wm_motor_sa", cat="washing_machine", name="Motor capacitor / belt (semi-automatic)", fams=["WM_SA"], w=22, cls="electrical", lvl=1, gas=False,
         dur=(45, 15), parts=[("MCAP", 0.6, (1, 1)), ("BELT", 0.4, (1, 1))], band="basic", season="flat", codes={},
         sym=["Wash motor humming, not rotating", "Spin tub slow, smell of burning rubber"],
         cause=["Run capacitor weak, replaced", "Belt slipped and worn, replaced"]),
    dict(key="wm_lid", cat="washing_machine", name="Lid switch fault", fams=["WM_TL"], w=7, cls="door", lvl=2, gas=False,
         dur=(40, 10), parts=[("LIDSW", 0.85, (1, 1))], band="basic", season="flat", codes={"zenith": ["dE"]},
         sym=["Lid is closed but machine beeps and will not start", "Machine does not start, lid sensor not detecting, {code}"],
         cause=["Lid switch not registering closure, replaced", "Lid hinge actuator broken, switch replaced"]),
    dict(key="wm_leak", cat="washing_machine", name="Hose / door seal water leak", fams=["WM_FL", "WM_TL", "WM_SA"], w=8, cls="water", lvl=1, gas=False,
         dur=(40, 10), parts=[("HOSE", 0.55, (1, 1))], band="basic", season="flat", codes={},
         sym=["Water leaking from bottom during wash", "Floor wet near machine after cycle"],
         cause=["Outlet hose clamp loose, tightened", "Hose cracked, replaced"]),
    # ---- water purifier
    dict(key="ro_membrane", cat="water_purifier", name="RO membrane choked (high TDS)", fams=["RO_UV", "RO_UF", "RO_MIN"], w=24, cls="quality", lvl=2, gas=False,
         dur=(50, 15), parts=[("MEMB", 0.9, (1, 1)), ("SED", 0.7, (1, 1)), ("CARB", 0.7, (1, 1))], band="basic", season="flat", codes={},
         sym=["Water tastes salty, TDS reading high", "Water output very slow and tastes bad", "Red service light on, water taste changed"],
         cause=["Membrane scaled, replaced with filters", "Output TDS 480 against input 520, membrane replaced"]),
    dict(key="ro_service", cat="water_purifier", name="Filter service due", fams=["RO_UV", "RO_UF", "RO_MIN"], w=22, cls="service", lvl=1, gas=False,
         dur=(45, 10), parts=[("SED", 0.95, (1, 1)), ("CARB", 0.95, (1, 1)), ("UVL", 0.15, (1, 1)), ("UFM", 0.15, (1, 1)), ("MINC", 0.15, (1, 1))], band="basic", season="flat", codes={},
         sym=["Service light blinking, filters not changed for 8 months", "Scheduled filter change, water flow reduced"],
         cause=["Sediment and carbon filters exhausted, replaced"]),
    dict(key="ro_pump", cat="water_purifier", name="Booster pump / SMPS fault", fams=["RO_UV", "RO_UF", "RO_MIN"], w=14, cls="electrical", lvl=2, gas=False,
         dur=(55, 15), parts=[("BPUMP", 0.5, (1, 1)), ("SMPS", 0.5, (1, 1))], band="standard", season="flat", codes={},
         sym=["Machine on but no water coming, no pump sound", "Pump sound but no flow, light flickering"],
         cause=["SMPS output low, replaced", "Booster pump diaphragm worn, replaced"]),
    dict(key="ro_sol", cat="water_purifier", name="Solenoid / float / leak", fams=["RO_UV", "RO_UF", "RO_MIN"], w=16, cls="water", lvl=2, gas=False,
         dur=(45, 10), parts=[("SOL", 0.5, (1, 1)), ("FLT", 0.3, (1, 1)), ("FIT", 0.4, (1, 1))], band="basic", season="flat", codes={},
         sym=["Water keeps running to drain, tank not filling", "Leak under purifier near tubing", "Tank full but pump keeps running"],
         cause=["Solenoid stuck open, replaced", "Elbow fitting cracked, replaced", "Float switch stuck, replaced"]),
    dict(key="ro_uv", cat="water_purifier", name="UV lamp fault", fams=["RO_UV", "RO_UF"], w=10, cls="electrical", lvl=1, gas=False,
         dur=(35, 10), parts=[("UVL", 0.85, (1, 1))], band="basic", season="flat", codes={},
         sym=["UV light blinking red, water not dispensing", "UV indicator off"],
         cause=["UV lamp life over, replaced with ballast"]),
    # ---- water heater
    dict(key="gy_element", cat="water_heater", name="Heating element failure", fams=["GY_ST", "GY_IN"], w=34, cls="heating", lvl=2, gas=False,
         dur=(60, 20), parts=[("HEL_ST", 0.5, (1, 1)), ("HEL_IN", 0.5, (1, 1)), ("FLG", 0.3, (1, 1))], band="standard", season="geyser", codes={},
         sym=["No hot water, indicator on", "Water only lukewarm, takes long to heat", "Heater trips MCB when switched on"],
         cause=["Heating element scaled and burnt, replaced", "Element open circuit, replaced"]),
    dict(key="gy_thermo", cat="water_heater", name="Thermostat / thermal cut-out fault", fams=["GY_ST", "GY_IN"], w=24, cls="heating", lvl=2, gas=False,
         dur=(50, 15), parts=[("THS", 0.6, (1, 1)), ("TCO", 0.5, (1, 1))], band="basic", season="geyser", codes={},
         sym=["Water too hot, steam from outlet", "Heater switches off before water is hot", "Thermal cut-out keeps tripping"],
         cause=["Thermostat stuck, replaced", "Thermal cut-out tripped permanently, replaced"]),
    dict(key="gy_leak", cat="water_heater", name="Tank / valve / flange leak", fams=["GY_ST"], w=15, cls="leak", lvl=2, gas=False,
         dur=(55, 15), parts=[("PRV", 0.5, (1, 1)), ("FLG", 0.45, (1, 1))], band="standard", season="geyser", codes={},
         sym=["Water dripping from bottom of geyser", "Water coming from safety valve continuously"],
         cause=["Pressure relief valve weeping, replaced", "Flange gasket perished, replaced"]),
    dict(key="gy_anode", cat="water_heater", name="Anode rod / scale (service)", fams=["GY_ST"], w=12, cls="service", lvl=1, gas=False,
         dur=(60, 15), parts=[("ANODE", 0.8, (1, 1)), ("FLG", 0.5, (1, 1))], band="basic", season="geyser", codes={},
         sym=["Brownish water from geyser, not serviced for 3 years", "Rust smell in hot water"],
         cause=["Anode rod consumed, replaced and tank descaled"]),
    dict(key="gy_earth", cat="water_heater", name="Earth leakage (shock) fault", fams=["GY_ST", "GY_IN"], w=6, cls="safety", lvl=3, gas=False,
         dur=(70, 20), parts=[("HEL_ST", 0.45, (1, 1)), ("HEL_IN", 0.45, (1, 1)), ("CORD", 0.3, (1, 1))], band="standard", season="geyser", codes={},
         sym=["Mild shock felt when touching tap or body", "ELCB trips when geyser switched on"],
         cause=["Element insulation breakdown causing leakage, replaced and earthing verified", "Earthing missing at point, rectified"], safety=True),
    dict(key="gy_misc", cat="water_heater", name="Indicator / cord / switch", fams=["GY_ST", "GY_IN"], w=9, cls="electrical", lvl=1, gas=False,
         dur=(30, 10), parts=[("LAMP", 0.4, (1, 1)), ("CORD", 0.3, (1, 1))], band="basic", season="geyser", codes={},
         sym=["Indicator lamp not glowing but water heats", "Power cord hot near plug"],
         cause=["Indicator lamp failed, replaced", "Plug and cord overheated, replaced"]),
]
FAULT_BY_KEY = {f["key"]: f for f in FAULTS}
for _f in FAULTS:
    _f.setdefault("safety", False)

# -------------------------------------------------------------------------
# Rate card (rupees). Revised 1 Apr 2026 to exercise effective dating.
# -------------------------------------------------------------------------
JOB_TYPES = ["installation", "preventive_service", "repair", "coverage_claim", "uninstall_reinstall", "inspection_advice"]
RATE_BASE = {  # category: (visit_fee, {band: labour}, installation, preventive, uninstall_reinstall, inspection)
    "air_conditioner": (399, {"basic": 450, "standard": 850, "complex": 1600}, 1800, 699, 1800, 299),
    "refrigerator": (349, {"basic": 400, "standard": 700, "complex": 1500}, 299, 0, 0, 249),
    "washing_machine": (349, {"basic": 400, "standard": 700, "complex": 1400}, 600, 499, 500, 249),
    "water_purifier": (299, {"basic": 350, "standard": 600, "complex": 1000}, 700, 549, 600, 199),
    "water_heater": (299, {"basic": 350, "standard": 600, "complex": 1100}, 700, 549, 600, 199),
}
def build_rates():
    for cat, (visit, lab, inst, prev, unin, insp) in RATE_BASE.items():
        for (vf, valid_from, valid_to, bump) in [(visit, dt.date(2025, 9, 1), dt.date(2026, 4, 1), 1.0),
                                                 (visit, dt.date(2026, 4, 1), None, 1.06)]:
            def r(x): return int(round(x * bump / 10) * 10)
            for band in ("basic", "standard", "complex"):
                for jt, labour in (("repair", lab[band]), ("coverage_claim", lab[band])):
                    add("rate_card", id=uid("rate", f"{cat}-{jt}-{band}-{valid_from}"), category_code=cat, job_type=jt,
                        complexity_band=band, visit_fee_paise=r(vf) * 100, labour_paise=r(labour) * 100,
                        valid_from=valid_from, valid_to=valid_to)
            for jt, base in (("installation", inst), ("preventive_service", prev), ("uninstall_reinstall", unin), ("inspection_advice", insp)):
                if base:
                    for band, mult in (("basic", 1.0), ("standard", 1.35), ("complex", 1.9)):
                        add("rate_card", id=uid("rate", f"{cat}-{jt}-{band}-{valid_from}"), category_code=cat, job_type=jt,
                            complexity_band=band, visit_fee_paise=(0 if jt in ("installation",) else r(vf)) * 100,
                            labour_paise=r(base * mult) * 100, valid_from=valid_from, valid_to=valid_to)

if __name__ == "__main__":
    build_catalogue(); build_rates()
    print({k: len(v) for k, v in TABLES.items()})
