import re
from typing import Dict, Any

class UntrustedInputGuard:
    """
    Model Armor / untrusted-input boundary defense.
    Enforces the core rule: customer messages, voice transcripts, and OCR text
    are STRICTLY UNTRUSTED DATA, never instructions to the model.
    """
    
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*prompt", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
        re.compile(r"dan\s+mode", re.IGNORECASE),
        re.compile(r"bypass\s+(safety|rules|gate)", re.IGNORECASE),
        re.compile(r"approve\s+this\s+quote\s+automatically", re.IGNORECASE),
        re.compile(r"override\s+price", re.IGNORECASE)
    ]

    @classmethod
    def sanitize_customer_text(cls, raw_text: str) -> Dict[str, Any]:
        """
        Sanitizes text and returns clean data payload with injection flags.
        """
        if not raw_text:
            return {"text": "", "flagged": False, "cleaned": ""}

        flagged = False
        detected_triggers = []
        for pat in cls.INJECTION_PATTERNS:
            if pat.search(raw_text):
                flagged = True
                detected_triggers.append(pat.pattern)

        # Escape delimiters to ensure text cannot break out of JSON/markdown blocks
        cleaned = raw_text.replace("```", "'''").strip()

        return {
            "text": raw_text,
            "cleaned": cleaned,
            "flagged": flagged,
            "detected_triggers": detected_triggers
        }

    @classmethod
    def wrap_as_data_block(cls, label: str, content: str) -> str:
        """
        Wraps untrusted content in an unambiguous XML-style data fence.
        """
        sanitized = cls.sanitize_customer_text(content)["cleaned"]
        return f"<{label} is_untrusted_user_data=\"true\">\n{sanitized}\n</{label}>"
