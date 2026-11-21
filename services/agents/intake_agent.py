from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from services.common.untrusted_guard import ModelArmorGuard

LEXICON_PATH = Path(__file__).resolve().parent / "lexicon" / "repair_vocabulary.yaml"

ERROR_CODE_RE = re.compile(r"\b(E21|E6|E4|Er4|dF|F1|F2|OE|UE|LE|CH05)\b", re.I)
TDS_RE = re.compile(r"\bTDS\b[^\d]{0,12}(\d{2,4})", re.I)
PINCODE_RE = re.compile(r"\b(50\d{4})\b")


def _detect_language(text: str, hint: Optional[str] = None) -> str:
    if any("\u0c00" <= ch <= "\u0c7f" for ch in text):
        return "te"
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return "hi"
    low = text.lower()
    if any(w in low for w in ("andi", "ledu", "ayyindi", "kuda", "chudandi", "pettanu", "ila undi", "nelalu")):
        return "te"
    if any(w in low for w in ("nahi", "kar raha", "aa raha", "pehle", "haan", "teeno", "karwana", "hai")):
        return "hi"
    return hint if hint in ("en", "hi", "te") else "en"


def _detect_category(text: str, hint: Optional[str] = None) -> str:
    if hint in ("ac", "refrigerator", "washing_machine", "ro_purifier", "geyser"):
        return hint
    low = text.lower()
    if any(k in low for k in ("washing", "washer", "वॉशिंग", "వాషింగ్", "e21", "spin", "drum", "lid", "wc-")):
        return "washing_machine"
    if any(k in low for k in ("geyser", "गीज़र", "గీజర్", "hot water", "water heater", "hw-")):
        return "geyser"
    if any(k in low for k in ("ro ", "ro water", "purifier", "tds", "membrane", "uppaga", "purelo", "pl-")):
        return "ro_purifier"
    if any(k in low for k in ("fridge", "freezer", "refrigerator", "ఫ్రిడ్జ్", "फ्रिज", "frost", "df", "er4", "fl-", "ice")):
        return "refrigerator"
    if any(k in low for k in ("ac ", "a/c", "air conditioner", "split", "ఏసీ", "एसी", "cooling", "e6", "av-", "zn-")):
        return "ac"
    return "ac"


def _detect_job_type(text: str, trigger: str, requested_job: Optional[str] = None) -> str:
    if trigger == "retailer_handover" or requested_job in ("installation", "demo"):
        return "installation"
    low = text.lower()
    if any(k in low for k in ("service karwana", "preventive", "annual service", "regular service", "3 ac hain")):
        return "preventive_service"
    if any(k in low for k in ("install", "mounting", "new ac", "new washer")):
        return "installation"
    return "repair"


def _extract_symptoms(text: str) -> List[str]:
    low = text.lower()
    symptoms: List[str] = []
    mapping = {
        "not_draining": ["e21", "not draining", "पानी नहीं निकल", "నీళ్లు బయటకు పోవడం లేదు", "drain"],
        "water_leak": ["leak", "నీళ్లు కారుతున్నాయి", "dripping", "water", "తడిసిపోయింది"],
        "not_cooling": ["not cooling", "cooling ledu", "cooling nahi", "warm air", "చల్లదనం రావడం లేదు", "weak"],
        "frost": ["frost", "ice aipoyindi", "freezer", "df", "er4", "ice"],
        "high_tds": ["tds", "uppaga", "salty", "taste"],
        "lid_fault": ["lid", "beep"],
        "shock": ["shock", "करंट", "కరెంట్", "current"],
        "burning_smell": ["burning", "जलने", "smoke", "धुआं", "spark"],
        "noisy_outdoor": ["శబ్దం", "fan", "ఫ్యాన్ తిరగడం లేదు", "noise", "sound"],
        "gasket": ["seal", "gasket", "door"],
        "no_hot_water": ["hot water", "thermostat", "heating"],
    }
    for sym, kws in mapping.items():
        if any(kw in low for kw in kws):
            symptoms.append(sym)
    return symptoms or ["general_fault"]


def run_intake_agent(
    raw_text: str,
    trigger: str,
    channel: str,
    language_hint: Optional[str] = None,
    category_hint: Optional[str] = None,
    requested_job: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ADK Intake Agent: screens text via Model Armor, detects language, category,
    job_type, error codes, symptoms, and pincode hints.
    """
    guard = ModelArmorGuard.screen_inbound(raw_text, source=channel)
    clean = guard.sanitized_text
    lang = _detect_language(clean, hint=language_hint)
    category = _detect_category(clean, hint=category_hint)
    job_type = _detect_job_type(clean, trigger=trigger, requested_job=requested_job)
    error_codes = sorted({m.group(1) for m in ERROR_CODE_RE.finditer(clean)})
    symptoms = _extract_symptoms(clean)
    tds_match = TDS_RE.search(clean)
    pin_match = PINCODE_RE.search(clean)

    facts: Dict[str, Any] = {}
    low = clean.lower()
    if any(k in low for k in ("milk", "spoil", "infant", "baby", "medicine", "food")):
        facts["food_water_health_at_risk"] = True
    if any(k in low for k in ("water", "wet", "గోడ మొత్తం తడిసిపోయింది", "spreading")):
        facts["water_leaking"] = True
    if tds_match:
        facts["tds_ppm"] = int(tds_match.group(1))
    if pin_match:
        facts["mentioned_pincode"] = pin_match.group(1)

    return {
        "sanitized_text": clean,
        "guard_filtered": guard.filtered,
        "guard_findings": guard.findings,
        "language": lang,
        "category_code": category,
        "job_type": job_type,
        "error_codes": error_codes,
        "symptoms": symptoms,
        "facts": facts,
    }
