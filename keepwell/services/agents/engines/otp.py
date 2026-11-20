"""Deterministic household closure OTP engine (A2).

Enforces Contract C0, C5.2, and AGENTS.md Section 6.2 A2:
- Issues cryptographically random 6-digit OTPs.
- Stores ONLY SHA-256 hash (`code_hash`) + `otp_ref` in `OTPRecord` (never
  plaintext code in DB records).
- In `mode='sandbox'`, exposes `get_sandbox_otp(otp_ref)` for dev/test retrieval.
- Verifies OTP with expiry, attempt-limit, and constant-time digest check,
  returning a closure confirmation reference.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

OTPMode = Literal["sandbox", "live"]


class OTPRecord(BaseModel):
    """Database-safe OTP record (never stores plaintext code)."""

    otp_ref: str
    visit_id: str
    household_id: str
    code_hash: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 5
    verified_at: Optional[datetime] = None
    closure_confirmation_ref: Optional[str] = None


class OTPVerificationResult(BaseModel):
    verified: bool
    otp_ref: str
    visit_id: str
    reason: str
    closure_confirmation_ref: Optional[str] = None
    closed_at: Optional[datetime] = None


def hash_otp_code(otp_ref: str, code: str) -> str:
    """Compute SHA-256 digest of `otp_ref:code`."""
    payload = f"{otp_ref}:{code.strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class OTPService:
    """Issues and verifies 6-digit household closure OTPs."""

    def __init__(self, mode: OTPMode = "sandbox") -> None:
        self.mode: OTPMode = mode
        self._records: dict[str, OTPRecord] = {}
        self._sandbox_codes: dict[str, str] = {}

    def issue_otp(
        self,
        *,
        visit_id: str,
        household_id: str,
        ttl_seconds: int = 600,
        max_attempts: int = 5,
        now: Optional[datetime] = None,
    ) -> OTPRecord:
        """Issue a new 6-digit OTP and store only its SHA-256 hash."""
        ts = now or datetime.now(timezone.utc)
        otp_ref = f"OTP-{uuid.uuid4().hex[:12].upper()}"
        code = f"{secrets.randbelow(1_000_000):06d}"
        record = OTPRecord(
            otp_ref=otp_ref,
            visit_id=visit_id,
            household_id=household_id,
            code_hash=hash_otp_code(otp_ref, code),
            created_at=ts,
            expires_at=ts + timedelta(seconds=ttl_seconds),
            max_attempts=max_attempts,
        )
        self._records[otp_ref] = record
        if self.mode == "sandbox":
            self._sandbox_codes[otp_ref] = code
        return record

    def get_sandbox_otp(self, otp_ref: str) -> str:
        """Retrieve plaintext OTP in sandbox mode only."""
        if self.mode != "sandbox":
            raise PermissionError("Sandbox OTP lookup is disabled outside sandbox mode.")
        if otp_ref not in self._sandbox_codes:
            raise KeyError(f"Unknown sandbox otp_ref: {otp_ref!r}")
        return self._sandbox_codes[otp_ref]

    def verify_otp(
        self,
        *,
        otp_ref: str,
        code: str,
        now: Optional[datetime] = None,
    ) -> OTPVerificationResult:
        """Verify a 6-digit OTP and return closure confirmation reference on success."""
        ts = now or datetime.now(timezone.utc)
        record = self._records.get(otp_ref)
        if record is None:
            return OTPVerificationResult(
                verified=False,
                otp_ref=otp_ref,
                visit_id="",
                reason="unknown_otp_ref",
            )

        if record.verified_at is not None:
            return OTPVerificationResult(
                verified=False,
                otp_ref=otp_ref,
                visit_id=record.visit_id,
                reason="otp_already_used",
            )

        if ts > record.expires_at:
            return OTPVerificationResult(
                verified=False,
                otp_ref=otp_ref,
                visit_id=record.visit_id,
                reason="otp_expired",
            )

        if record.attempts >= record.max_attempts:
            return OTPVerificationResult(
                verified=False,
                otp_ref=otp_ref,
                visit_id=record.visit_id,
                reason="max_attempts_exceeded",
            )

        record.attempts += 1
        candidate_hash = hash_otp_code(otp_ref, code)
        if not hmac.compare_digest(record.code_hash, candidate_hash):
            return OTPVerificationResult(
                verified=False,
                otp_ref=otp_ref,
                visit_id=record.visit_id,
                reason="invalid_code",
            )

        closure_ref = f"CLS-{uuid.uuid4().hex[:12].upper()}"
        record.verified_at = ts
        record.closure_confirmation_ref = closure_ref
        return OTPVerificationResult(
            verified=True,
            otp_ref=otp_ref,
            visit_id=record.visit_id,
            reason="verified",
            closure_confirmation_ref=closure_ref,
            closed_at=ts,
        )
