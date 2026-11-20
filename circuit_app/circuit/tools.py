"""Allowlisted tools the agent may call, plus the deterministic S5 readiness gate.
World facts (approvals, assignment, custody, partner responses) can ONLY be set by
external actor events in app.py, never by the model."""
import json
import re
import uuid
from . import db, seed

PINE_DOC = "Pine Labs UPI Reserve Pay / mandate docs (pinelabs.com/docs -> Online Payments -> UPI Reserve Pay). Verify exact section before recording."
DELHIVERY_DOC = "Delhivery Maps API Reference -> Distance Matrix (delhivery.com/maps/reference). Verify exact section before recording."

MODEL_EDITABLE = {"brand", "model", "model_confirmed", "warranty_status", "error_code", "symptom",
                  "hazard", "address_landmark", "reporter_name", "payer_name", "payer_is_reporter",
                  "diagnosis_hypotheses", "diagnosis_source_ids"}

TOOL_SPECS = {
    "search_knowledge": "args {query}: full-text search over ingested AC guidance (RAG). Returns chunks with source_id + provenance.",
    "lookup_machine_kundli": "args {model}: consented machine history record (fourth rail, prototype). Absent record != known machine.",
    "search_mistri_gyan": "args {symptom}: reviewed fault library: safe household checks, likely causes, technician tests.",
    "update_case": f"args {{fields}}: set case facts heard from humans. Allowed keys: {sorted(MODEL_EDITABLE)}. warranty_status one of UNKNOWN|IN_WARRANTY|OUT_OF_WARRANTY.",
    "rank_technicians": "args {skills_needed:[str]}: rank fictional agency technicians by skill match, earliest slot, experience.",
    "check_kit": "args {model}: check agency stock compatibility for a confirmed model.",
    "request_agency_assignment": "args {tech_ids:[str], note}: ask the agency dispatcher to assign one. Agency decides.",
    "offer_slots": "args {}: after agency assigned AND technician accepted, load that technician's slots for the household to choose.",
    "request_payer_authorization": "args {line_items:[{item, paise}], ceiling_paise}: create a Pine Labs DOC_SIMULATED mandate request. The payer must approve separately.",
    "request_route": "args {}: create a Delhivery Maps DOC_SIMULATED distance request (technician base -> household).",
    "evaluate_ready_gate": "args {}: run the deterministic S5 readiness gate and get each predicate.",
    "escalate_to_human": "args {reason}: hand to agency owner/dispatcher (safety, anger, confusion).",
}


def _facts(cid):
    return db.get_case(cid)["facts"]


