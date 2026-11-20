"""Loads fictional agency fixtures and the knowledge stores (Machine Kundli, Mistri Gyan, RAG)."""
import json
import re
from . import db

FIXTURE = json.loads((db.ROOT / "data" / "seed_demo_fixtures.json").read_text())
AGENCY = FIXTURE["agency"]
TECHS = FIXTURE["technicians"]
INVENTORY = FIXTURE["inventory"]
PRICES = FIXTURE["pricing_assumptions_not_market_facts"]

# Machine Kundli prototype: one SYNTHETIC per-machine record (fourth rail, imagined capability #1).
KUNDLI = {
    "DEMO-AC-MODEL-A": {
        "model": "DEMO-AC-MODEL-A", "appliance": "AC (split, non-inverter)",
        "install_year": 2023, "warranty_status_on_file": "EXPIRED (fixture claim)",
        "prior_events": [{"date": "2025-04-12", "work": "general service + filter clean",
                          "outcome": "household reported OK"}],
        "consent_ref": None, "source_mode": "SYNTHETIC_FIXTURE",
        "note": "Prototype record. No real shared cross-agency Kundli rail exists today.",
    }
}

# Mistri Gyan prototype: reviewed fault library entries (imagined capability #2). Generic, no SKU claims.
FAULTS = [
    {"fault_id": "MG-AC-001", "symptom": "AC running but not cooling / weak cooling",
     "household_safe_checks": ["Is it set to Cool mode?", "Is set temperature below room temperature?",
                               "Is airflow from the indoor unit weak?", "Any error code on display?"],
     "likely_causes": ["clogged air filter", "wrong mode/settings", "low supply voltage",
                       "refrigerant or component issue (technician inspection only)"],
     "technician_test": "Visual filter check, supply voltage check, gas pressure check by qualified tech",
     "kit_if_confirmed": "CLEANING-KIT-DEMO (only for filter/coil cleaning hypothesis)",
     "review_status": "SYNTHETIC_FIXTURE_NOT_FIELD_REVIEWED"},
    {"fault_id": "MG-AC-002", "symptom": "Burning smell, sparks, smoke",
     "household_safe_checks": ["Switch off at the mains if safe", "Leave the room"],
     "likely_causes": ["electrical fault"], "technician_test": "Qualified electrical inspection",
     "kit_if_confirmed": None, "review_status": "SAFETY_RULE", "escalate": True},
    {"fault_id": "MG-AC-003", "symptom": "Water dripping from indoor unit",
     "household_safe_checks": ["Is water dripping inside the room?", "How long has it been dripping?"],
     "likely_causes": ["blocked drain pipe", "dirty filter causing icing"],
     "technician_test": "Drain line check", "kit_if_confirmed": "CLEANING-KIT-DEMO",
     "review_status": "SYNTHETIC_FIXTURE_NOT_FIELD_REVIEWED"},
]


def ingest_knowledge():
    """Index every .md/.txt in knowledge/ into FTS5, paragraph-chunked.
    A file may start with lines like `source_id: X` / `url: ...` / `provenance: ...`."""
    db.x("DELETE FROM kb")
    n = 0
    for f in sorted((db.ROOT / "knowledge").glob("*")):
        if f.suffix not in (".md", ".txt") or f.name.upper().startswith("README"):
            continue
        text = f.read_text()
        meta = dict(re.findall(r"^(source_id|url|provenance):\s*(.+)$", text, re.M))
        sid = meta.get("source_id", f.stem.upper())
        prov = meta.get("provenance", "SECONDARY_SOURCE" if meta.get("url") else "SYNTHESIZED_GENERIC_GUIDANCE")
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 60]
        for i, p in enumerate(paras):
            db.x("INSERT INTO kb VALUES(?,?,?,?,?)", (f"{sid}#{i}", sid, f.stem, p, prov))
            n += 1
    return n


def seed_all():
    for m, rec in KUNDLI.items():
        db.x("INSERT OR REPLACE INTO machines VALUES(?,?)", (m, json.dumps(rec)))
    for fa in FAULTS:
        db.x("INSERT OR REPLACE INTO faults VALUES(?,?)", (fa["fault_id"], json.dumps(fa)))
    return ingest_knowledge()


def new_case_facts():
    return {
        "reporter": {"name": None}, "resident": {"access_permission": "UNKNOWN"},
        "payer": {"name": None, "is_reporter": "UNKNOWN"},
        "machine": {"brand": None, "model": None, "model_confirmed": False,
                    "warranty_status": "UNKNOWN", "error_code": None},
        "symptom": None, "hazard": False, "address_landmark": None,
        "diagnosis": {"hypotheses": [], "source_ids": []},
        "ranked_techs": [], "assigned_tech": None, "tech_accepted": False,
        "slots_offered": [], "slot_selected": None,
        "quote": None, "payer_approved": False, "payer_approved_ceiling_paise": None,
        "pine": {"status": "NOT_REQUESTED", "pending_id": None},
        "kit": {"sku": None, "compatible": None, "custody_ack": False},
        "route": {"status": "NOT_REQUESTED", "pending_id": None},
        "owner_signoff": False, "gate": None,
        "gnani_calls": 0, "questions_asked": 0,
    }
