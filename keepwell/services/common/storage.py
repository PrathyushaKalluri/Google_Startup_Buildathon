from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

from services.common.config import KEEPWELL_ROOT, settings


class StorageAdapter:
    """Cloud Storage adapter with local filesystem fallback and 48h default retention."""

    def __init__(self, local_dir: Optional[Path] = None):
        self.local_dir = local_dir or (KEEPWELL_ROOT / "storage_part_a")
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def put_bytes(
        self,
        object_path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None,
        retain_hours: int = 48,
    ) -> Dict[str, str]:
        target_bucket = bucket or settings.gcs_bucket_media
        retain_until = (datetime.now(timezone.utc) + timedelta(hours=retain_hours)).date().isoformat()

        use_live = (
            os.getenv("LIVE_GOOGLE") == "1"
            or os.getenv("USE_LIVE_GCS") == "1"
            or (bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) and not settings.demo_mode)
        )
        if use_live and settings.gcp_project_id and settings.gcp_project_id != "keepwell-dev":
            try:
                from google.cloud import storage  # type: ignore

                client = storage.Client(project=settings.gcp_project_id)
                blob = client.bucket(target_bucket).blob(object_path)
                blob.metadata = {"retain_until": retain_until}
                blob.upload_from_string(data, content_type=content_type)
                return {
                    "storage_uri": f"gs://{target_bucket}/{object_path}",
                    "retain_until": retain_until,
                    "backend": "real_gcs",
                }
            except Exception:
                pass

        dest = self.local_dir / object_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {
            "storage_uri": f"file://{dest}",
            "retain_until": retain_until,
            "backend": "local_fallback",
        }

    def generate_signed_upload_url(self, object_path: str, content_type: str = "audio/ogg") -> Dict[str, str]:
        return {
            "upload_url": f"{settings.api_base_url}/v1/channels/whatsapp/simulator/media?path={object_path}",
            "media_ref": f"gs://{settings.gcs_bucket_media}/{object_path}",
            "content_type": content_type,
            "expires_in_seconds": "900",
        }


storage_adapter = StorageAdapter()