def run_tool(cid, name, args):
    args = args or {}
    f = _facts(cid)
    if name == "search_knowledge":
        terms = re.findall(r"\w+", str(args.get("query", "")).lower())
        if not terms:
            return {"chunks": []}
        match = " OR ".join(terms[:12])
        rows = db.q("SELECT chunk_id, source_id, text, provenance FROM kb WHERE kb MATCH ? ORDER BY rank LIMIT 3", (match,))
        return {"store": "RAG (SQLite FTS5)", "chunks": [dict(r) for r in rows]}

    if name == "lookup_machine_kundli":
        r = db.q("SELECT record FROM machines WHERE model=?", (str(args.get("model", "")).upper(),), one=True)
        return {"store": "Machine Kundli", "record": json.loads(r["record"]) if r else None,
                "result": "FOUND" if r else "NO_RECORD (unknown history; do not assume)"}

    if name == "search_mistri_gyan":
        s = str(args.get("symptom", "")).lower()
        out = []
        for r in db.q("SELECT record FROM faults"):
            rec = json.loads(r["record"])
            words = set(re.findall(r"\w+", rec["symptom"].lower()))
            if words & set(re.findall(r"\w+", s)):
                out.append(rec)
        return {"store": "Mistri Gyan", "entries": out}

    if name == "update_case":
        fields = args.get("fields", {}) or {}
        applied, rejected = {}, []
        for k, v in fields.items():
            if k not in MODEL_EDITABLE:
                rejected.append(k)
                continue
            if k in ("brand", "model", "model_confirmed", "warranty_status", "error_code"):
                f["machine"][k] = v
            elif k == "reporter_name":
                f["reporter"]["name"] = v
            elif k == "payer_name":
                f["payer"]["name"] = v
            elif k == "payer_is_reporter":
                f["payer"]["is_reporter"] = v
            elif k == "diagnosis_hypotheses":
                f["diagnosis"]["hypotheses"] = v
            elif k == "diagnosis_source_ids":
                f["diagnosis"]["source_ids"] = v
            else:
                f[k] = v
            applied[k] = v
        db.save_facts(cid, f)
        return {"applied": applied, "rejected_world_facts_only_humans_can_set": rejected}

    if name == "rank_technicians":
        need = " ".join(args.get("skills_needed", [])).lower()
        ranked = []
        for t in seed.TECHS:
            skill_txt = " ".join(t["skills"]).lower()
            match = len(set(re.findall(r"\w+", need)) & set(re.findall(r"\w+", skill_txt)))
            score = match * 10 + t["experience_years_claimed"] - (0 if t["slots"] else 50)
            ranked.append({"tech_id": t["tech_id"], "name": t["pseudonym"], "skills": t["skills"],
                           "earliest_slot": min(t["slots"]) if t["slots"] else None,
                           "score": score, "source_mode": "SYNTHETIC_FIXTURE"})
        ranked.sort(key=lambda r: (-r["score"], r["earliest_slot"] or "9"))
        f["ranked_techs"] = ranked
        db.save_facts(cid, f)
        return {"ranked": ranked, "note": "Circuit ranks; the agency dispatcher assigns."}

    if name == "check_kit":
        model = str(args.get("model", "")).upper()
        hits = [i for i in seed.INVENTORY if model and model in [m.upper() for m in i["compatible_models"]]]
        f["kit"]["sku"] = hits[0]["sku"] if hits else None
        f["kit"]["compatible"] = bool(hits)
        db.save_facts(cid, f)
        return {"compatible_stock": hits, "result": "COMPATIBLE_KIT_IN_FIXTURE" if hits else
                "NO_PROVEN_COMPATIBLE_PART -> inspection visit only",
                "warning": "Fixture stock is not physical custody; technician must confirm kit in bag."}

    if name == "request_agency_assignment":
        ids = args.get("tech_ids", [])
        return {"sent_to": "agency_dispatcher", "candidates": ids,
                "status": "WAITING_FOR_AGENCY_ASSIGNMENT"}

    if name == "offer_slots":
        if not (f["assigned_tech"] and f["tech_accepted"]):
            return {"error": "Not allowed: agency assignment and technician acceptance required first (R07)."}
        t = next(t for t in seed.TECHS if t["tech_id"] == f["assigned_tech"])
        f["slots_offered"] = t["slots"]
        db.save_facts(cid, f)
        return {"slots": t["slots"], "status": "WAITING_FOR_HOUSEHOLD_SLOT_CHOICE"}

    if name == "request_payer_authorization":
        ceiling = int(args.get("ceiling_paise") or 0)
        items = args.get("line_items", [])
        if ceiling <= 0:
            return {"error": "ceiling_paise must be > 0"}
        pid = "PINE-" + uuid.uuid4().hex[:6].upper()
        req = {"endpoint": "Pine Labs UPI Reserve Pay - create mandate (DOC_SIMULATED)",
               "body": {"merchant_reference": f"{cid}-{pid}", "amount": {"value": ceiling, "currency": "INR"},
                        "purpose": "AC repair - approved spending ceiling", "line_items": items,
                        "payer_role": "adult_payer"},
               "note": "Field names must be checked against the Pine Labs doc section before recording."}
        db.x("INSERT INTO pending_sim VALUES(?,?,?,?,?,?,?,?,?)",
             (pid, cid, "PINE_LABS", json.dumps(req), PINE_DOC, "WAITING_FOR_WIZARD", None, db.now(), None))
        f["quote"] = {"line_items": items, "ceiling_paise": ceiling}
        f["pine"] = {"status": "REQUESTED", "pending_id": pid}
        db.save_facts(cid, f)
        return {"pending_id": pid, "request": req, "status": "WAITING: payer approval + Pine response (DOC_SIMULATED)"}

    if name == "request_route":
        if not f["assigned_tech"]:
            return {"error": "No assigned technician yet."}
        rid = "DLV-" + uuid.uuid4().hex[:6].upper()
        req = {"endpoint": "Delhivery Maps Distance Matrix (DOC_SIMULATED)",
               "body": {"origins": [f"{f['assigned_tech']} agency base, Ramagundam (fictional)"],
                        "destinations": [f.get("address_landmark") or "household (landmark pending)"],
                        "mode": "two_wheeler"},
               "note": "Use the documented response shape; Maps does not prove stock or arrival."}
        db.x("INSERT INTO pending_sim VALUES(?,?,?,?,?,?,?,?,?)",
             (rid, cid, "DELHIVERY_MAPS", json.dumps(req), DELHIVERY_DOC, "WAITING_FOR_WIZARD", None, db.now(), None))
        f["route"] = {"status": "REQUESTED", "pending_id": rid}
        db.save_facts(cid, f)
        return {"pending_id": rid, "request": req}

    if name == "evaluate_ready_gate":
        g = ready_gate(f)
        f["gate"] = g
        db.save_facts(cid, f)
        if g["verdict"].startswith("READY"):
            db.set_state(cid, "S5")
        return g

    if name == "escalate_to_human":
        return {"escalated_to": "agency_owner", "reason": args.get("reason")}

    return {"error": f"Unknown tool {name}"}


