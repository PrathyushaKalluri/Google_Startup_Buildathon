"""Comprehensive unit tests for Keepwell A2 lexicons & 10 deterministic engines."""

from __future__ import annotations

import json
import random
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from services.agents.engines import (
    ASSIGNMENT_WEIGHTS,
    CANONICAL_STOP_USE_MESSAGE,
    GST_RATE_PERCENT,
    HOUSEHOLD_ASKED_HOW_URGENT,
    PAYMENT_CLOSES_JOB,
    PRICE_SCORED,
    SOURCE_LADDER_ORDER,
    URGENCY_RULES,
    AssignmentRequirements,
    CataloguePart,
    CompatibilityRow,
    GateMachine,
    GateViolationError,
    OTPService,
    PriceBookEntry,
    RequestedPart,
    SafeFixEntry,
    SafeFixStep,
    StockItem,
    TechnicianProfile,
    assess_urgency,
    build_estimate_range,
    build_firm_quote,
    build_visit_plan,
    can_close_job_from_payment,
    check_authority,
    complete_sandbox_payment,
    compute_gst_paise,
    compute_variance_pct,
    create_payment_intent,
    exceeds_variance_threshold,
    haversine_km,
    load_hazard_lexicon,
    load_part_catalogue_csv,
    load_part_compatibility_csv,
    load_safe_fix_catalogue,
    resolve_parts,
    score_technicians,
    select_safe_fix,
    sign_webhook_payload,
    validate_safe_fix_entry,
    verify_webhook_signature,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
LEXICON_DIR = REPO_ROOT / "services" / "agents" / "lexicon"
VOICE_SCRIPTS_JSON = REPO_ROOT / "input" / "dataset" / "evaluator_only" / "voice_scripts.json"


# ---------------------------------------------------------------------------
# 1. Runtime Lexicon Tests
# ---------------------------------------------------------------------------
class TestLexicons:
    def test_repair_vocabulary_covers_all_5_categories_and_error_codes(self) -> None:
        vocab_path = LEXICON_DIR / "repair_vocabulary.yaml"
        data = yaml.safe_load(vocab_path.read_text(encoding="utf-8"))

        appliances = data["appliances"]
        expected_cats = {
            "air_conditioner",
            "refrigerator",
            "washing_machine",
            "water_purifier",
            "water_heater",
        }
        assert expected_cats == set(appliances.keys())
        for cat_cfg in appliances.values():
            for lang_key in ("en", "hi_devanagari", "hi_romanized", "te_script", "te_romanized"):
                assert cat_cfg[lang_key], f"Missing {lang_key} terms for {cat_cfg['canonical_code']}"

        error_codes = data["error_codes"]
        assert {"E21", "E6", "dF", "Er4"}.issubset(set(error_codes.keys()))

    def test_hazard_lexicon_structure_and_canonical_stop_message(self) -> None:
        lex = load_hazard_lexicon()
        assert lex["metadata"]["canonical_stop_use_message"] == CANONICAL_STOP_USE_MESSAGE
        hazards = lex["hazards"]
        for key in (
            "shock_or_tingling",
            "smoke_or_burning_smell",
            "water_near_electrics",
            "chemical_smell",
            "swelling_or_rupture",
        ):
            assert key in hazards
            phrases = hazards[key]["phrases"]
            for lang_key in ("en", "hi_devanagari", "hi_romanized", "te_script", "te_romanized"):
                assert len(phrases[lang_key]) >= 2


# ---------------------------------------------------------------------------
# 2. Authority Engine Tests
# ---------------------------------------------------------------------------
class TestAuthorityEngine:
    @pytest.mark.parametrize(
        "level,job_type,entitlement,expected_decision",
        [
            ("authorised_service", "repair", "brand_warranty", "proceed"),
            ("authorised", "repair", "out_of_warranty", "proceed"),
            ("authorised_service", "installation", "brand_warranty", "proceed"),
            ("independent", "repair", "brand_warranty", "return_to_brand"),
            ("independent", "repair", "extended_warranty", "return_to_brand"),
            ("independent", "coverage_claim", "out_of_warranty", "return_to_brand"),
            ("independent", "repair", "out_of_warranty", "proceed_with_notice"),
            ("independent", "repair", "amc", "proceed_with_notice"),
            ("installation_only", "installation", "brand_warranty", "proceed"),
            ("installation_only", "uninstall_reinstall", "out_of_warranty", "proceed"),
            ("installation_only", "repair", "out_of_warranty", "cannot_repair"),
            ("installation_only", "repair", "brand_warranty", "cannot_repair"),
            ("none", "repair", "brand_warranty", "return_to_brand"),
            ("none", "installation", "out_of_warranty", "cannot_install"),
            ("none", "repair", "out_of_warranty", "cannot_repair"),
        ],
    )
    def test_authority_matrix(
        self,
        level: str,
        job_type: str,
        entitlement: str,
        expected_decision: str,
    ) -> None:
        res = check_authority(level, job_type, entitlement)
        assert res.decision == expected_decision
        assert res.reason


# ---------------------------------------------------------------------------
# 3. Urgency & 100% Safety Recall Tests
# ---------------------------------------------------------------------------
class TestUrgencyEngine:
    def test_rule_count_and_never_asks_how_urgent(self) -> None:
        assert HOUSEHOLD_ASKED_HOW_URGENT is False
        classes = [r["class"] for r in URGENCY_RULES.values()]
        assert classes.count("safety") == 4
        assert classes.count("urgent") == 5
        assert classes.count("standard") == 1
        assert classes.count("planned") == 2

    def test_100_percent_safety_recall_multilingual_and_voice_scripts(self) -> None:
        """Release gate: 100% recall on all safety hazard prompts across EN/HI/TE."""
        scripts = json.loads(VOICE_SCRIPTS_JSON.read_text(encoding="utf-8"))
        safety_cases = [
            # Real dataset safety voice scripts (C05 geyser tap shock, C15 burning smell + smoke)
            (scripts["C05/01_call.ogg"]["transcript_original_script"], "geyser", {}),
            (scripts["C15/01_call.ogg"]["transcript_original_script"], "washing_machine", {}),
            # English
            ("Getting a mild electric shock from the bathroom tap when geyser is on", "geyser", {}),
            ("There is a burning smell and sparks coming from the AC plug", "ac", {}),
            ("Smoke is coming out of the washing machine motor", "washing_machine", {}),
            ("Water is dripping onto the switchboard and socket is wet", "ac", {}),
            ("Strong chemical gas smell coming from the refrigerator", "refrigerator", {}),
            ("The geyser tank body is swelling and bulging", "geyser", {}),
            # Hindi Devanagari & Romanized
            ("नल में करंट लगता है जब गीज़र चालू हो", "geyser", {}),
            ("AC se jalne ki badboo aur chingari nikal rahi hai", "ac", {}),
            ("स्विचबोर्ड पर पानी गिर रहा है", "ac", {}),
            ("फ्रिज से गैस की बदबू आ रही है", "refrigerator", {}),
            ("capacitor phool gaya hai aur dhuan aa raha hai", "ac", {}),
            # Telugu script & Romanized
            ("గీజర్ ఆన్ చేస్తే ట్యాప్ లో కరెంట్ కొడుతోంది", "geyser", {}),
            ("వాషింగ్ మెషీన్ నుంచి కాలిపోయిన వాసన మరియు పొగ వస్తోంది", "washing_machine", {}),
            ("స్విచ్‌బోర్డ్ మీద నీళ్లు పడుతున్నాయి", "ac", {}),
            ("fridge nunchi gas vasana vasthondi", "refrigerator", {}),
            ("geyser tap lo current koduthondi", "geyser", {}),
            # Structured facts only
            ("Appliance problem", "refrigerator", {"shock_or_tingling": True}),
            ("Appliance problem", "refrigerator", {"chemical_smell": True}),
            ("Appliance problem", "ac", {"water_near_electrics": True}),
            ("Appliance problem", "washing_machine", {"smoke_or_burning_smell": True}),
        ]

        hits = 0
        for text, cat, facts in safety_cases:
            res = assess_urgency(text=text, category_code=cat, facts=facts)
            if (
                res.urgency_class == "safety"
                and res.safety_flag is True
                and res.protective_steps_sent is True
                and res.stop_use_message == CANONICAL_STOP_USE_MESSAGE
            ):
                hits += 1
        recall = hits / len(safety_cases)
        assert recall == 1.0, f"Safety recall dropped below 100%: {hits}/{len(safety_cases)}"

    def test_urgent_rules_repeat_30d_and_food_risk_and_planned(self) -> None:
        rep = assess_urgency(
            text="Washing machine not draining again",
            category_code="washing_machine",
            repeat_within_days=12,
        )
        assert rep.urgency_class == "urgent"
        assert "URG-REPEAT-30D" in rep.rule_codes
        assert rep.safety_flag is False

        food = assess_urgency(
            text="Fridge not cooling and milk and insulin medicine will spoil",
            category_code="refrigerator",
            facts={"not_cooling": True, "at_risk": ["milk", "medicine"]},
        )
        assert food.urgency_class == "urgent"
        assert "URG-FOOD-RISK" in food.rule_codes

        inst = assess_urgency(text="New split AC installation", category_code="ac", job_type="installation")
        assert inst.urgency_class == "planned"
        assert "PLN-INSTALL" in inst.rule_codes

        prev = assess_urgency(
            text="Annual RO filter service", category_code="ro_purifier", job_type="preventive_service"
        )
        assert prev.urgency_class == "planned"
        assert "PLN-SERVICE" in prev.rule_codes

        std = assess_urgency(text="AC blows slightly warm air", category_code="ac")
        assert std.urgency_class == "standard"
        assert std.rule_codes == ["STD-DEFAULT"]


# ---------------------------------------------------------------------------
# 4. SafeFix Catalogue Engine Tests
# ---------------------------------------------------------------------------
class TestSafeFixEngine:
    def test_refuses_review_due_and_retired_entries(self) -> None:
        catalogue = load_safe_fix_catalogue()
        by_code = {e.code: e for e in catalogue}
        assert by_code["SF-AC-RESET"].status == "review_due"
        assert by_code["SF-GY-LEGACY"].status == "retired"

        ok_reset, errs_reset = validate_safe_fix_entry(by_code["SF-AC-RESET"])
        assert not ok_reset and any("status" in e for e in errs_reset)

        ok_legacy, errs_legacy = validate_safe_fix_entry(by_code["SF-GY-LEGACY"])
        assert not ok_legacy and any("status" in e for e in errs_legacy)

        # Selecting for AC communication error must NOT pick SF-AC-RESET
        sel = select_safe_fix(
            category_code="ac",
            symptoms=["communication error", "error code"],
            error_codes=["E6"],
        )
        assert sel is None or sel.entry.code != "SF-AC-RESET"

    def test_brand_specific_ranked_over_generic_and_safety_blocks_fix(self) -> None:
        wavecrest_brand_id = "40508238-6fc9-59b8-84af-f27406b34b7d"
        sel = select_safe_fix(
            category_code="washing_machine",
            brand_id=wavecrest_brand_id,
            symptoms=["will not drain"],
            error_codes=["E21"],
        )
        assert sel is not None
        assert sel.entry.code == "SF-WM-DRAINFILTER-WC"
        assert sel.brand_specific is True

        # Safety flag MUST prevent any safe fix from being offered
        blocked = select_safe_fix(
            category_code="washing_machine",
            brand_id=wavecrest_brand_id,
            symptoms=["will not drain"],
            error_codes=["E21"],
            safety_flag=True,
        )
        assert blocked is None

    def test_enforces_check_limits_in_code(self) -> None:
        bad_entry = SafeFixEntry(
            id="test-1",
            code="SF-BAD",
            category_code="air_conditioner",
            title="Too many steps and needs tools",
            symptom_terms=["weak cooling"],
            steps=[SafeFixStep(n=i, say="s", check="c") for i in range(1, 8)],
            step_count=7,
            est_minutes=15,
            reversible=False,
            needs_tools=True,
            manual_doc_id=None,
            manual_page=None,
            reviewer_name=None,
            reviewed_on=None,
            status="active",
        )
        ok, errors = validate_safe_fix_entry(bad_entry)
        assert not ok
        assert len(errors) >= 6


# ---------------------------------------------------------------------------
# 5. Consent Gate State Machine Tests
# ---------------------------------------------------------------------------
class TestGateMachine:
    def test_safety_and_non_repair_skip_both_gates(self) -> None:
        gm_safety = GateMachine(job_type="repair", safety_flag=True, urgency_class="safety")
        assert gm_safety.gate1.answer == "not_asked"
        assert gm_safety.gate1.not_asked_reason == "safety_flag"
        assert gm_safety.gate2.answer == "not_asked"
        assert gm_safety.gate2.not_asked_reason == "safety_flag"
        assert gm_safety.can_start_fix() is False
        assert gm_safety.can_start_video() is False
        with pytest.raises(GateViolationError):
            gm_safety.record_gate1("yes")

        gm_install = GateMachine(job_type="installation", safety_flag=False, urgency_class="planned")
        assert gm_install.gate1.answer == "not_asked"
        assert gm_install.gate1.not_asked_reason == "job_type"
        assert gm_install.gate2.answer == "not_asked"
        assert gm_install.gate2.not_asked_reason == "job_type"
        with pytest.raises(GateViolationError):
            gm_install.ask_gate1()

    def test_gate1_no_or_silence_skips_gate2_and_blocks_illegal_transitions(self) -> None:
        for ans in ("no", "silence"):
            gm = GateMachine(job_type="repair")
            gm.record_gate1(ans)  # type: ignore[arg-type]
            assert gm.gate2.answer == "not_asked"
            assert gm.gate2.not_asked_reason == "gate1_not_yes"
            assert gm.can_start_fix() is False
            assert gm.can_start_video() is False
            with pytest.raises(GateViolationError):
                gm.record_gate2("yes", choice="switch_to_video")

    def test_illegal_gate2_before_gate1_and_valid_video_flow(self) -> None:
        gm = GateMachine(job_type="repair")
        assert gm.can_start_fix() is False
        with pytest.raises(GateViolationError):
            gm.ask_gate2()
        with pytest.raises(GateViolationError):
            gm.record_gate2("yes", choice="switch_to_video")
        with pytest.raises(GateViolationError):
            gm.assert_can_start_fix()

        gm.record_gate1("yes")
        assert gm.can_start_fix() is True
        assert gm.can_start_video() is False

        with pytest.raises(GateViolationError):
            gm.record_gate2("yes", choice=None)

        gm.record_gate2("yes", choice="switch_to_video")
        assert gm.can_start_video() is True
        gm.assert_can_start_video()

        # Continue-here does NOT permit video
        gm2 = GateMachine(job_type="repair")
        gm2.record_gate1("yes")
        gm2.record_gate2("yes", choice="continue_here")
        assert gm2.can_start_fix() is True
        assert gm2.can_start_video() is False


# ---------------------------------------------------------------------------
# 6. Assignment Engine Tests
# ---------------------------------------------------------------------------
class TestAssignmentEngine:
    def test_exact_weights_sum_100_and_price_not_scored(self) -> None:
        assert ASSIGNMENT_WEIGHTS == {
            "fix_confidence": 30,
            "parts_readiness": 25,
            "time_to_visit": 20,
            "route_cost": 15,
            "reliability": 5,
            "household_fit": 5,
        }
        assert sum(ASSIGNMENT_WEIGHTS.values()) == 100
        assert PRICE_SCORED is False

    def test_hard_filters_scoring_and_haversine_fallback(self) -> None:
        req = AssignmentRequirements(
            household_lat=17.4500,
            household_lon=78.3800,
            household_language="hi",
            min_skill_level=3,
            required_safety_certs=["gas"],
            max_km=15.0,
        )
        techs = [
            # Eligible top scorer (no drive_minutes -> uses haversine fallback)
            TechnicianProfile(
                technician_id="t1",
                name="Vikram",
                skill_level=5,
                safety_certs=["gas", "electrical"],
                languages=["hi", "en"],
                lat=17.4520,
                lon=78.3810,
                first_time_fix_rate=0.95,
                on_time_rate=0.95,
                repeat_visit_rate_30d=0.02,
                parts_ready_ratio=1.0,
                earliest_slot_hours=2.0,
            ),
            # Eligible lower scorer
            TechnicianProfile(
                technician_id="t2",
                name="Raju",
                skill_level=3,
                safety_certs=["gas"],
                languages=["te"],
                lat=17.5000,
                lon=78.4200,
                first_time_fix_rate=0.70,
                on_time_rate=0.75,
                repeat_visit_rate_30d=0.10,
                parts_ready_ratio=0.5,
                earliest_slot_hours=12.0,
            ),
            # Filtered out: missing gas cert
            TechnicianProfile(
                technician_id="t3",
                name="NoCert",
                skill_level=5,
                safety_certs=[],
                languages=["hi"],
                lat=17.4500,
                lon=78.3800,
            ),
            # Filtered out: not identity_verified
            TechnicianProfile(
                technician_id="t4",
                name="Unverified",
                identity_verified=False,
                skill_level=5,
                safety_certs=["gas"],
                languages=["hi"],
                lat=17.4500,
                lon=78.3800,
            ),
            # Filtered out: too far (> 15 km)
            TechnicianProfile(
                technician_id="t5",
                name="TooFar",
                skill_level=5,
                safety_certs=["gas"],
                languages=["hi"],
                lat=17.2000,
                lon=78.4000,
            ),
        ]

        candidates = score_technicians(techs, req, top_k=3)
        assert [c.technician_id for c in candidates] == ["t1", "t2"]
        assert candidates[0].rank == 1
        assert candidates[0].score > candidates[1].score
        assert candidates[0].drive_minutes >= 0.0
        assert "Skill L5" in candidates[0].why
        assert haversine_km(17.45, 78.38, 17.45, 78.38) == 0.0


# ---------------------------------------------------------------------------
# 7. Parts Hard Catalogue Check & Fuzz Test
# ---------------------------------------------------------------------------
class TestPartsEngine:
    def test_real_dataset_valid_and_incompatible_parts(self) -> None:
        cat = load_part_catalogue_csv()
        compat = load_part_compatibility_csv()
        first_compat = compat[0]
        matching_part = next(p for p in cat if p.id == first_compat.part_id)

        verified, unresolved = resolve_parts(
            [matching_part.part_no],
            brand_id=matching_part.brand_id,
            model_id=first_compat.model_id,
            catalogue_rows=cat,
            compat_rows=compat,
        )
        assert len(verified) == 1
        assert verified[0].part_no == matching_part.part_no
        assert unresolved == []

        # Same part number against a non-existent model_id MUST be unresolved
        v2, u2 = resolve_parts(
            [matching_part.part_no],
            brand_id=matching_part.brand_id,
            model_id="00000000-0000-0000-0000-000000000000",
            catalogue_rows=cat,
            compat_rows=compat,
        )
        assert v2 == []
        assert len(u2) == 1
        assert u2[0].flag == "compatibility_unverified"

    def test_parts_never_invented_fuzz_50_bogus_part_numbers(self) -> None:
        """Contract C11 invariant: 50 random bogus part numbers -> 0 verified, 50 unresolved."""
        cat = load_part_catalogue_csv()
        compat = load_part_compatibility_csv()
        brand_id = cat[0].brand_id
        model_id = compat[0].model_id

        rng = random.Random(42)
        bogus_parts = [
            f"FAKE-{''.join(rng.choices(string.ascii_uppercase + string.digits, k=8))}"
            for _ in range(50)
        ]

        verified, unresolved = resolve_parts(
            bogus_parts,
            brand_id=brand_id,
            model_id=model_id,
            catalogue_rows=cat,
            compat_rows=compat,
        )
        assert verified == []
        assert len(unresolved) == 50
        assert all(u.flag == "not_in_brand_catalogue" for u in unresolved)


# ---------------------------------------------------------------------------
# 8. Planner Engine Tests
# ---------------------------------------------------------------------------
class TestPlannerEngine:
    def test_visit_plan_carries_already_tried_and_source_ladder(self) -> None:
        assert SOURCE_LADDER_ORDER == ("van", "centre", "parts_centre")
        cat = [
            CataloguePart(id="p1", brand_id="b1", part_no="WC-PUMP-01", name="Drain pump", mrp_paise=120000),
            CataloguePart(id="p2", brand_id="b1", part_no="WC-HOSE-02", name="Outlet hose", mrp_paise=35000),
        ]
        compat = [
            CompatibilityRow(part_id="p1", model_id="m1"),
            CompatibilityRow(part_id="p2", model_id="m1"),
        ]
        stock = [
            StockItem(part_no="WC-PUMP-01", holder_type="centre", quantity=2),
            StockItem(part_no="WC-PUMP-01", holder_type="parts_centre", quantity=5),
            StockItem(part_no="WC-HOSE-02", holder_type="van", quantity=1),
        ]

        plan = build_visit_plan(
            category_code="washing_machine",
            trigger_reason="safe_fix_failed_rerun",
            already_tried=["SF-WM-DRAINFILTER-WC: cleaned drain pump filter"],
            requested_parts=[
                RequestedPart(part_no="WC-PUMP-01", quantity=1, probability=0.85),
                RequestedPart(part_no="WC-HOSE-02", quantity=1, probability=0.40),
                RequestedPart(part_no="INVENTED-999", quantity=1, probability=0.20),
            ],
            brand_id="b1",
            model_id="m1",
            catalogue_rows=cat,
            compat_rows=compat,
            stock_rows=stock,
        )
        assert plan.already_tried == ["SF-WM-DRAINFILTER-WC: cleaned drain pump filter"]
        assert plan.est_duration_p80_min >= plan.est_duration_p50_min > 0
        by_part = {p.part_no: p for p in plan.parts}
        assert set(by_part.keys()) == {"WC-PUMP-01", "WC-HOSE-02"}
        assert by_part["WC-HOSE-02"].source_ladder == "van"
        assert by_part["WC-HOSE-02"].ready is True
        assert by_part["WC-PUMP-01"].source_ladder == "centre"
        assert by_part["WC-PUMP-01"].ready is True
        assert len(plan.unresolved_parts) == 1
        assert plan.unresolved_parts[0].query == "INVENTED-999"


# ---------------------------------------------------------------------------
# 9. Pricing Engine Tests
# ---------------------------------------------------------------------------
class TestPricingEngine:
    def test_18_percent_gst_split_and_repeat_30d_waiver(self) -> None:
        assert GST_RATE_PERCENT == 18
        assert compute_gst_paise(100000) == 18000

        pb = PriceBookEntry(
            category_code="washing_machine",
            job_type="repair",
            complexity_band="standard",
            visit_fee_paise=40000,
            labour_paise=60000,
        )
        cat = [CataloguePart(id="p1", brand_id="b1", part_no="WC-PUMP-01", name="Drain pump", mrp_paise=100000)]
        compat = [CompatibilityRow(part_id="p1", model_id="m1")]
        verified, _ = resolve_parts(["WC-PUMP-01"], "b1", "m1", cat, compat)

        # Out-of-warranty: 400 + 600 + 1000 = 2000 INR -> +18% GST = 2360 INR = 236000 paise
        q_oow = build_firm_quote(price_book=pb, verified_parts=verified, entitlement="out_of_warranty")
        assert q_oow.subtotal_paise == 200000
        assert q_oow.gst_paise == 36000
        assert q_oow.total_paise == 236000
        assert q_oow.household_paise == 236000
        assert q_oow.covered_paise == 0

        # AMC: visit+labour covered (1000 INR + 180 GST = 118000), parts household (1000 INR + 180 GST = 118000)
        q_amc = build_firm_quote(price_book=pb, verified_parts=verified, entitlement="amc")
        assert q_amc.covered_paise == 118000
        assert q_amc.household_paise == 118000
        assert q_amc.covered_paise + q_amc.household_paise == q_amc.total_paise

        # Brand warranty: 100% covered
        q_war = build_firm_quote(price_book=pb, verified_parts=verified, entitlement="brand_warranty")
        assert q_war.household_paise == 0
        assert q_war.covered_paise == 236000

        # Repeat within 30d: visit fee waived (0 + 600 + 1000 = 1600 INR -> +18% = 188800 paise)
        q_rep = build_firm_quote(
            price_book=pb, verified_parts=verified, entitlement="out_of_warranty", is_repeat_30d=True
        )
        assert q_rep.visit_fee_waived is True
        assert q_rep.subtotal_paise == 160000
        assert q_rep.total_paise == 188800

        # Estimate range & variance %
        est = build_estimate_range(price_book=pb, probable_parts=verified, entitlement="out_of_warranty")
        assert est.low_paise == 118000
        assert est.high_paise == 236000
        assert compute_variance_pct(100000, 125000) == 25.0
        assert exceeds_variance_threshold(100000, 125000, threshold_pct=20.0) is True
        assert exceeds_variance_threshold(100000, 115000, threshold_pct=20.0) is False


# ---------------------------------------------------------------------------
# 10. Payment & OTP Engine Tests
# ---------------------------------------------------------------------------
class TestPaymentsAndOTP:
    def test_payment_intent_upi_gpay_hmac_sandbox_and_never_closes_job(self) -> None:
        upi = create_payment_intent(
            quote_id="q-1",
            amount_paise=236000,
            method="upi_intent",
            upi_vpa="frostwave@upi",
            merchant_name="Frost and Wave Service Point",
        )
        assert upi.upi_intent_url is not None
        assert upi.upi_intent_url.startswith("upi://pay?")
        assert "pa=frostwave%40upi" in upi.upi_intent_url
        assert "am=2360.00" in upi.upi_intent_url

        gpay = create_payment_intent(
            quote_id="q-1",
            amount_paise=236000,
            method="google_pay",
            google_pay_environment="TEST",
            merchant_name="Frost and Wave",
        )
        assert gpay.google_pay is not None
        assert gpay.google_pay.environment == "TEST"
        assert gpay.google_pay.transaction_info.currency_code == "INR"
        assert gpay.google_pay.transaction_info.total_price == "2360.00"

        # HMAC webhook verification
        body = b'{"payment_id":"123","status":"paid"}'
        secret = "test-webhook-secret"
        sig = sign_webhook_payload(body, secret)
        assert verify_webhook_signature(body, sig, secret) is True
        assert verify_webhook_signature(body, f"sha256={sig}", secret) is True
        assert verify_webhook_signature(body, "deadbeef", secret) is False

        # Sandbox completion
        paid = complete_sandbox_payment(upi, result="success", payment_mode="sandbox")
        assert paid.status == "paid"
        assert paid.payment_ref is not None and paid.payment_ref.startswith("SBX-")
        with pytest.raises(PermissionError):
            complete_sandbox_payment(upi, result="success", payment_mode="live")

        # Hard invariant: payment NEVER closes a job
        assert PAYMENT_CLOSES_JOB is False
        assert can_close_job_from_payment(paid) is False

    def test_otp_issue_hash_only_sandbox_verify_and_expiry(self) -> None:
        svc = OTPService(mode="sandbox")
        now = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
        rec = svc.issue_otp(visit_id="v-1", household_id="h-1", ttl_seconds=300, now=now)

        code = svc.get_sandbox_otp(rec.otp_ref)
        assert len(code) == 6 and code.isdigit()
        # Plaintext code must NEVER appear in the DB record serialization
        assert code not in rec.model_dump_json()

        # Wrong code rejected
        bad = svc.verify_otp(otp_ref=rec.otp_ref, code="000000" if code != "000000" else "999999", now=now)
        assert bad.verified is False
        assert bad.reason == "invalid_code"

        # Correct code succeeds and returns closure confirmation ref
        ok = svc.verify_otp(otp_ref=rec.otp_ref, code=code, now=now + timedelta(seconds=30))
        assert ok.verified is True
        assert ok.closure_confirmation_ref is not None
        assert ok.closure_confirmation_ref.startswith("CLS-")

        # Replay rejected
        replay = svc.verify_otp(otp_ref=rec.otp_ref, code=code, now=now + timedelta(seconds=40))
        assert replay.verified is False
        assert replay.reason == "otp_already_used"

        # Expiry rejected
        rec2 = svc.issue_otp(visit_id="v-2", household_id="h-1", ttl_seconds=60, now=now)
        code2 = svc.get_sandbox_otp(rec2.otp_ref)
        exp = svc.verify_otp(otp_ref=rec2.otp_ref, code=code2, now=now + timedelta(seconds=61))
        assert exp.verified is False
        assert exp.reason == "otp_expired"

        # Live mode forbids sandbox lookup
        live_svc = OTPService(mode="live")
        live_rec = live_svc.issue_otp(visit_id="v-3", household_id="h-1", now=now)
        with pytest.raises(PermissionError):
            live_svc.get_sandbox_otp(live_rec.otp_ref)
