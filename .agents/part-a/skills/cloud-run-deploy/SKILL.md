---
name: cloud-run-deploy
description: Build, bootstrap, deploy, and tear down Keepwell backend services (kw-api and kw-worker) on Google Cloud Run in asia-south1.
---

# Cloud Run Deployment Runbook (Part A)

## Region & Services
- **Region:** `asia-south1` (Mumbai) for all personal-data resources (Cloud Run, Cloud SQL, GCS, Firestore, BigQuery, Secret Manager).
- **Services:** `kw-api` (`SERVICE_ROLE=api`, `min-instances=1` for demo, `--session-affinity` for WebSocket Live calls, `--timeout=3600`) and `kw-worker` (`SERVICE_ROLE=worker`, `min-instances=0`, `--no-allow-unauthenticated`).

## Procedure
1. **Bootstrap GCP (idempotent):**
   ```bash
   GCP_PROJECT_ID=<project> ./infra/backend/setup_gcp.sh
   ```
   Enables APIs, creates Artifact Registry `keepwell`, Cloud SQL Postgres 16 (`db-f1-micro`), GCS buckets (`media` with 48h ephemeral lifecycle, `kb`), least-privilege SAs (`kw-api-sa`, `kw-worker-sa`, `kw-scheduler-sa`), Pub/Sub topics, Firestore Native, BigQuery dataset `keepwell_analytics`, and Secret Manager placeholders.
2. **Populate secrets** in Secret Manager (`DATABASE_URL`, `GEMINI_API_KEY`, `GOOGLE_MAPS_API_KEY`, WhatsApp tokens, `MAGIC_LINK_SIGNING_KEY`, `PHONE_HASH_KEY`, `PAYMENT_WEBHOOK_SECRET`). Never commit secrets.
3. **Build & push container image:**
   ```bash
   gcloud builds submit --config=infra/backend/cloudbuild.yaml --project=<project> .
   ```
4. **Deploy Cloud Run + Scheduler jobs:**
   ```bash
   GCP_PROJECT_ID=<project> ./infra/backend/deploy_backend.sh
   ```
5. **Verify health:**
   ```bash
   curl -fsS "${API_URL}/healthz" && curl -fsS "${API_URL}/readyz"
   ```
6. **Teardown (cleanup):**
   ```bash
   GCP_PROJECT_ID=<project> ./infra/backend/teardown.sh [--delete-db]
   ```
