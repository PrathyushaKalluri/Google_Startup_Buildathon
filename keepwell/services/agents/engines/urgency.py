"""Deterministic urgency & safety assessment engine (A2).

Loads `services/agents/lexicon/hazard_lexicon.yaml` and implements the 12
urgency rules from `input/dataset/csv/urgency_rule.csv` (4 safety, 5 urgent,
1 standard, 2 planned).

Invariant (Contract C0 & C11):
- The household is NEVER asked "how urgent is it?".
- Any safety trigger ALWAYS classifies as `safety`, sets `safety_flag=True`,
  `protective_steps_sent=True`, and emits the canonical stop-use message.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

UrgencyClass = Literal["safety", "urgent", "standard", "planned"]

HOUSEHOLD_ASKED_HOW_URGENT: bool = False

FACT_QUESTIONS: tuple[str, str, str] = (
    "Does this affect food, water, or someone's health right now?",
    "Can the appliance be used at all right now?",
    "How long has it been like this?",
)

CANONICAL_STOP_USE_MESSAGE: str = (
    "Please stop using it and switch it off at the wall. "
    "A technician will come as soon as possible."
)

_CATEGORY_ALIASES: dict[str, str] = {
    "ac": "air_conditioner",
    "split_ac": "air_conditioner",
    "air_conditioner": "air_conditioner",
    "fridge": "refrigerator",
    "refrigerator": "refrigerator",
    "wm": "washing_machine",
    "washer": "washing_machine",
    "washing_machine": "washing_machine",
    "ro": "water_purifier",
    "ro_purifier": "water_purifier",
    "water_purifier": "water_purifier",
    "geyser": "water_heater",
    "water_heater": "water_heater",
}

_LEXICON_PATH = Path(__file__).resolve().parent.parent / "lexicon" / "hazard_lexicon.yaml"

# The 12 canonical rules from input/dataset/csv/urgency_rule.csv
URGENCY_RULES: dict[str, dict[str, Any]] = {
    "SAF-SHOCK": {
        "class": "safety",
        "category_code": None,
        "description": "Any shock or tingling from the appliance, a tap or a body panel",
        "protective_message": (
            "Please keep the appliance and its MCB switched off, do not touch it or "
            "any tap connected to it, and keep children away. We are arranging a technician."
        ),
    },
    "SAF-SMOKE-BURN": {
        "class": "safety",
        "category_code": None,
        "description": "Smoke, sparks, melting or a burning smell",
        "protective_message": (
            "Please unplug it or switch it off at the MCB if you can do so without "
            "touching it, keep away from it and open a window."
        ),
    },
    "SAF-WATER-ELEC": {
        "class": "safety",
        "category_code": None,
        "description": "Water running onto a switchboard, socket or the appliance's electrics",
        "protective_message": (
            "Please switch off the MCB for that circuit and keep away from the wet area."
        ),
    },
    "SAF-GAS-SMELL": {
        "class": "safety",
        "category_code": "refrigerator",
        "description": "Chemical or gas smell from a refrigerator",
        "protective_message": (
            "Please keep flames and switches away, open windows and do not run the refrigerator."
        ),
    },
    "URG-FOOD-RISK": {
        "class": "urgent",
        "category_code": "refrigerator",
        "description": "Refrigerator not cooling and food, milk or medicine is at risk",
        "protective_message": (
            "Please keep the door closed and move milk and medicines to a neighbour's "
            "refrigerator if you can."
        ),
    },
    "URG-VULNERABLE-HEAT": {
        "class": "urgent",
        "category_code": "air_conditioner",
        "description": "No cooling with an infant, an elderly person or a medical need at home",
        "protective_message": None,
    },
    "URG-ACTIVE-LEAK": {
        "class": "urgent",
        "category_code": None,
        "description": "Active water leak that switching the appliance off does not stop",
        "protective_message": "Please close the water inlet tap for the appliance.",
    },
    "URG-REPEAT-30D": {
        "class": "urgent",
        "category_code": None,
        "description": "Same fault again within 30 days of a repair",
        "protective_message": None,
    },
    "URG-NO-WATER-HEAT": {
        "class": "urgent",
        "category_code": "water_heater",
        "description": "No hot water with an infant or elderly person at home",
        "protective_message": None,
    },
    "STD-DEFAULT": {
        "class": "standard",
        "category_code": None,
        "description": "Working partly, or stopped with nothing at risk",
        "protective_message": None,
    },
    "PLN-SERVICE": {
        "class": "planned",
        "category_code": None,
        "description": "Preventive service",
        "protective_message": None,
    },
    "PLN-INSTALL": {
        "class": "planned",
        "category_code": None,
        "description": "Installation or demo",
        "protective_message": None,
    },
}

_FOOD_RISK_TERMS = (
    "food", "milk", "medicine", "medicines", "insulin", "spoiling", "spoil",
    "खाना", "दूध", "दवाई", "दवाइयां", "khana", "doodh", "dawai",
    "ఆహారం", "పాలు", "మందులు", "paalu", "mandulu",
)
_VULNERABLE_TERMS = (
    "infant", "baby", "newborn", "elderly", "senior", "old age", "medical", "patient",
    "बच्चा", "शिशु", "बुजुर्ग", "मरीज", "baccha", "buzurg", "mareez",
    "చిన్న పిల్లలు", "పసిపిల్ల", "వృద్ధులు", "పెద్దవారు", "musali", "pillalu",
)
_ACTIVE_LEAK_TERMS = (
    "leak continues when off", "still leaking when off", "won't stop leaking",
    "flooding", "water won't stop", "inlet leaking continuously",
    "बंद करने पर भी पानी", "लगातार पानी बह रहा",
    "ఆఫ్ చేసినా నీళ్లు", "ఆగకుండా నీళ్లు",
)


class UrgencyResult(BaseModel):
    """Structured urgency assessment matching Contract C5.1."""

    model_config = ConfigDict(populate_by_name=True)

    urgency_class: UrgencyClass = Field(alias="class")
    rule_codes: list[str]
    safety_flag: bool
    safety_reason: Optional[str] = None
    protective_steps_sent: bool = False
    protective_message: Optional[str] = None
    stop_use_message: Optional[str] = None
    matched_hazards: list[str] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    assessed_by: Literal["agent", "centre_console"] = "agent"
    reason: str


@lru_cache(maxsize=4)
def load_hazard_lexicon(path: Optional[str] = None) -> dict[str, Any]:
    """Load and cache hazard_lexicon.yaml."""
    lex_path = Path(path) if path else _LEXICON_PATH
    with lex_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


def normalize_category(category_code: Optional[str]) -> Optional[str]:
    if not category_code:
        return None
    key = category_code.strip().lower()
    return _CATEGORY_ALIASES.get(key, key)


def detect_hazards(
    text: str = "",
    facts: Optional[dict[str, Any]] = None,
    lexicon_path: Optional[str] = None,
) -> tuple[list[str], list[str]]:
    """Return `(matched_rule_codes, matched_hazard_keys)` from text and structured facts."""
    lexicon = load_hazard_lexicon(lexicon_path)
    hazards_cfg: dict[str, Any] = lexicon.get("hazards", {})
    norm_text = (text or "").lower()
    fact_map = facts or {}

    rule_codes: list[str] = []
    matched_keys: list[str] = []

    def _add(rule_code: str, hazard_key: str) -> None:
        if rule_code not in rule_codes:
            rule_codes.append(rule_code)
        if hazard_key not in matched_keys:
            matched_keys.append(hazard_key)

    # 1. Structured boolean flags
    flag_to_rule = {
        "shock_or_tingling": ("SAF-SHOCK", "shock_or_tingling"),
        "smoke_or_burning_smell": ("SAF-SMOKE-BURN", "smoke_or_burning_smell"),
        "water_near_electrics": ("SAF-WATER-ELEC", "water_near_electrics"),
        "chemical_smell": ("SAF-GAS-SMELL", "chemical_smell"),
        "gas_smell": ("SAF-GAS-SMELL", "chemical_smell"),
        "swelling": ("SAF-SMOKE-BURN", "swelling_or_rupture"),
        "swelling_or_rupture": ("SAF-SMOKE-BURN", "swelling_or_rupture"),
    }
    for flag_key, (rc, hk) in flag_to_rule.items():
        if fact_map.get(flag_key) is True:
            _add(rc, hk)

    # 2. Multilingual lexicon matching
    if norm_text:
        for hazard_key, cfg in hazards_cfg.items():
            rc = cfg.get("rule_code", "SAF-SMOKE-BURN")
            phrases_by_lang = cfg.get("phrases", {})
            hit = False
            for lang_phrases in phrases_by_lang.values():
                for phrase in lang_phrases:
                    if phrase.lower() in norm_text:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                _add(rc, hazard_key)

    return rule_codes, matched_keys


def assess_urgency(
    *,
    text: str = "",
    category_code: Optional[str] = None,
    job_type: str = "repair",
    facts: Optional[dict[str, Any]] = None,
    repeat_within_days: Optional[int] = None,
    lexicon_path: Optional[str] = None,
) -> UrgencyResult:
    """Assess urgency deterministically from text, category, job_type, and facts.

    Priority order:
    1. Safety rules (always win, even if job_type is planned)
    2. Planned job types (preventive_service, installation, uninstall_reinstall, demo)
    3. Urgent rules (repeat <= 30d, food/milk/medicine risk, vulnerable heat,
       active leak when off, no hot water with vulnerable household member)
    4. Standard default
    """
    norm_cat = normalize_category(category_code)
    norm_job = (job_type or "repair").strip().lower()
    fact_map = dict(facts or {})
    norm_text = (text or "").lower()

    if repeat_within_days is not None and "repeat_within_days" not in fact_map:
        fact_map["repeat_within_days"] = repeat_within_days

    # 1. Safety check ALWAYS runs first (100% recall invariant)
    safety_rules, matched_hazards = detect_hazards(
        text=text, facts=fact_map, lexicon_path=lexicon_path
    )
    if safety_rules:
        lexicon = load_hazard_lexicon(lexicon_path)
        canonical_stop = (
            lexicon.get("metadata", {}).get("canonical_stop_use_message")
            or CANONICAL_STOP_USE_MESSAGE
        )
        primary_rule = safety_rules[0]
        specific_guidance = URGENCY_RULES[primary_rule]["protective_message"]
        combined_protective = f"{canonical_stop} {specific_guidance}".strip()
        safety_reason = "; ".join(
            URGENCY_RULES[rc]["description"] for rc in safety_rules if rc in URGENCY_RULES
        )
        return UrgencyResult(
            **{"class": "safety"},
            rule_codes=safety_rules,
            safety_flag=True,
            safety_reason=safety_reason,
            protective_steps_sent=True,
            protective_message=combined_protective,
            stop_use_message=canonical_stop,
            matched_hazards=matched_hazards,
            facts=fact_map,
            reason=f"Safety hazard detected ({', '.join(safety_rules)}): {safety_reason}",
        )

    # 2. Planned jobs (non-repair)
    if norm_job == "preventive_service":
        return UrgencyResult(
            **{"class": "planned"},
            rule_codes=["PLN-SERVICE"],
            safety_flag=False,
            protective_steps_sent=False,
            facts=fact_map,
            reason="Preventive service scheduled as planned.",
        )
    if norm_job in ("installation", "uninstall_reinstall", "demo"):
        return UrgencyResult(
            **{"class": "planned"},
            rule_codes=["PLN-INSTALL"],
            safety_flag=False,
            protective_steps_sent=False,
            facts=fact_map,
            reason="Installation or demo scheduled as planned.",
        )

    # 3. Urgent rules
    urgent_codes: list[str] = []
    protective_notes: list[str] = []

    at_risk_set = {str(x).strip().lower() for x in (fact_map.get("at_risk") or [])}
    text_has_food_risk = any(t in norm_text for t in _FOOD_RISK_TERMS)
    text_has_vulnerable = any(t in norm_text for t in _VULNERABLE_TERMS)
    text_has_active_leak = any(t in norm_text for t in _ACTIVE_LEAK_TERMS)

    # URG-REPEAT-30D
    rep_days = fact_map.get("repeat_within_days")
    if (isinstance(rep_days, (int, float)) and 0 <= rep_days <= 30) or fact_map.get(
        "is_repeat_30d"
    ) is True:
        urgent_codes.append("URG-REPEAT-30D")

    # URG-FOOD-RISK
    food_at_risk = bool(at_risk_set & {"food", "milk", "medicine"}) or text_has_food_risk
    not_cooling = bool(fact_map.get("not_cooling")) or (
        norm_cat == "refrigerator" and ("not cooling" in norm_text or "warm" in norm_text or food_at_risk)
    )
    if food_at_risk and (norm_cat in (None, "refrigerator") or fact_map.get("not_cooling")):
        if not_cooling or food_at_risk:
            urgent_codes.append("URG-FOOD-RISK")
            if URGENCY_RULES["URG-FOOD-RISK"]["protective_message"]:
                protective_notes.append(URGENCY_RULES["URG-FOOD-RISK"]["protective_message"])

    # URG-VULNERABLE-HEAT
    vulnerable_heat = bool(at_risk_set & {"infant", "elderly", "medical"}) or text_has_vulnerable
    if norm_cat == "air_conditioner" and vulnerable_heat and (
        fact_map.get("stopped") is True
        or fact_map.get("not_cooling") is True
        or "not cooling" in norm_text
        or "warm air" in norm_text
        or "stopped" in norm_text
    ):
        urgent_codes.append("URG-VULNERABLE-HEAT")

    # URG-ACTIVE-LEAK
    if fact_map.get("leak_continues_when_off") is True or text_has_active_leak:
        urgent_codes.append("URG-ACTIVE-LEAK")
        if URGENCY_RULES["URG-ACTIVE-LEAK"]["protective_message"]:
            protective_notes.append(URGENCY_RULES["URG-ACTIVE-LEAK"]["protective_message"])

    # URG-NO-WATER-HEAT
    vulnerable_water = bool(at_risk_set & {"infant", "elderly"}) or text_has_vulnerable
    if norm_cat == "water_heater" and vulnerable_water and (
        fact_map.get("stopped") is True
        or "no hot water" in norm_text
        or "not heating" in norm_text
    ):
        urgent_codes.append("URG-NO-WATER-HEAT")

    if urgent_codes:
        reason = "; ".join(URGENCY_RULES[rc]["description"] for rc in urgent_codes)
        prot = " ".join(protective_notes) if protective_notes else None
        return UrgencyResult(
            **{"class": "urgent"},
            rule_codes=urgent_codes,
            safety_flag=False,
            protective_steps_sent=bool(prot),
            protective_message=prot,
            facts=fact_map,
            reason=f"Urgent condition matched ({', '.join(urgent_codes)}): {reason}",
        )

    # 4. Standard default
    return UrgencyResult(
        **{"class": "standard"},
        rule_codes=["STD-DEFAULT"],
        safety_flag=False,
        protective_steps_sent=False,
        facts=fact_map,
        reason="No safety or urgent triggers matched; classified as standard.",
    )