def ready_gate(f):
    m = f["machine"]
    P = []

    def p(name, ok, source):
        P.append({"predicate": name, "result": "PASS" if ok is True else ("FAIL" if ok is False else "UNKNOWN"),
                  "source": source})

    p("safety_clear", not f.get("hazard"), "household report via agent")
    p("out_of_warranty_confirmed", m["warranty_status"] == "OUT_OF_WARRANTY" or None, "household report (ROLEPLAY)")
    p("symptom_and_model_confirmed", bool(f.get("symptom")) and bool(m.get("model_confirmed")), "household read-back")
    p("agency_assigned", bool(f["assigned_tech"]), "agency actor event (ROLEPLAY)")
    p("technician_accepted", bool(f["tech_accepted"]), "technician actor event (ROLEPLAY)")
    p("slot_chosen_by_household", bool(f["slot_selected"]), "household actor event (ROLEPLAY)")
    p("resident_access_granted", f["resident"]["access_permission"] == "GRANTED", "household actor event (ROLEPLAY)")
    p("kit_compatible", f["kit"]["compatible"], "fixture stock vs confirmed model (SYNTHETIC_FIXTURE)")
    p("kit_in_technician_bag", bool(f["kit"]["custody_ack"]), "technician actor event (ROLEPLAY)")
    p("payer_approved_ceiling", bool(f["payer_approved"]), "payer actor event (ROLEPLAY)")
    p("pine_mandate_active", f["pine"]["status"] == "ACTIVE", "Pine Labs response (DOC_SIMULATED)")
    p("route_feasible", f["route"]["status"] == "RESPONDED", "Delhivery Maps response (DOC_SIMULATED)")
    p("owner_signoff", bool(f["owner_signoff"]), "agency owner actor event (ROLEPLAY, pilot L2)")

    res = {x["predicate"]: x["result"] for x in P}
    missing = [x["predicate"] for x in P if x["result"] != "PASS"]
    if res["safety_clear"] == "FAIL":
        verdict = "ESCALATE_SAFETY"
    elif m["warranty_status"] == "IN_WARRANTY":
        verdict = "OEM_REFERRAL"
    elif not missing:
        verdict = "READY_IN_ROLEPLAY"
    elif missing == ["kit_compatible", "kit_in_technician_bag"] or missing == ["kit_compatible"]:
        verdict = "READY_FOR_INSPECTION_VISIT_IN_ROLEPLAY"
    else:
        verdict = "WAIT"
    return {"verdict": verdict, "predicates": P, "missing": missing,
            "label": "Simulation verdict only. Not a real repair or real payment."}
