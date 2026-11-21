"""Knowledge-base PDFs (L2 documents). Fictional brands; content is internally consistent with the catalogue and fault library."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from common import *
from catalogue import *
from world import WARRANTY
import safefix

ST = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ST["Heading1"], fontName="Helvetica-Bold", fontSize=15, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#14365d"))
H2 = ParagraphStyle("h2", parent=ST["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#14365d"))
BODY = ParagraphStyle("b", parent=ST["BodyText"], fontName="Helvetica", fontSize=9.6, leading=13.2, spaceAfter=4)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=8.4, leading=11)
CELL = ParagraphStyle("c", parent=BODY, fontSize=8.6, leading=10.8, spaceAfter=0)
CELLB = ParagraphStyle("cb", parent=CELL, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("n", parent=BODY, backColor=colors.HexColor("#fff4d6"), borderPadding=5, leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8)
WARN = ParagraphStyle("w", parent=BODY, backColor=colors.HexColor("#fde2e2"), borderPadding=5, leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8)

class Doc:
    def __init__(self, key, title, subtitle, code, rev, date, brand=None, cat=None, series=None, dtype="manual", authority="oem", audience="technician", valid_to=None):
        self.key, self.title, self.subtitle, self.code, self.rev, self.date = key, title, subtitle, code, rev, date
        self.meta = dict(brand=brand, cat=cat, series=series, dtype=dtype, authority=authority, audience=audience, valid_to=valid_to)
        self.flow = [Spacer(1, 18 * mm), Paragraph(title, ParagraphStyle("t", parent=H1, fontSize=22, leading=27, spaceAfter=8)),
                     Paragraph(subtitle, ParagraphStyle("st", parent=BODY, fontSize=12, textColor=colors.HexColor("#555555"))), Spacer(1, 6 * mm),
                     Paragraph(f"Document {code} &nbsp;|&nbsp; Revision {rev} &nbsp;|&nbsp; Issued {date}", SMALL),
                     Paragraph("Fictional documentation prepared for the Keepwell prototype. Brands, codes and terms are invented and must not be used for real repairs.", SMALL),
                     Spacer(1, 6 * mm)]
    def h1(self, t): self.flow.append(Paragraph(t, H1))
    def h2(self, t): self.flow.append(Paragraph(t, H2))
    def p(self, t): self.flow.append(Paragraph(t, BODY))
    def note(self, t): self.flow.append(Paragraph("<b>Note.</b> " + t, NOTE))
    def warn(self, t): self.flow.append(Paragraph("<b>Warning.</b> " + t, WARN))
    def bullets(self, items):
        for i in items:
            self.flow.append(Paragraph("&bull;&nbsp; " + i, ParagraphStyle("li", parent=BODY, leftIndent=12, firstLineIndent=-8, spaceAfter=2)))
        self.flow.append(Spacer(1, 3))
    def steps(self, items):
        for n, i in enumerate(items, 1):
            self.flow.append(Paragraph(f"<b>{n}.</b>&nbsp; " + i, ParagraphStyle("st", parent=BODY, leftIndent=14, firstLineIndent=-10, spaceAfter=2)))
        self.flow.append(Spacer(1, 3))
    def table(self, header, rows, widths=None):
        data = [[Paragraph(str(h), CELLB) for h in header]] + [[Paragraph(str(c), CELL) for c in r] for r in rows]
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5edf7")), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c4d4")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        self.flow += [t, Spacer(1, 6)]
    def pagebreak(self): self.flow.append(PageBreak())
    def build(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, f"{self.key}.pdf")
        def deco(c, d):
            c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor("#666666"))
            c.drawString(18 * mm, 10 * mm, f"{self.code}  rev {self.rev}  |  {self.title}")
            c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")
            c.restoreState()
        SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                          title=self.title, author="Keepwell prototype (fictional)").build(self.flow, onFirstPage=deco, onLaterPages=deco)
        return path

def codes_table(doc, brand, cat):
    rows = ERROR_CODES[(brand, cat)]
    doc.table(["Code", "Meaning", "First action"], [[c, m, a] for c, m, a in rows], [20 * mm, 70 * mm, 84 * mm])

def specs_table(doc, brand, cat):
    rows = []
    for b, c, code, series, year, fam, sp in MODELS:
        if b == brand and c == cat:
            rows.append([code, series, year] + [f"{k}: {v}" for k, v in sp.items()][:4])
    doc.table(["Model", "Series", "Launch year", "Specification", "", "", ""][:3 + max(len(r) - 3 for r in rows)], rows)

OUT = []
def reg(doc):
    OUT.append(doc); return doc

def parts_for_model_table(doc, brand, cats):
    bid = uid("brand", brand)
    pm = {}
    mods = {m["id"]: m["model_code"] for m in TABLES["appliance_model"]}
    for pc in TABLES["part_compatibility"]:
        pm.setdefault(pc["part_id"], []).append((mods[pc["model_id"]], pc["revision"]))
    rows = []
    for p in TABLES["part_catalogue"]:
        if p["brand_id"] == bid and p["kind"] == "genuine":
            fits = sorted({m + (f" rev {r}" if r else "") for m, r in pm.get(p["id"], []) if MODEL_BY_CODE[m][1] in cats})
            if fits:
                rows.append([p["part_no"], p["name"], ", ".join(fits), f"Rs {p['mrp_paise'] // 100:,}"])
    rows.sort()
    doc.table(["Part no.", "Description", "Fits", "MRP"], rows, [32 * mm, 56 * mm, 64 * mm, 22 * mm])

# ----------------------------------------------------------------------------------------- documents
def build_all(outdir):
    # 1 Aerovane manual -------------------------------------------------------------------
    d = reg(Doc("av_manual", "Aerovane Vortex, Sky and Flow split air conditioners", "Operation, maintenance and service manual", "AV-AC-SM-04", "D", "2025-08-14",
                "aerovane", "air_conditioner", "Vortex,Sky,Flow", "manual"))
    d.h1("1. Models covered")
    d.p("This manual covers the Aerovane Vortex and Sky inverter split air conditioners and the Flow fixed-speed split. All models use R32 refrigerant. "
        "Inverter models have DC fan motors and a variable-speed compressor driven by an outdoor inverter module. The Flow is a fixed-speed unit with an AC induction outdoor fan motor and a compressor driven directly from the supply through contactor and run capacitors.")
    specs_table(d, "aerovane", "air_conditioner")
    d.h1("2. Safety")
    d.warn("Isolate the supply at the outdoor isolator and the indoor MCB before opening any panel. Wait 3 minutes for the inverter module capacitors to discharge on inverter models. Refrigerant work must be done only by a technician certified for R32 handling.")
    d.bullets(["R32 is mildly flammable (class A2L). No open flame near the unit. Use a refrigerant-rated leak detector.",
               "Outdoor units above the second floor must be serviced only by technicians certified for work at height, using a harness anchored to a structural point.",
               "Do not bypass the overload protector or the supply fuse. A repeatedly tripping MCB indicates a fault, not an undersized MCB."])
    d.h1("3. Installation requirements")
    d.table(["Item", "Requirement"], [
        ["Standard copper pipe length", "3 m included; up to 15 m allowed for 1.0 and 1.5 T; 20 m for 2.0 T. Additional length needs extra refrigerant charge of 15 g per metre beyond 5 m."],
        ["Height difference", "Indoor above outdoor: up to 7 m. Outdoor above indoor: up to 5 m."],
        ["Drain hose", "Slope continuously downwards, minimum 1 cm per metre. No loops, bends held up by clips, or low points that hold water."],
        ["Outdoor clearance", "30 cm behind, 60 cm at sides, 200 cm in front, 100 cm above."],
        ["Supply", "Dedicated supply with 16 A MCB for 1.0 and 1.5 T inverter units; 20 A for 2.0 T. Earthing mandatory."]], [48 * mm, 126 * mm])
    d.h1("4. Routine maintenance (every 6 months in regular use)")
    d.steps(["Remove and wash indoor filters; dry in shade before refitting.", "Clean indoor coil and blower wheel with low-pressure jet; protect the PCB and display from water.",
             "Flush the drain tray and drain line; confirm free flow by pouring 500 ml of water into the tray.", "Clean the outdoor condenser coil from inside to outside; straighten fins.",
             "Check the refrigerant pressure only if cooling is poor. Do not add gas routinely.", "Tighten electrical terminals at the indoor and outdoor terminal blocks.",
             "Verify cooling: supply-return air temperature difference of at least 8 degrees C after 15 minutes at 24 degrees C set point."])
    d.note("A drop in cooling with ice on the indoor pipe usually means low charge or blocked airflow. Always clean filters and the coil first, then check pressure. Adding gas without finding the leak leads to repeat visits.")
    d.h1("5. Parts and consumables")
    d.p("Part numbers for these models are listed in Parts List AV-AC-PL-03. Always quote the model code and, for PCBs, the board revision.")

    # 2 Aerovane error codes ---------------------------------------------------------------
    d = reg(Doc("av_error_codes", "Aerovane split air conditioner error codes", "Indoor unit display codes, Vortex and Sky series", "AV-AC-EC-02", "C", "2025-08-14",
                "aerovane", "air_conditioner", "Vortex,Sky", "error_codes"))
    d.h1("1. How codes are shown")
    d.p("The indoor display shows the code in red seven-segment digits. The operation lamp blinks once per second while a protection is active. The unit restarts automatically after 3 minutes for E1, E2 and E3. For E4, E5, E6 and E7 the unit stays locked out until the supply is cycled.")
    codes_table(d, "aerovane", "air_conditioner")
    d.h1("2. Notes by code")
    d.h2("E5 versus E6")
    d.p("E5 and E6 are often confused. E5 is an electrical protection of the compressor drive (current too high). E6 is a refrigerant protection (pressure too low). "
        "A unit that shows E6 with ice on the indoor pipe and a warm outdoor pipe is low on gas. A unit that shows E5 shortly after the compressor starts points to the outdoor fan, condenser coil, supply voltage or the outdoor module, not to low gas.")
    d.h2("E4 on the Flow series")
    d.p("The Flow (fixed-speed) does not report E4 or E5. Faults on the Flow appear as symptoms only; use the troubleshooting guide AV-AC-TS-05.")
    d.h2("H1 anti-ice")
    d.p("H1 shows when the pipe sensor reads below 0 degrees C for 5 minutes. Check filters and coil before suspecting gas.")
    d.note("Another brand's code of the same name can mean something different. E5 on Zenith units means indoor to outdoor communication loss. Always read codes against the brand and series of the unit.")

    # 3 Aerovane troubleshooting ----------------------------------------------------------------
    d = reg(Doc("av_troubleshooting", "Aerovane split air conditioners: troubleshooting guide", "Symptom, checks, likely cause and action", "AV-AC-TS-05", "B", "2025-09-02",
                "aerovane", "air_conditioner", "Vortex,Sky,Flow", "troubleshooting"))
    d.h1("1. Cooling poor or absent")
    d.table(["Check", "Result", "Likely cause", "Action"], [
        ["Filters and indoor coil", "Clogged", "Restricted airflow", "Jet-clean; re-test. Do not add gas."],
        ["Pipe frost or ice", "Ice on indoor pipe, outdoor valve cold or frosted", "Low charge (leak)", "Leak-test joints (flare nuts, service valve), repair, recover, evacuate, recharge to nameplate. Typical top-up need: 200 to 500 g."],
        ["Outdoor fan", "Not rotating (fixed-speed Flow)", "Fan capacitor 2.5 uF failed", "Replace capacitor. Check fan motor winding if capacitor is good."],
        ["Outdoor fan", "Not rotating (Vortex, Sky)", "DC fan motor or outdoor module fault (E7 or E5)", "Check motor connector, then replace outdoor DC fan motor."],
        ["Compressor", "Hums, no start (Flow)", "Compressor run capacitor 35 uF weak", "Replace capacitor; if it persists, check compressor windings."],
        ["Compressor", "Hums, no start (Vortex, Sky)", "Outdoor inverter module or compressor", "There is no compressor capacitor on inverter units. Check E5, then module, then compressor."]],
            [34 * mm, 38 * mm, 42 * mm, 60 * mm])
    d.note("Inverter units have no fan or compressor capacitors. Do not carry capacitors as a first fix for Vortex or Sky outdoor faults.")
    d.h1("2. Water leaking from indoor unit")
    d.steps(["Check that the unit is level and the drain tray is intact.", "Run the unit in cool mode for 10 minutes and watch the drain outlet.",
             "If the outlet is dry and water drips from the unit, inspect for a sagging drain hose with a low point that holds water; correct the slope to at least 1 cm per metre.",
             "If the hose is clear and sloped, flush the drain line with nitrogen or low-pressure water to clear algae. Replace the hose only if it is cracked or collapsed.",
             "Check the filter seating and insulation at the pipe joint for condensation drip."])
    d.p("Most leak complaints within the first 12 months of a new installation come from the drain run (low point, kinked hose) and not from a faulty unit. Where the drain run was part of the installation, the repair is the installer's responsibility.")
    d.h1("3. Display blank, remote not responding, random shutdown")
    d.p("Check supply voltage at the outdoor isolator (170 to 270 V), then the indoor PCB. Relay chatter on the indoor board is a known failure on Vortex units built before March 2026. "
        "Replace the indoor PCB with part AV-AC-PCBI-A as per the original design. <i>(See Service Bulletin SB-AV-2026-02 for the current instruction.)</i>")
    d.h1("4. Noise")
    d.bullets(["Indoor blower noise or intermittent stop with E3: blower motor bearing; replace motor.", "Outdoor rattle: loose fan blade or mounting bolts; tighten before replacing parts.",
               "Humming outdoor unit with no cooling on a fixed-speed Flow: check fan capacitor first, then compressor capacitor."])

    # 4 Aerovane bulletin ------------------------------------------------------------------------
    d = reg(Doc("av_bulletin_pcb", "Service Bulletin SB-AV-2026-02", "Indoor PCB relay failure, Vortex series: revised replacement part", "SB-AV-2026-02", "A", "2026-03-10",
                "aerovane", "air_conditioner", "Vortex", "bulletin", valid_to=None))
    d.h1("1. Affected units")
    d.p("Aerovane Vortex AV-VX18I3 and AV-VX12I3 with indoor PCB revision A, manufactured between January 2023 and December 2023.")
    d.h1("2. Problem")
    d.p("The fan relay on indoor PCB revision A can burn after repeated cycling. Symptoms: unit switches off by itself, remote not responding, display blank, or E4 reported with a good interconnect cable.")
    d.h1("3. Instruction")
    d.warn("This bulletin supersedes the PCB replacement instruction in Troubleshooting Guide AV-AC-TS-05 rev B. Do not fit revision A boards on affected units.")
    d.steps(["Confirm model code and PCB revision printed near the connector.", "Replace the indoor PCB with <b>AV-AC-PCBI-B</b>. Revision B is backwards compatible with Vortex units that shipped with revision A.",
             "Do not mix connector harnesses between revisions; use the harness supplied in the kit.", "Record old and new serial numbers on the job card."])
    d.h1("4. Warranty")
    d.p("Indoor PCB failures on affected units are covered for 24 months from installation as parts-only under Aerovane warranty terms; labour follows the 12 month comprehensive period.")

    # 5 Aerovane parts list ---------------------------------------------------------------------
    d = reg(Doc("av_parts_list", "Aerovane split air conditioners: genuine parts list", "Part numbers, fitment and list price", "AV-AC-PL-03", "E", "2026-04-01",
                "aerovane", "air_conditioner", "Vortex,Sky,Flow", "parts_view"))
    d.h1("Genuine parts")
    d.p("Prices are list price (MRP) inclusive of GST at the time of issue.")
    parts_for_model_table(d, "aerovane", ["air_conditioner"])
    d.note("Indoor PCB: revision B supersedes revision A on all Vortex units. Sky units ship with revision B only.")

    # 6 Zenith AC manual -----------------------------------------------------------------------
    d = reg(Doc("zn_ac_manual", "Zenith CoolSense and Aura split air conditioners", "Operation, error codes and service guide", "ZN-AC-SM-02", "B", "2025-07-30",
                "zenith", "air_conditioner", "CoolSense,Aura", "manual"))
    d.h1("1. Models covered")
    specs_table(d, "zenith", "air_conditioner")
    d.h1("2. Error codes")
    codes_table(d, "zenith", "air_conditioner")
    d.note("On Zenith units E5 means indoor to outdoor communication loss. It does not indicate a compressor protection. Compressor over-current is reported as F5.")
    d.h1("3. Service procedure")
    d.steps(["Record model code and serial from the indoor unit sticker.", "Read the stored last 3 fault codes: press the Display button 5 times within 5 seconds.",
             "Clean filters and coil before any refrigerant work.", "For F0, leak-test joints; recharge to the nameplate quantity (see sticker) after repair.",
             "For F5, check supply voltage, outdoor fan and condenser coil; if clear, test the outdoor module.", "Close the job with a cooling performance check after 15 minutes."])
    d.h1("4. Drain protection P1")
    d.p("P1 is raised when the drain tray float switch trips. Clear the drain line, check the slope, and verify that the float moves freely.")

    # 7 Zenith install guide --------------------------------------------------------------------
    d = reg(Doc("zn_install_guide", "Zenith split air conditioner installation guide", "Requirements for CoolSense and Aura", "ZN-AC-IG-01", "C", "2025-07-30",
                "zenith", "air_conditioner", "CoolSense,Aura", "installation"))
    d.h1("1. Warranty condition")
    d.warn("Zenith warranty applies only if installation is done by a Zenith authorised centre or an installer approved by Zenith. Record the installer identity and date on the installation certificate.")
    d.h1("2. Site requirements")
    d.table(["Item", "Requirement"], [
        ["Pipe length", "3 m standard (included). Maximum 15 m for 1.5 T. Extra pipe and refrigerant are chargeable."],
        ["Height", "Outdoor unit may be at most 10 m above the indoor unit."],
        ["Drain", "Minimum slope 1 cm per metre, no low points, drain terminated at least 5 cm above the discharge point."],
        ["Outdoor unit support", "Wall bracket or ledge rated for at least 4 times the unit weight (Aura 1.5 T outdoor: 38 kg). Use four 10 mm anchor bolts; do not stand the unit on a loose slab."],
        ["Electrical", "Dedicated 16 A supply, 3-core 2.5 sq mm copper, earthing verified, MCB rating per nameplate."]], [48 * mm, 126 * mm])
    d.h1("3. High-rise and ledge installations")
    d.bullets(["Above the 3rd floor, the outdoor unit must be installed from inside the balcony or a safe platform; no one may lean out of a window without a harness.",
               "Installer must hold work-at-height certification and use a full-body harness anchored to a structural point rated for 22 kN.",
               "Confirm society rules and permission for external ledge installation before the visit.", "Estimated time on a 9th-floor ledge installation: 2 to 3 hours with two people."])
    d.h1("4. Commissioning")
    d.steps(["Vacuum the pipe set to below 500 microns for 20 minutes.", "Release charge, leak-test flare joints with soapy water or a detector.",
             "Run for 15 minutes; record suction pressure, current and supply-return temperature difference.", "Demonstrate remote, timer and filter cleaning to the household; hand over warranty card."])

    # 8 Zenith fridge and washer -----------------------------------------------------------------------
    d = reg(Doc("zn_fridge_washer", "Zenith Frost Inverter refrigerator and AquaFlow washer", "Operation, error codes and service notes", "ZN-HA-SM-01", "A", "2025-09-10",
                "zenith", "refrigerator", "Frost Inverter,AquaFlow", "manual"))
    d.h1("1. Refrigerator ZN-F300I: display codes")
    codes_table(d, "zenith", "refrigerator")
    d.p("<b>dF</b> appears when the defrost cycle exceeds 45 minutes or the evaporator sensor does not reach 5 degrees C in the cycle. "
        "A freezer full of frost with a warm fresh-food section and dF displayed indicates a defrost heater or defrost thermostat failure. Replace the heater and thermostat together.")
    d.note("Frostline refrigerators use a different code for defrost failure (Er4). Do not mix code tables between brands.")
    d.h1("2. Washer ZN-W75T: display codes")
    codes_table(d, "zenith", "washing_machine")
    d.h1("3. Service notes")
    d.bullets(["nd: clean the drain filter first; replace the drain motor only if the impeller is intact and the motor does not run.", "Ub: level the machine and distribute the load; inspect suspension rods.",
               "CE on the refrigerator: check the inverter drive board before replacing the compressor."])

    # 9 Frostline manual -------------------------------------------------------------------------
    d = reg(Doc("fl_fridge_manual", "Frostline Duo and Solo refrigerators", "Operation, display codes and service guide", "FL-RF-SM-03", "C", "2025-08-20",
                "frostline", "refrigerator", "Duo,Solo", "manual"))
    d.h1("1. Models")
    specs_table(d, "frostline", "refrigerator")
    d.h1("2. Display codes (Duo frost-free)")
    codes_table(d, "frostline", "refrigerator")
    d.h1("3. Frost build-up and warm fresh-food section (Duo)")
    d.p("The Duo cools the fresh-food section by air from the freezer evaporator. When frost builds up on the back wall of the freezer the airflow stops and the fresh-food section warms up.")
    d.table(["Check", "Finding", "Action"], [
        ["Defrost heater continuity", "Open circuit", "Replace defrost heater and bimetal thermostat together (parts FL-FR-DEFH, FL-FR-DEFT)"],
        ["Bimetal thermostat", "Not closing below -5 degrees C", "Replace with the heater as a pair"],
        ["Door gasket", "Torn or hardened", "Replace the gasket; manually defrost the evaporator before testing"],
        ["Evaporator fan", "Not rotating", "Clear ice; replace fan motor if seized"]], [45 * mm, 50 * mm, 79 * mm])
    d.note("Manually defrost for 8 hours before testing a fix; otherwise residual ice masks the result.")
    d.h1("4. Compressor does not start (clicking)")
    d.p("Clicking followed by a trip of the overload means the PTC start relay is weak. Replace the PTC relay and overload protector together (FL-FR-PTC). Measure compressor winding resistance if the problem returns.")
    d.h1("5. Direct-cool Solo")
    d.p("The Solo (FL-S190) has a mechanical thermostat and no display. Over-cooling or no cooling with a thermostat that does not click points to the thermostat. The Solo door gasket is model specific (FL-FR-GASK-S190).")

    # 10 Frostline bulletin -----------------------------------------------------------------------
    d = reg(Doc("fl_defrost_bulletin", "Service Bulletin SB-FL-2026-01", "Defrost heater and bimetal replacement as a pair, Duo series", "SB-FL-2026-01", "A", "2026-01-22",
                "frostline", "refrigerator", "Duo", "bulletin"))
    d.p("Repeat visits for frost build-up on FL-D260 and FL-D340 were traced to replacing only the defrost heater while leaving a stuck bimetal thermostat. "
        "From 22 January 2026 the defrost heater FL-FR-DEFH and bimetal FL-FR-DEFT must always be replaced together and the freezer manually defrosted before the test. "
        "Er4 may or may not display before the fault; its absence does not rule out defrost failure.")

    # 11 Wavecrest washer ---------------------------------------------------------------------
    d = reg(Doc("wc_washer_manual", "Wavecrest TopWash, FrontWash and TwinTub washing machines", "Operation, error codes and service guide", "WC-WM-SM-02", "B", "2025-08-18",
                "wavecrest", "washing_machine", "TopWash,FrontWash,TwinTub", "manual"))
    d.h1("1. Models")
    specs_table(d, "wavecrest", "washing_machine")
    d.h1("2. Display codes")
    codes_table(d, "wavecrest", "washing_machine")
    d.h1("3. E21: water not draining")
    d.steps(["Switch off and unplug. Drain remaining water through the emergency drain tube.", "Clean the drain filter (front lower panel on FrontWash). Coins, hairpins and lint are the most common cause.",
             "Check the outlet hose for kinks and the standpipe for partial blockage; the hose must not be pushed fully into the standpipe.",
             "Run a drain-only cycle. If the pump or motor does not run, test continuity and replace the pump (FrontWash) or drain motor (TopWash).",
             "Replace parts only after the filter, hose and standpipe are clear."])
    d.p("A repeat of E21 within 30 days of a pump or motor replacement usually means the hose or standpipe, not the new part.")
    d.h1("4. Semi-automatic TwinTub: burning smell")
    d.warn("A burning smell or smoke from the motor means the run capacitor or motor winding is overheating. Disconnect the supply immediately and do not run the machine again until inspected by a technician.")
    d.p("Common causes: failed motor run capacitor (WC-WM-MCAP), slipped or worn belt (WC-WM-BELT), jammed pulley. Measure winding resistance before fitting a new capacitor.")
    d.h1("5. Top-load lid detection")
    d.p("A lid that is closed but the machine beeps and will not start indicates the lid switch (WC-WM-LIDSW) or a broken actuator. Test continuity with the lid closed.")

    # 12 Purelo ------------------------------------------------------------------------------
    d = reg(Doc("pl_ro_manual", "Purelo Aqua, Aqua Plus and Mineral water purifiers", "Operation, filter schedule, TDS interpretation and troubleshooting", "PL-RO-SM-02", "B", "2025-08-25",
                "purelo", "water_purifier", "Aqua,Aqua Plus,Mineral", "manual"))
    d.h1("1. Filter schedule")
    d.table(["Item", "Typical life", "Notes"], [
        ["Sediment filter", "6 months or 2,000 L", "Replace sooner with borewell or tanker water"],
        ["Carbon block filter", "6 months or 2,500 L", "Replace with sediment filter"],
        ["RO membrane 75 GPD", "24 months or 8,000 L", "Replace earlier if rejection falls below 85 percent"],
        ["UV lamp", "12 months", "Blinking red UV light means lamp life over or lamp fault"],
        ["UF membrane (Aqua Plus)", "12 months", ""], ["Mineraliser (Mineral)", "6 months", ""]], [48 * mm, 44 * mm, 82 * mm])
    d.h1("2. TDS interpretation")
    d.p("Measure input TDS (tap) and output TDS (purified). Rejection percent is (input minus output) divided by input. Healthy output TDS is below 100 ppm on municipal water and below 150 ppm on borewell water.")
    d.table(["Observation", "Meaning", "Action"], [
        ["Rejection above 90 percent", "Membrane healthy", "None"],
        ["Rejection 70 to 90 percent", "Membrane ageing or scaled", "Flush; replace membrane if no improvement"],
        ["Rejection below 70 percent, or output equal to or above input", "Membrane failed or bypass leaking", "Replace membrane and check seals and the flow restrictor"],
        ["Low output flow with normal TDS", "Sediment or carbon filter choked, or pump weak", "Replace filters, then test pump pressure (should be above 60 psi)"]], [60 * mm, 54 * mm, 60 * mm])
    d.note("Replacing only filters when output TDS is high does not fix a failed membrane. Always compare input and output TDS before ordering parts.")
    d.h1("3. Other faults")
    d.bullets(["No water, no pump sound: SMPS adapter 24 V output low; replace SMPS.", "Pump runs, no flow: pump diaphragm worn or solenoid not opening.",
               "Water runs to drain continuously, tank not filling: solenoid stuck open or float switch stuck.", "Leak under unit: check elbow fittings and tubing; replace fitting set."])
    d.h1("4. Warranty and consumables")
    d.p("Filters, membrane and UV lamp are consumables and are not covered by the warranty or by AMC parts cover.")

    # 13 Heatwell ---------------------------------------------------------------------------
    d = reg(Doc("hw_geyser_manual", "Heatwell Store and Instant water heaters", "Installation safety, operation and service guide", "HW-WH-SM-02", "B", "2025-08-12",
                "heatwell", "water_heater", "Store,Instant", "manual"))
    d.h1("1. Models")
    specs_table(d, "heatwell", "water_heater")
    d.h1("2. Safety")
    d.warn("If anyone feels a tingle or shock from a tap, the geyser body or the wall near it, switch off the geyser at the MCB and the wall switch immediately and do not use hot water from it until a qualified technician has tested it. Do not attempt to open the heater.")
    d.bullets(["A 3-pin plug with a proper earth connection and an earth-leakage breaker (ELCB, 30 mA) are mandatory.", "Never reset a tripped ELCB repeatedly. Repeated tripping is a symptom of leakage current.",
               "Technicians must measure insulation resistance between the heating element terminals and the tank body. Below 1 megohm the element must be replaced."])
    d.h1("3. Faults")
    d.table(["Symptom", "Likely cause", "Action"], [
        ["No hot water, indicator on", "Heating element open", "Replace element (HW-WH-HEL_ST on Store, HW-WH-HEL_IN on Instant) and flange gasket"],
        ["Water too hot, steam", "Thermostat stuck", "Replace thermostat and thermal cut-out"],
        ["Shock or ELCB trips", "Element insulation breakdown or missing earth", "Isolate; test insulation and earthing; replace element; verify earth before restoring"],
        ["Water drips from bottom or valve", "Relief valve or flange gasket", "Replace valve or gasket; do not plug the valve"],
        ["Brown water", "Anode rod consumed, scale", "Replace anode rod; descale tank"]], [44 * mm, 52 * mm, 78 * mm])
    d.p("Anode rod life is about 2 years in hard water areas.")

    # 14 Warranty terms ----------------------------------------------------------------------
    d = reg(Doc("warranty_terms_brands", "Brand warranty terms summary", "Aerovane, Zenith, Frostline, Wavecrest, Purelo, Heatwell", "KW-WT-01", "A", "2025-09-01",
                None, None, None, "warranty_terms", authority="oem", audience="both"))
    d.h1("1. How to read this summary")
    d.p("Warranty starts on the installation date (or the purchase date if there was no installation). A comprehensive period covers parts and labour and the visit fee. After it ends, some components continue to be covered for parts only; labour and visit fees are then payable by the household.")
    rows = []
    for b, w in WARRANTY.items():
        po = ", ".join(f"{k.replace('_', ' ')}: {v} months" for k, v in w["parts_only"].items()) or "none"
        rows.append([b.capitalize(), f"{w['comp']} months", f"{w['labour']} months", po, "; ".join(w["exclusions"])])
    d.table(["Brand", "Comprehensive", "Labour", "Parts-only cover", "Exclusions"], rows, [20 * mm, 24 * mm, 18 * mm, 52 * mm, 60 * mm])
    d.h1("2. General conditions")
    d.bullets(["Warranty work must be done by a brand-authorised service centre. Independent centres may service the appliance but the repair is then paid for by the household.",
               "Consumables (filters, membranes, gaskets after 12 months, hoses, UV lamps) are never covered.", "Gas refilling on air conditioners is covered only if the leak is found and repaired under warranty.",
               "Damage from supply voltage outside 170 to 270 V, pests, water ingress, or unauthorised repair voids cover for the affected part.",
               "Claims need the serial number and proof of purchase. A claim reference is issued by the brand helpline before the visit."])
    d.h1("3. Repeat visits")
    d.p("A repeat visit for the same fault within 30 days of a repair is treated as a continuation of the earlier job. The visit fee is waived and the centre must investigate the earlier repair.")

    # 15 Extended warranty -----------------------------------------------------------------
    d = reg(Doc("ext_warranty_assurenest", "AssureNest Extended Care terms", "Extended warranty plan for household appliances", "AN-EW-01", "A", "2025-09-01",
                None, None, None, "warranty_terms", audience="both"))
    d.p("Extends the brand comprehensive warranty by 24 months. Covers parts and labour. A claim number must be obtained from the AssureNest helpline before any visit. Maximum 3 visits per year. Exclusions: consumables, cosmetic damage, pre-existing faults and misuse. The plan activates the day the brand comprehensive warranty ends.")

    # 16-18 AMC -------------------------------------------------------------------------------
    for key, prov, cats, n in (("amc_coolcraft", "Cool Craft AMC Gold", "air conditioners and refrigerators", 2), ("amc_aquacare", "AquaCare RO Care Plan", "RO water purifiers", 3), ("amc_metro", "Metro Home Care AMC", "air conditioners, washing machines and water heaters", 2)):
        d = reg(Doc(key, f"{prov}: annual maintenance contract terms", f"Covers {cats}", f"AMC-{key[4:8].upper()}-01", "A", "2025-09-01", None, None, None, "amc_terms", audience="both"))
        d.p(f"The plan includes {n} preventive services per year and labour for repairs during the plan year. Priority visit within 48 hours of a request.")
        d.bullets(["Spare parts are not included unless listed on the plan certificate. Consumables such as filters, membranes, UV lamps and refrigerant are always chargeable.",
                   "Visit fees are waived for covered appliances. Labour for repairs is included.", "Plan runs 12 months from the activation date shown on the certificate."])

    # 19 Keepwell field guide ------------------------------------------------------------------
    d = reg(Doc("kw_field_guide", "Keepwell technician field guide: safety first", "Escalation rules and household communication", "KW-FG-01", "A", "2026-06-01",
                None, None, None, "troubleshooting", authority="keepwell"))
    d.h1("1. Stop-and-escalate conditions")
    d.bullets(["Any report of electric shock, tingling, sparks, burning smell or smoke: tell the household to switch the appliance off at the MCB and keep away, then dispatch within 4 hours with a qualified technician. Do not give do-it-yourself checks.",
               "Refrigerant smell on an R32 or R600a appliance: ventilate, no flames or switches, certified technician only.", "Water leaking near sockets or the MCB panel: switch off at the MCB first."])
    d.h1("2. Refrigerant handling")
    d.bullets(["Only technicians with gas certification may open a refrigerant circuit.", "Recover refrigerant; never vent. Evacuate to below 500 microns before charging.", "Record the charge added and the leak location on the job card."])
    d.h1("3. Parts discipline")
    d.p("Check model code and board revision before ordering. Prefer genuine parts on warranty jobs. Carry the part that has the highest probability for the fault plus the common consumables.")

    # 20 Keepwell install checklist ----------------------------------------------------------
    d = reg(Doc("kw_install_checklist", "Keepwell installation checklist: split air conditioners", "From site survey to household handover", "KW-IC-01", "A", "2026-06-01",
                None, "air_conditioner", None, "installation", authority="keepwell"))
    d.steps(["Site survey: pipe route length, floor, ledge or balcony outdoor unit location, society permission, supply point and MCB.", "Confirm model, serial and invoice. Photograph the carton label and the invoice.",
             "Mount indoor bracket level; route pipes; maintain drain slope of at least 1 cm per metre without low points.", "Outdoor unit on rated bracket or ledge; harness for work at height.",
             "Flare, vacuum, leak-test, release charge; record pressures.", "Run for 15 minutes; verify cooling difference and drain flow.", "Demonstrate to the household; collect the OTP to close the job; record installer identity on the warranty certificate."])

    # 21 Keepwell safe-fix catalogue (household-facing steps, reviewed) -------------------------
    d = reg(Doc("kw_safe_fix_catalogue", "Keepwell safe-fix catalogue", "Fixes a household may be guided through before a visit", "KW-SF-01", "B", "2026-09-30",
                None, None, None, "safe_fix", authority="keepwell", audience="both"))
    d.h1("1. The safe-fix threshold")
    d.p("A fix is listed only if every one of these is true. If any is false the fix is not listed and the agent does not offer it.")
    d.bullets(["Reversible, and the worst case of doing it is that nothing changes.", "No tools. Nothing is opened except a cover that the maker's own manual tells the household to open.",
               "One sentence and about two minutes per step, six steps at most.", "Checkable: the household can see whether it worked.",
               "Supported by the maker's manual or by a named reviewer, with a review date. A fix past its review date is withdrawn until re-reviewed.",
               "Never listed: factory reset, firmware changes, battery removal, replacing a part, mains wiring, anything inside the unit."])
    d.h1("2. Stop at once if")
    d.bullets(["there is a shock, a burning smell, smoke or sparks;", "water is near a switchboard or socket;", "the appliance or its plug is hot or swollen;", "the household is unsure or unwilling. A no or silence is a no."])
    d.h1("3. Catalogue")
    for f in safefix.FIXES:
        d.h2(f"{f['code']}: {f['title']}")
        d.p(f"Appliance: {f['cat'].replace('_', ' ')}. Applies to: {f['brand'] or 'any brand'}. About {f['minutes']} minutes. Reviewed {f['reviewed']} by {safefix.REVIEWERS[f['rev']][0]}, review due {f['due']}. Status: {f.get('status', 'active')}.")
        d.steps([f"{s} <i>Check: {c}</i>" for s, c in f["steps"]])
        d.p(f"<b>Worst case:</b> {f['worst']} <b>Stop if:</b> {f['stop']}")
    # household checks added to each maker's manual so the cited page exists
    for dd in OUT:
        fx = safefix.BY_MANUAL.get(dd.key)
        if fx and dd.key != "kw_safe_fix_catalogue":
            dd.h1("Household checks you may do yourself")
            dd.p("The checks below are safe for the household and need no tools. Stop and call the service centre if the stop condition applies.")
            for f in fx:
                if f.get("status") == "retired":
                    continue
                dd.h2(f["title"])
                dd.steps([s for s, c in f["steps"]])
                dd.p(f"<b>Stop if:</b> {f['stop']}")
    paths = []
    for dd in OUT:
        paths.append((dd, dd.build(outdir)))
    return paths

def find_manual_pages(paths):
    """Page on which 'Household checks you may do yourself' starts, per KB document."""
    import subprocess
    pages = {}
    for dd, path in paths:
        n = int(subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
        for pg in range(1, n + 1):
            t = subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg), path, "-"], capture_output=True, text=True).stdout
            if "Household checks you may do yourself" in t or (dd.key == "kw_safe_fix_catalogue" and "3. Catalogue" in t):
                pages[dd.key] = pg; break
    return pages

def register_kb_rows(paths):
    for dd, path in paths:
        m = dd.meta
        add("kb_document", id=uid("kbdoc", dd.key), title=dd.title, brand_id=uid("brand", m["brand"]) if m["brand"] else None, category_code=m["cat"],
            model_series=m["series"], doc_type=m["dtype"], language="en", version_year=int(dd.date[:4]), valid_to=m["valid_to"], authority=m["authority"],
            audience=m["audience"], storage_uri=f"gs://keepwell-sim/kb/{dd.key}.pdf", file_search_store=None, file_search_doc=None, rights_status="confirmed",
            created_at=ist(2025, 9, 1, 9) if dd.date < "2026" else ist(int(dd.date[:4]), int(dd.date[5:7]), int(dd.date[8:10]), 9), updated_at=ist(2026, 6, 1, 9))

if __name__ == "__main__":
    build_catalogue(); build_rates()
    paths = build_all("/tmp/kbtest")
    print(len(paths), "pdfs")
