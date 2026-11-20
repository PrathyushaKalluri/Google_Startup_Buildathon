from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx

from services.common.config import settings


@dataclass
class GuardResult:
    original_length: int
    sanitized_text: str
    filtered: bool
    findings: List[str] = field(default_factory=list)
    direction: str = "inbound"
    backend: str = "regex_fallback"


def _call_real_model_armor(text: str, direction: str) -> Optional[Tuple[bool, List[str]]]:
    """Call GCP Model Armor regional REST API (asia-south1) using ADC. Returns None on outage/offline."""
    use_live = os.getenv("LIVE_GOOGLE") == "1" or os.getenv("USE_LIVE_MODEL_ARMOR") == "1"
    template = os.getenv("MODEL_ARMOR_TEMPLATE") or settings.model_armor_template
    if not (use_live and template):
        return None
    try:
        import google.auth  # type: ignore
        from google.auth.transport.requests import Request as GoogleAuthRequest  # type: ignore

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not creds.valid:
            creds.refresh(GoogleAuthRequest())
        loc = settings.gcp_region or "asia-south1"
        if "/locations/" in template:
            loc = template.split("/locations/", 1)[1].split("/", 1)[0]
        if direction == "inbound":
            url = f"https://modelarmor.{loc}.rep.googleapis.com/v1/{template}:sanitizeUserPrompt"
            body: Dict[str, Any] = {"userPromptData": {"text": text}}
        else:
            url = f"https://modelarmor.{loc}.rep.googleapis.com/v1/{template}:sanitizeModelResponse"
            body = {"modelResponseData": {"text": text}}
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": settings.gcp_project_id,
        }
        resp = httpx.post(url, json=body, headers=headers, timeout=8.0)
        if resp.status_code != 200:
            return None
        data = resp.json()
        sr = data.get("sanitizationResult", {})
        overall = sr.get("filterMatchState", "NO_MATCH_FOUND")
        findings: List[str] = []
        for fname, fobj in (sr.get("filterResults") or {}).items():
            if isinstance(fobj, dict):
                # Nested filter result (e.g. piAndJailbreakFilterResult.matchState or raiFilterResult.matchState)
                for inner in fobj.values():
                    if isinstance(inner, dict) and inner.get("matchState") == "MATCH_FOUND":
                        findings.append(f"model_armor:{fname}")
        return (overall == "MATCH_FOUND" or bool(findings)), findings
    except Exception:
        return None


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

        ma_res = _call_real_model_armor(text, direction="inbound")
        if ma_res is not None:
            matched, ma_findings = ma_res
            sanitized = cls.PLACEHOLDER if matched else text.replace("```", "'''").strip()
            return GuardResult(
                original_length=len(text),
                sanitized_text=sanitized,
                filtered=matched,
                findings=ma_findings,
                direction="inbound",
                backend="real_model_armor",
            )

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
            backend="regex_fallback",
        )

    @classmethod
    def screen_outbound(cls, text: Optional[str]) -> GuardResult:
        if not text:
            return GuardResult(original_length=0, sanitized_text="", filtered=False, direction="outbound")

        ma_res = _call_real_model_armor(text, direction="outbound")
        if ma_res is not None:
            matched, ma_findings = ma_res
            sanitized = cls.PLACEHOLDER if matched else text
            return GuardResult(
                original_length=len(text),
                sanitized_text=sanitized,
                filtered=matched,
                findings=ma_findings,
                direction="outbound",
                backend="real_model_armor",
            )

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
            backend="regex_fallback",
        )

    @classmethod
    def wrap_untrusted(cls, label: str, text: str) -> tuple[str, GuardResult]:
        res = cls.screen_inbound(text)
        fenced = f'<{label} untrusted="true">\n{res.sanitized_text}\n</{label}>'
        return fenced, res
