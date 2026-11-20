import re
from typing import Dict, Any, Optional

class IdentityAgent:
    """
    Appliance Identity Agent.
    Parses OCR text or model plate images to extract Model Number and Serial Number.
    Performs exact database matching to pull prior repair history.
    """

    # Common Indian Refrigerator & AC model formats
    MODEL_REGEXES = [
        re.compile(r"\b(GL-[A-Z0-9]{5,10})\b", re.IGNORECASE),          # LG Refrigerator
        re.compile(r"\b(RT[0-9]{2}[A-Z0-9]{4,8})\b", re.IGNORECASE),       # Samsung Refrigerator
        re.compile(r"\b(205\s*IMPC|215\s*VITR)\b", re.IGNORECASE),       # Whirlpool Refrigerator
        re.compile(r"\b(183V\s*CZR|185V\s*DAZ)\b", re.IGNORECASE),       # Voltas AC
        re.compile(r"\b(AR18[A-Z0-9]{6,8})\b", re.IGNORECASE),           # Samsung AC
        re.compile(r"\b(RD\s*EDGE\s*[A-Z0-9]{4,8})\b", re.IGNORECASE)     # Godrej Refrigerator
    ]

    @classmethod
    def extract_identity_from_ocr(cls, ocr_text: str) -> Dict[str, Any]:
        """Extracts brand and model from label plate OCR text."""
        model_found = None
        for reg in cls.MODEL_REGEXES:
            m = reg.search(ocr_text)
            if m:
                model_found = m.group(0).upper().replace(" ", "")
                break

        # Check brand hints
        brand = "Generic"
        ocr_lower = ocr_text.lower()
        if "lg" in ocr_lower:
            brand = "LG"
        elif "samsung" in ocr_lower:
            brand = "Samsung"
        elif "whirlpool" in ocr_lower:
            brand = "Whirlpool"
        elif "voltas" in ocr_lower:
            brand = "Voltas"
        elif "godrej" in ocr_lower:
            brand = "Godrej"

        return {
            "model_number": model_found,
            "brand": brand,
            "confidence": 0.95 if model_found else 0.40,
            "is_verified": model_found is not None
        }
