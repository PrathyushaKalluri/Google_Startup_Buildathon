"""Deterministic payment intent, HMAC webhook verification, and sandbox engine (A2).

Enforces Contract C5.1, C5.2, and AGENTS.md Section 6.2 A2:
- Creates `PaymentIntent` for `upi_intent` (from `UPI_VPA`) or `google_pay`
  (Google Pay Web API payload for TEST / PRODUCTION).
- Verifies HMAC-SHA256 webhook signatures using constant-time comparison.
- Supports sandbox completion when `payment_mode == 'sandbox'`.
- Hard invariant: payment NEVER closes a job; only the household's OTP does.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from urllib.parse import urlencode

from pydantic import BaseModel, Field

PAYMENT_CLOSES_JOB: bool = False

PaymentMethod = Literal["upi_intent", "google_pay"]
PaymentStatus = Literal["created", "pending", "paid", "failed", "expired"]
GooglePayEnv = Literal["TEST", "PRODUCTION"]


class GooglePayTransactionInfo(BaseModel):
    currency_code: Literal["INR"] = "INR"
    total_price_status: Literal["FINAL"] = "FINAL"
    total_price: str


class GooglePayPayload(BaseModel):
    environment: GooglePayEnv = "TEST"
    merchant_name: str
    merchant_id: str
    gateway: str
    gateway_merchant_id: str
    transaction_info: GooglePayTransactionInfo


class PaymentIntentModel(BaseModel):
    """Matches Contract C5.1 PaymentIntent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quote_id: str
    amount_paise: int = Field(gt=0)
    status: PaymentStatus = "created"
    method: PaymentMethod
    upi_intent_url: Optional[str] = None
    google_pay: Optional[GooglePayPayload] = None
    payment_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    paid_at: Optional[datetime] = None


def paise_to_rupees_str(amount_paise: int) -> str:
    """Format integer paise as rupees with 2 decimal places (e.g. 12550 -> '125.50')."""
    rupees, paise = divmod(amount_paise, 100)
    return f"{rupees}.{paise:02d}"


def create_payment_intent(
    *,
    quote_id: str,
    amount_paise: int,
    method: PaymentMethod,
    upi_vpa: str = "",
    merchant_name: str = "Keepwell Service Centre",
    google_pay_environment: GooglePayEnv = "TEST",
    google_pay_merchant_id: str = "",
    google_pay_gateway: str = "example",
    google_pay_gateway_merchant_id: str = "",
    ttl_minutes: int = 30,
    now: Optional[datetime] = None,
) -> PaymentIntentModel:
    """Create a UPI intent or Google Pay Web API PaymentIntent."""
    if amount_paise <= 0:
        raise ValueError("amount_paise must be positive.")

    created = now or datetime.now(timezone.utc)
    expires = created + timedelta(minutes=ttl_minutes)
    intent_id = str(uuid.uuid4())
    amount_str = paise_to_rupees_str(amount_paise)

    upi_url: Optional[str] = None
    gpay_payload: Optional[GooglePayPayload] = None

    if method == "upi_intent":
        if not upi_vpa or "@" not in upi_vpa:
            raise ValueError("A valid UPI_VPA (e.g. centre@upi) is required for upi_intent.")
        params = urlencode(
            {
                "pa": upi_vpa,
                "pn": merchant_name,
                "tr": intent_id,
                "tn": f"Keepwell quote {quote_id}",
                "am": amount_str,
                "cu": "INR",
            }
        )
        upi_url = f"upi://pay?{params}"
    elif method == "google_pay":
        gpay_payload = GooglePayPayload(
            environment=google_pay_environment,
            merchant_name=merchant_name,
            merchant_id=google_pay_merchant_id or "BCR2DN0000000000",
            gateway=google_pay_gateway,
            gateway_merchant_id=google_pay_gateway_merchant_id or "exampleGatewayMerchantId",
            transaction_info=GooglePayTransactionInfo(
                currency_code="INR",
                total_price_status="FINAL",
                total_price=amount_str,
            ),
        )
    else:
        raise ValueError(f"Unsupported payment method: {method!r}")

    return PaymentIntentModel(
        id=intent_id,
        quote_id=quote_id,
        amount_paise=amount_paise,
        status="pending",
        method=method,
        upi_intent_url=upi_url,
        google_pay=gpay_payload,
        created_at=created,
        expires_at=expires,
    )


def sign_webhook_payload(payload: bytes, secret: str) -> str:
    """Compute hex HMAC-SHA256 signature for a payment webhook payload."""
    if not secret:
        raise ValueError("PAYMENT_WEBHOOK_SECRET must not be empty.")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 webhook signature using constant-time comparison."""
    if not secret or not signature:
        return False
    expected = sign_webhook_payload(payload, secret)
    provided = signature.strip()
    if provided.startswith("sha256="):
        provided = provided[len("sha256="):]
    return hmac.compare_digest(expected, provided)


def complete_sandbox_payment(
    intent: PaymentIntentModel,
    *,
    result: Literal["success", "failure"] = "success",
    payment_mode: str = "sandbox",
    now: Optional[datetime] = None,
) -> PaymentIntentModel:
    """Complete a PaymentIntent in sandbox mode only."""
    if payment_mode != "sandbox":
        raise PermissionError("Sandbox completion is only permitted when PAYMENT_MODE=sandbox.")

    ts = now or datetime.now(timezone.utc)
    updated = intent.model_copy(deep=True)
    if result == "success":
        updated.status = "paid"
        updated.payment_ref = f"SBX-{uuid.uuid4().hex[:12].upper()}"
        updated.paid_at = ts
    else:
        updated.status = "failed"
    return updated


def can_close_job_from_payment(intent: PaymentIntentModel) -> bool:
    """Invariant: payment NEVER closes a job; only household OTP closure does."""
    _ = intent
    return PAYMENT_CLOSES_JOB
