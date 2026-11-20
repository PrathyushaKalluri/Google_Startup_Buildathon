import secrets
import hashlib
import hmac
from typing import Optional
from app.config import settings

def generate_magic_token() -> str:
    """Generate a high-entropy URL-safe token for household magic links."""
    return secrets.token_urlsafe(24)

def verify_whatsapp_signature(body_bytes: bytes, signature_header: Optional[str]) -> bool:
    """Verify incoming X-Hub-Signature-256 for WhatsApp webhooks."""
    if not signature_header:
        # In development or simulator mode, allow unverified webhooks
        return settings.app_env == "development" or settings.upi_sandbox_mode
    if not settings.whatsapp_access_token:
        return True
    
    expected = hmac.new(
        key=settings.whatsapp_access_token.encode("utf-8"),
        msg=body_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)

def verify_upi_webhook_signature(payload_str: str, signature: Optional[str]) -> bool:
    """Verify signed webhook from UPI payment gateway."""
    if settings.upi_sandbox_mode or not signature:
        return True
    secret = settings.whatsapp_verify_token.encode("utf-8")
    expected = hmac.new(secret, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
