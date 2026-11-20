import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = os.getenv("APP_ENV", "development")
    port: int = int(os.getenv("PORT", "8000"))
    host: str = os.getenv("HOST", "0.0.0.0")
    debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1")
    
    # GCP / Gemini settings
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "keepwell-pilot-mumbai")
    gcp_region: str = os.getenv("GCP_REGION", "asia-south1")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    gemini_model_fast: str = os.getenv("GEMINI_MODEL_FAST", "gemini-3.5-flash-lite")
    gemini_model_reasoning: str = os.getenv("GEMINI_MODEL_REASONING", "gemini-3.8-flash")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./keepwell.db")
    
    # Storage
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local")
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")
    gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "keepwell-media-evidence")
    
    # WhatsApp
    whatsapp_phone_number_id: Optional[str] = os.getenv("WHATSAPP_PHONE_NUMBER_ID", None)
    whatsapp_access_token: Optional[str] = os.getenv("WHATSAPP_ACCESS_TOKEN", None)
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "keepwell_webhook_secret_2026")
    
    # UPI
    upi_sandbox_mode: bool = os.getenv("UPI_SANDBOX_MODE", "true").lower() in ("true", "1")
    upi_vpa: str = os.getenv("UPI_VPA", "agency.keepwell@icici")

settings = Settings()
