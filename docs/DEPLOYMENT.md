# Keepwell Cloud Deployment Guide (`docs/DEPLOYMENT.md`)

## 1. Target Environment & Cost Guardrails
- **GCP & Firebase Project:** `gen-lang-client-0527907563` (`204009310844`)
- **Primary Data Residency Region:** `asia-south1` (Mumbai) for Cloud SQL, Firestore Native, Cloud Storage, Model Armor (`keepwell-guard-v1`), and Cloud Run (`kw-api`, `kw-worker`).
  - *Location exception note:* `gemini-3.1-flash-live-preview` is served via the Gemini Developer API (`v1alpha`) global endpoint when `GOOGLE_GENAI_USE_VERTEXAI=false`.
- **Database Version Note:** Local development runs Homebrew `PostgreSQL 18.7` (required for macOS arm64 Homebrew `postgis` and `pgvector` bottles). Production Cloud SQL runs `PostgreSQL 16.15` (`kw-pg-verify`, `db-f1-micro` in `asia-south1-c`), verified with unmodified `keepwell_schema.sql` and all 4 extensions (`postgis 3.6.4`, `vector 0.8.7`, `pgcrypto 1.3`, `btree_gist 1.7`).
- **Hard Cost & Quota Caps Applied:**
  - Cloud Billing Budget Alert: `Keepwell Buildathon Budget Alert` ($25 USD at 50%, 90%, 100%).
  - Cloud Run: `--min-instances=0 --max-instances=2` on both `kw-api` and `kw-worker`.
  - Cloud SQL: `db-f1-micro` (10 GB disk), kept `STOPPED` (`--activation-policy=NEVER`) whenever idle.
  - Generative Language API Quota Overrides: `BidiGenerateContentSessionsPerProject-PaidTier3 = 30`, `GenerateContentRequestsPerMinutePerProjectPerRegion = 120`, `EmbedContentRequestsPerMinutePerProjectPerRegion = 120`, `ApiRequestsPerMinutePerProjectPerRegion = 300`.

## 2. One-Command Deploy & Dry-Run
```bash
# Preview every step without spending resources:
./deploy/deploy_all.sh --dry-run

# Full deploy (starts Cloud SQL, deploys kw-api & kw-worker, builds 4 Wasm apps, deploys Firebase Hosting, runs smoke tests):
./deploy/deploy_all.sh
```

## 3. Firebase Hosting Multisite Targets (`asia-south1` backed)
- **Centre Console & Stage View:** `https://kw-console-0527.web.app`
- **Technician & Parts Centre Field App:** `https://kw-field-0527.web.app`
- **Household Companion & Simulator:** `https://kw-household-0527.web.app`
- **Brand & Retailer Portal:** `https://kw-brand-0527.web.app`

## 4. Stop Cloud SQL When Idle
```bash
gcloud sql instances patch kw-pg-verify --activation-policy=NEVER --clear-authorized-networks --project=gen-lang-client-0527907563 --quiet
```
