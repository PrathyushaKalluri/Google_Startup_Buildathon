from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GuardResult:
    original_length: int
    sanitized_text: str
    filtered: bool
    findings: List[str] = field(default_factory=list)
    direction: str = "inbound"


class ModelArmorGuard:
    """
    Model Armor + deterministic untrusted-input & output guard.
    Every inbound message, transcript chunk, OCR string, KB snippet, and
    brand/retailer payload passes through screen_inbound() before any model sees it.
    Every model output passes through screen_outbound() before storage or display.
    """

    INJECTION_PATTERNS = [
        ("prompt_injection_ignore", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I)),
        ("prompt_injection_system", re.compile(r"(reveal|print|show|dump)\s+(your\s+)?system\s+prompt", re.I)),
        ("prompt_injection_role", re.compile(r"(you\s+are\s+now|act\s+as)\s+(a\s+)?(developer|jailbreak|dan|admin|root)", re.I)),
        ("policy_bypass", re.compile(r"bypass\s+(safety|consent|gate|otp|rls|authority)", re.I)),
        ("price_override", re.compile(r"(set|override|change)\s+(the\s+)?(price|quote|total)\s+to\s+0", re.I)),
        ("sql_injection_probe", re.compile(r";\s*(drop|delete|truncate|alter)\s+table\b", re.I)),
    ]

    UNSAFE_OUTPUT_PATTERNS = [
        ("unsafe_mains_wiring", re.compile(r"(strip|cut|touch|splice)\s+(the\s+)?(live|mains)\s+wire", re.I)),
        ("unsafe_refrigerant", re.compile(r"(open|vent|release|refill)\s+(the\s+)?(r32|r600a|refrigerant|gas)\s+(pipe|line|valve)", re.I)),
        ("forbidden_word_staff", re.compile(r"\b(human approval|dispatcher)\b", re.I)),
    ]

    PLACEHOLDER = "[filtered]"

    @classmethod
    def screen_inbound(
        cls,
        text: Optional[str],
        source: str = "household_message",
    ) -> GuardResult:
        if not text:
            return GuardResult(original_length=0, sanitized_text="", filtered=False, direction="inbound")

        findings: List[str] = []
        sanitized = text
        for code, pattern in cls.INJECTION_PATTERNS:
            if pattern.search(sanitized):
                findings.append(code)
                sanitized = pattern.sub(cls.PLACEHOLDER, sanitized)

        # Prevent markdown fence breakouts
        sanitized = sanitized.replace("```", "'''").strip()

        return GuardResult(
            original_length=len(text),
            sanitized_text=sanitized,
            filtered=bool(findings),
            findings=findings,
            direction="inbound",
        )

    @classmethod
    def screen_outbound(cls, text: Optional[str]) -> GuardResult:
        if not text:
            return GuardResult(original_length=0, sanitized_text="", filtered=False, direction="outbound")

        findings: List[str] = []
        sanitized = text
        for code, pattern in cls.UNSAFE_OUTPUT_PATTERNS:
            if pattern.search(sanitized):
                findings.append(code)
                sanitized = pattern.sub(cls.PLACEHOLDER, sanitized)

        return GuardResult(
            original_length=len(text),
            sanitized_text=sanitized,
            filtered=bool(findings),
            findings=findings,
            direction="outbound",
        )

    @classmethod
    def wrap_untrusted(cls, label: str, text: str) -> tuple[str, GuardResult]:
        res = cls.screen_inbound(text)
        fenced = f'<{label} untrusted="true">\n{res.sanitized_text}\n</{label}>'
        return fenced, res
