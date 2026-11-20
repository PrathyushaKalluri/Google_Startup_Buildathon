---
name: gcp-deployment
description: Google Cloud deployment runbook for KeepWell on Cloud Run, Cloud SQL, Secret Manager, and Storage in Mumbai (asia-south1).
---

# KeepWell Google Cloud Deployment Runbook

## Target Infrastructure
- **Region**: `asia-south1` (Mumbai, India)
- **Container Host**: Google Cloud Run (Serverless, min instances 0, scales on HTTP requests)
- **Database**: Cloud SQL for PostgreSQL (with pgvector extension)
- **Object Storage**: Cloud Storage (for customer voice notes, model plate photos, repair audio)
- **Secrets**: Google Secret Manager (`GEMINI_API_KEY`, `DB_PASSWORD`, `WHATSAPP_TOKEN`)
- **AI Processing**: Gemini API / Vertex AI (`gemini-3.5-flash-lite`, `gemini-3.8-flash`)

## Deployment Steps
1. Authenticate and set project:
   ```bash
   gcloud auth login
   gcloud config set project <PROJECT_ID>
   ```
2. Run automated setup script:
   ```bash
   cd deploy
   ./setup_gcp.sh
   ```
3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy keepwell \
     --source . \
     --region asia-south1 \
     --allow-unauthenticated \
     --set-env-vars "APP_ENV=production,GCP_REGION=asia-south1"
   ```
