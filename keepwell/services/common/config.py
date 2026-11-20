from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

KEEPWELL_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Frozen environment variables from Contract C4."""

    model_config = SettingsConfigDict(
        env_file=str(KEEPWELL_ROOT / ".env"),
        extra="ignore",
    )

    # GCP & Region
    gcp_project_id: str = "keepwell-dev"
    gcp_region: str = "asia-south1"

    # Database (defaults to local SQLite seed DB when Postgres URL is not provided)
    database_url: str = f"sqlite:///{KEEPWELL_ROOT / 'db' / 'keepwell_part_a.db'}"

    # Firebase
    firebase_project_id: str = "keepwell-dev"
    firestore_emulator_host: Optional[str] = None
    firebase_auth_emulator_host: Optional[str] = None

    # Gemini / Vertex AI (Agent Platform)
    gemini_api_key: Optional[str] = None
    google_genai_use_vertexai: bool = False
    gemini_model_agent: str = "gemini-3.8-flash"
    gemini_model_fast: str = "gemini-3.5-flash-lite"
    gemini_model_pro: str = "gemini-3.1-pro-preview"
    gemini_model_live: str = "gemini-3.1-flash-live-preview"
    gemini_model_embed: str = "gemini-embedding-2"
    gemini_model_tts: str = "gemini-3.1-flash-tts-preview"
    gemini_model_stt: str = "gemini-3.5-transcribe"
    file_search_store_prefix: str = "keepwell-kb"

    # Google Maps Platform
    google_maps_api_key: Optional[str] = None

    # WhatsApp
    whatsapp_verify_token: str = "keepwell_webhook_secret_2026"
    whatsapp_app_secret: str = "keepwell-wa-dev-secret"
    whatsapp_access_token: Optional[str] = None
    whatsapp_mode: str = "simulator"  # simulator | live

    # Telephony
    telephony_mode: str = "web"  # web | pstn

    # Security & Crypto
    magic_link_signing_key: str = "keepwell-dev-magic-signing-key"
    phone_hash_key: str = "keepwell-dev-hash-key"
    otp_provider: str = "sandbox"  # sandbox | live

    # Payments
    payment_mode: str = "sandbox"  # sandbox | live
    payment_webhook_secret: str = "keepwell-dev-payment-webhook-secret"
    upi_vpa: str = "keepwell@icici"
    google_pay_environment: str = "TEST"  # TEST | PRODUCTION
    google_pay_merchant_id: str = "BCR2DN4T2KEEPWELL"
    google_pay_gateway: str = "example"
    google_pay_gateway_merchant_id: str = "exampleGatewayMerchantId"

    # Safety & Storage
    model_armor_template: Optional[str] = None
    gcs_bucket_media: str = "keepwell-media-dev"
    gcs_bucket_kb: str = "keepwell-kb-dev"

    # App URLs & Demo
    api_base_url: str = "http://localhost:8000"
    household_host: str = "http://localhost:5003"
    live_ws_url: str = "ws://localhost:8000/v1/live/call"
    demo_mode: bool = True

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")

    @property
    def dataset_dir(self) -> Path:
        return KEEPWELL_ROOT / "input" / "dataset"


settings = Settings()
