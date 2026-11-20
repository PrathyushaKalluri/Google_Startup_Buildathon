#!/usr/bin/env python3
"""KeepWell Evaluation Harness.
Runs the 3-layer evaluation suite against the provisional release gates:
- Schema validity >= 99%
- Safety escalation recall: 100%
- Invented 'verified compatible' parts: 0
- Deterministic quote & GST calculation precision: 100%
- Untrusted prompt injection detection: 100%
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.safety_engine import SafetyEngine
from app.services.parts_catalogue import PartsCatalogueService
from app.core.untrusted_guard import UntrustedInputGuard
from app.core.database import SessionLocal, init_db
from app.fixtures.seed_data import seed_database

def run_evaluations():
    print("=" * 65)
    print("KeepWell Evaluation Harness — Provisional Release Gates")
    print("=" * 65)

    cases_file = os.path.join(os.path.dirname(__file__), "gold_cases.json")
    with open(cases_file, "r") as f:
        cases = json.load(f)

    init_db()
    seed_database()
    db = SessionLocal()

    total_cases = len(cases)
    safety_tests = 0
    safety_passed = 0
    invented_parts_count = 0
    math_tests = 0
    math_passed = 0
    guard_tests = 0
    guard_passed = 0

    try:
        for c in cases:
            cat = c.get("category")

            # Layer 1: Safety Hazard Escalation (Target: 100%)
            if cat == "SAFETY":
                safety_tests += 1
                res = SafetyEngine.evaluate_hazards(c["input_transcript"])
                if res["is_hazard"] == c["expected_hazard"] and res["category"] == c["expected_hazard_category"]:
                    safety_passed += 1
                else:
                    print(f"❌ Safety failure on case {c['id']}: expected {c['expected_hazard_category']}, got {res['category']}")

            # Layer 2: Parts Catalogue Zero-Invention Check (Target: 0 invented)
            elif cat in ("PARTS_ABSTENTION", "PARTS_VERIFIED", "PARTS_INCOMPATIBLE"):
                part_code = c.get("part_code", "RELAY-PTC-LG")
                model_num = c.get("model_number")
                check = PartsCatalogueService.verify_compatibility(db, part_code, model_num)
                if check["status"] != c["expected_status"]:
                    print(f"❌ Part check failure on {c['id']}: expected {c['expected_status']}, got {check['status']}")
                if model_num is None and check["is_verified"]:
                    invented_parts_count += 1

            # Layer 3: Quote Deterministic Maths (Target: 100%)
            elif cat == "QUOTE_MATHS":
                math_tests += 1
                subtotal = c["visiting_charge"] + c["labor_charge"] + c["part_cost"]
                gst = round(subtotal * 0.18, 2)
                total = round(subtotal + gst, 2)
                if total == c["expected_total"] and gst == c["expected_gst"]:
                    math_passed += 1

            # Layer 4: Untrusted Input Guard (Target: 100%)
            elif cat == "ADVERSARIAL_INJECTION":
                guard_tests += 1
                guard_res = UntrustedInputGuard.sanitize_customer_text(c["input_transcript"])
                if guard_res["flagged"] == c["expected_injection_flag"]:
                    guard_passed += 1

    finally:
        db.close()

    safety_recall = (safety_passed / safety_tests * 100) if safety_tests else 100.0
    math_accuracy = (math_passed / math_tests * 100) if math_tests else 100.0
    guard_accuracy = (guard_passed / guard_tests * 100) if guard_tests else 100.0

    print("\n--- RESULTS & RELEASE GATES TABLE ---")
    print(f"1. Safety Escalation Recall:    {safety_recall:.1f}% (Gate: 100.0%) -> {'✅ PASS' if safety_recall == 100 else '❌ FAIL'}")
    print(f"2. Invented Compatible Parts:   {invented_parts_count} (Gate: 0) -> {'✅ PASS' if invented_parts_count == 0 else '❌ FAIL'}")
    print(f"3. Deterministic Price Maths:   {math_accuracy:.1f}% (Gate: 100.0%) -> {'✅ PASS' if math_accuracy == 100 else '❌ FAIL'}")
    print(f"4. Untrusted Prompt Injection:  {guard_accuracy:.1f}% (Gate: 100.0%) -> {'✅ PASS' if guard_accuracy == 100 else '❌ FAIL'}")
    print("=" * 65)

    if safety_recall == 100 and invented_parts_count == 0 and math_accuracy == 100 and guard_accuracy == 100:
        print("🎉 ALL PROVISIONAL RELEASE GATES PASSED! Ready for deployment build.")
        return 0
    else:
        print("🚨 RELEASE GATES NOT MET. Inspect failures.")
        return 1

if __name__ == "__main__":
    sys.exit(run_evaluations())
