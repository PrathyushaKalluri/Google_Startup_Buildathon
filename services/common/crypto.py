from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet

from services.common.config import settings


def normalise_phone(phone: str) -> str:
    """Strip spaces and hyphens for consistent hashing."""
    return phone.replace(" ", "").replace("-", "").strip()


def hash_phone_bytes(phone: str, key: Optional[str] = None) -> bytes:
    """HMAC-SHA256 phone hash matching input/dataset/gen/common.py."""
    k = (key or settings.phone_hash_key).encode("utf-8")
    return hmac.new(k, normalise_phone(phone).encode("utf-8"), hashlib.sha256).digest()


def hash_phone_hex(phone: str, key: Optional[str] = None) -> str:
    return hash_phone_bytes(phone, key=key).hex()


def mask_phone(phone: str) -> str:
    """Return masked phone for UI & logs (never expose full PII in logs)."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return f"+91 *****{digits[-4:]}"


def _fernet() -> Fernet:
    raw_key = base64.urlsafe_b64encode(
        hashlib.sha256(b"keepwell-dev-encryption-key").digest()
    )
    return Fernet(raw_key)


def encrypt_phone(phone: str) -> bytes:
    return _fernet().encrypt(phone.encode("utf-8"))


def decrypt_phone(token: bytes) -> str:
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except Exception:
        return "+91 *****0000"


def mint_magic_token(
    subject_id: str,
    scope: str,
    ttl_seconds: int = 86400,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a URL-safe HMAC-SHA256 signed expiring token for public household routes."""
    payload: Dict[str, Any] = {
        "sub": subject_id,
        "scope": scope,
        "exp": int(time.time()) + ttl_seconds,
    }
    if extra:
        payload.update(extra)
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(
        settings.magic_link_signing_key.encode("utf-8"),
        b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{b64}.{sig}"


def verify_magic_token(token: str, expected_scope: Optional[str] = None) -> Dict[str, Any]:
    """Verify signed magic token signature, expiry, and optional scope."""
    if "." not in token:
        raise ValueError("Malformed magic token")
    b64, sig = token.rsplit(".", 1)
    expected_sig = hmac.new(
        settings.magic_link_signing_key.encode("utf-8"),
        b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("Invalid magic token signature")
    pad = "=" * (-len(b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(b64 + pad).decode("utf-8"))
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("Magic token expired")
    if expected_scope and payload.get("scope") != expected_scope:
        raise ValueError(f"Invalid scope: expected {expected_scope}")
    return payload


def verify_hmac_sha256(body: bytes, signature: Optional[str], secret: str) -> bool:
    if not signature:
        return False
    clean_sig = signature.removeprefix("sha256=")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(clean_sig, expected)
