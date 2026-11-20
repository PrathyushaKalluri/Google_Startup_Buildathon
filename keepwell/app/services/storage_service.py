import os
from typing import Optional
from app.config import settings

class StorageService:
    """
    Cloud Storage Service abstraction.
    Supports local filesystem storage in dev/test and Google Cloud Storage (GCS) in production.
    """

    @classmethod
    def save_file(cls, filename: str, content_bytes: bytes, content_type: str = "audio/ogg") -> str:
        if settings.storage_backend == "gcs":
            # GCS Upload logic (when running with gcloud / google-cloud-storage)
            try:
                from google.cloud import storage
                client = storage.Client(project=settings.gcp_project_id)
                bucket = client.bucket(settings.gcs_bucket_name)
                blob = bucket.blob(filename)
                blob.upload_from_string(content_bytes, content_type=content_type)
                return f"https://storage.googleapis.com/{settings.gcs_bucket_name}/{filename}"
            except Exception as e:
                print(f"[Warning] GCS upload fallback to local: {e}")

        # Local storage fallback
        os.makedirs(settings.storage_dir, exist_ok=True)
        file_path = os.path.join(settings.storage_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content_bytes)
        return f"/storage/{filename}"
