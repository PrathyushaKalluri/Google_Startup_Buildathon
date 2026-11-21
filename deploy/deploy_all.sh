#!/usr/bin/env bash
# ============================================================================
# Keepwell Unified Deploy Script (Part C — Integrator)
# Deploys Cloud SQL (start if stopped), Cloud Run (kw-api, kw-worker with
# min-instances=0, max-instances=2), Firestore rules/indexes, and 4 Firebase
# Hosting targets (kw-console-0527, kw-field-0527, kw-household-0527, kw-brand-0527).
# Usage:
#   ./deploy/deploy_all.sh --dry-run
#   ./deploy/deploy_all.sh
# ============================================================================
set -euo pipefail

DRY_RUN="false"
for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    DRY_RUN="true"
  fi
done

PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0527907563}"
REGION="${GCP_REGION:-asia-south1}"
SQL_INSTANCE="${KW_SQL_INSTANCE:-kw-pg-verify}"

echo "==> Keepwell Unified Deploy (project=${PROJECT_ID}, region=${REGION}, sql=${SQL_INSTANCE}, dry_run=${DRY_RUN})"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[DRY-RUN] 1. Would start Cloud SQL instance ${SQL_INSTANCE} (db-f1-micro, POSTGRES_16)"
  echo "[DRY-RUN] 2. Would build & push image ${REGION}-docker.pkg.dev/${PROJECT_ID}/keepwell/backend:latest via Cloud Build"
  echo "[DRY-RUN] 3. Would deploy Cloud Run kw-api & kw-worker (min-instances=0, max-instances=2)"
  echo "[DRY-RUN] 4. Would build 4 Flutter Web apps (--wasm) targeting kw-api URL"
  echo "[DRY-RUN] 5. Would deploy Firestore rules/indexes & 4 Hosting sites (kw-{console,field,household,brand}-0527)"
  echo "[DRY-RUN] 6. Would update Firebase Auth authorizedDomains and run deploy/tools/smoke_test.py"
  exit 0
fi

echo "==> 1. Starting Cloud SQL instance ${SQL_INSTANCE}..."
/opt/homebrew/bin/gcloud sql instances patch "${SQL_INSTANCE}" \
  --activation-policy=ALWAYS \
  --project="${PROJECT_ID}" \
  --quiet

echo "==> 2. Building backend container via Cloud Build..."
/opt/homebrew/bin/gcloud builds submit \
  --config=infra/backend/cloudbuild.yaml \
  --project="${PROJECT_ID}" .

echo "==> 3. Deploying Cloud Run services (kw-api & kw-worker, min=0, max=2)..."
GCP_PROJECT_ID="${PROJECT_ID}" GCP_REGION="${REGION}" KW_SQL_INSTANCE="${SQL_INSTANCE}" \
  ./infra/backend/deploy_backend.sh

API_URL="$(/opt/homebrew/bin/gcloud run services describe kw-api --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
WS_URL="${API_URL/https:\/\//wss:\/\/}/v1/live/call"

echo "==> 4. Building 4 Flutter Web apps (--wasm) against ${API_URL}/v1..."
API_BASE_URL="${API_URL}/v1" LIVE_WS_URL="${WS_URL}" FIREBASE_PROJECT_ID="${PROJECT_ID}" DEMO_MODE="true" \
  ./apps/tools/build_all.sh

echo "==> 5. Deploying Firestore rules/indexes and 4 Firebase Hosting sites..."
FIREBASE_PROJECT_ID="${PROJECT_ID}" ./infra/frontend/deploy_frontend.sh

echo "==> 6. Running production smoke tests against ${API_URL}..."
KW_SMOKE_URL="${API_URL}" PYTHONPATH=. .venv312/bin/python deploy/tools/smoke_test.py
