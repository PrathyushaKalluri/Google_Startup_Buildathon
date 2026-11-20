import re
from typing import Dict, Any, Optional

class SafetyEngine:
    """
    Deterministic Safety & Hazard Rules Engine.
    Executes BEFORE any LLM reasoning.
    No model is allowed to bypass or dilute these hazard determinations.
    """
    
    # Priority hazard patterns covering Telugu, Hindi (both Latin transliteration & native scripts), and English
    HAZARD_PATTERNS = {
        "REFRIGERANT_GAS_LEAK": [
            re.compile(r"gas\s+(leak|leaking|smell|vasana|badbu)", re.IGNORECASE),
            re.compile(r"(गैस|గ్యాస్).*(लीक|बदबू|వాసన|లీక్)", re.IGNORECASE),
            re.compile(r"(pungent|chemical)\s+smell", re.IGNORECASE),
            re.compile(r"r600a|r32|isobutane", re.IGNORECASE),
            re.compile(r"hissing\s+(sound|noise)\s+(near|behind)\s+compressor", re.IGNORECASE)
        ],
        "ELECTRICAL_SHOCK": [
            re.compile(r"current\s+(shock|kodutundi|mar\s*raha)", re.IGNORECASE),
            re.compile(r"(करंट|కరెంట్|झटका|షాక్|shock|current)", re.IGNORECASE),
            re.compile(r"(electric|metal)\s+shock", re.IGNORECASE),
            re.compile(r"tingling\s+(sensation|on\s+door)", re.IGNORECASE),
            re.compile(r"earthing\s+(issue|fault)", re.IGNORECASE)
        ],
        "FIRE_OR_SMOKE": [
            re.compile(r"spark(ing|\s+vastundi|\s+aa\s+raha)?", re.IGNORECASE),
            re.compile(r"(चिंगारी|స్పార్క్|धुआ|धुआँ|పొగ|smoke|fire|blast|burst)", re.IGNORECASE),
            re.compile(r"(jalne|burning)\s+(badbu|smell|plastic|wire)", re.IGNORECASE),
            re.compile(r"smoke|dhuan", re.IGNORECASE),
            re.compile(r"burst|blast|fire", re.IGNORECASE)
        ]
    }

    EMERGENCY_INSTRUCTIONS = {
        "REFRIGERANT_GAS_LEAK": "DANGER: Flammable gas leak suspected. Immediately ventilate the room, extinguish open flames, do not toggle electric switches, and step outside.",
        "ELECTRICAL_SHOCK": "DANGER: Electrical earthing hazard. Disconnect the main wall plug immediately. Do not touch metallic body with bare feet or wet hands.",
        "FIRE_OR_SMOKE": "DANGER: Fire/spark hazard. Turn off the main electrical MCB immediately and do not operate the appliance."
    }

    @classmethod
    def evaluate_hazards(cls, raw_text: str) -> Dict[str, Any]:
        """
        Scans input for safety hazards.
        Returns:
            {
                "is_hazard": bool,
                "category": Optional[str],
                "matched_pattern": Optional[str],
                "instructions": Optional[str],
                "escalate_to_human": bool
            }
        """
        if not raw_text:
            return {"is_hazard": False, "category": None, "instructions": None, "escalate_to_human": False}

        for category, patterns in cls.HAZARD_PATTERNS.items():
            for pat in patterns:
                m = pat.search(raw_text)
                if m:
                    return {
                        "is_hazard": True,
                        "category": category,
                        "matched_trigger": m.group(0),
                        "instructions": cls.EMERGENCY_INSTRUCTIONS[category],
                        "escalate_to_human": True
                    }

        return {
            "is_hazard": False,
            "category": None,
            "matched_trigger": None,
            "instructions": None,
            "escalate_to_human": False
        }
