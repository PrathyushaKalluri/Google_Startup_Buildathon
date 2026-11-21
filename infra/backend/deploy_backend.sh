#!/usr/bin/env bash
# ============================================================================
# Keepwell Backend Cloud Run Deploy Script (kw-api & kw-worker)
# Region: asia-south1 (Mumbai)
# Usage:
#   GCP_PROJECT_ID=<your-project> ./infra/backend/deploy_backend.sh
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID before running}"
REGION="${GCP_REGION:-asia-south1}"
SQL_INSTANCE="${KW_SQL_INSTANCE:-keepwell-pg}"
SQL_CONN="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/keepwell/backend:${IMAGE_TAG}"
BUCKET_MEDIA="${GCS_BUCKET_MEDIA:-${PROJECT_ID}-keepwell-media}"
BUCKET_KB="${GCS_BUCKET_KB:-${PROJECT_ID}-keepwell-kb}"
DEMO_MODE="${DEMO_MODE:-true}"

COMMON_ENV="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-${PROJECT_ID}},GCS_BUCKET_MEDIA=${BUCKET_MEDIA},GCS_BUCKET_KB=${BUCKET_KB},FILE_SEARCH_STORE_PREFIX=keepwell-kb,WHATSAPP_MODE=${WHATSAPP_MODE:-simulator},TELEPHONY_MODE=${TELEPHONY_MODE:-web},OTP_PROVIDER=${OTP_PROVIDER:-sandbox},PAYMENT_MODE=${PAYMENT_MODE:-sandbox},GOOGLE_PAY_ENVIRONMENT=${GOOGLE_PAY_ENVIRONMENT:-TEST},DEMO_MODE=${DEMO_MODE}"

COMMON_SECRETS="DATABASE_URL=DATABASE_URL:latest,ADMIN_DATABASE_URL=ADMIN_DATABASE_URL:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest,WHATSAPP_VERIFY_TOKEN=WHATSAPP_VERIFY_TOKEN:latest,WHATSAPP_APP_SECRET=WHATSAPP_APP_SECRET:latest,WHATSAPP_ACCESS_TOKEN=WHATSAPP_ACCESS_TOKEN:latest,MAGIC_LINK_SIGNING_KEY=MAGIC_LINK_SIGNING_KEY:latest,PHONE_HASH_KEY=PHONE_HASH_KEY:latest,PAYMENT_WEBHOOK_SECRET=PAYMENT_WEBHOOK_SECRET:latest"

echo "==> 1. Deploying kw-api to Cloud Run (${REGION}, min-instances=0, max-instances=2)..."
gcloud run deploy kw-api \
  --image="${IMAGE_URI}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="kw-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --add-cloudsql-instances="${SQL_CONN}" \
  --set-env-vars="${COMMON_ENV},SERVICE_ROLE=api" \
  --set-secrets="${COMMON_SECRETS}" \
  --min-instances=0 \
  --max-instances=2 \
  --cpu=1 \
  --memory=1Gi \
  --timeout=3600 \
  --session-affinity \
  --allow-unauthenticated

echo "==> 2. Deploying kw-worker to Cloud Run (${REGION}, min-instances=0, max-instances=2)..."
gcloud run deploy kw-worker \
  --image="${IMAGE_URI}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="kw-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --add-cloudsql-instances="${SQL_CONN}" \
  --set-env-vars="${COMMON_ENV},SERVICE_ROLE=worker" \
  --set-secrets="${COMMON_SECRETS}" \
  --min-instances=0 \
  --max-instances=2 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=600 \
  --no-allow-unauthenticated

WORKER_URL="$(gcloud run services describe kw-worker --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
API_URL="$(gcloud run services describe kw-api --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
SCHED_SA="kw-scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> 3. Creating/updating Cloud Scheduler jobs targeting kw-worker..."
upsert_scheduler_job() {
  local name="$1"
  local schedule="$2"
  local path="$3"
  if gcloud scheduler jobs describe "${name}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "${name}" \
      --location="${REGION}" \
      --schedule="${schedule}" \
      --uri="${WORKER_URL}${path}" \
      --http-method=POST \
      --oidc-service-account-email="${SCHED_SA}" \
      --oidc-token-audience="${WORKER_URL}" \
      --project="${PROJECT_ID}" >/dev/null
  else
    gcloud scheduler jobs create http "${name}" \
      --location="${REGION}" \
      --schedule="${schedule}" \
      --uri="${WORKER_URL}${path}" \
      --http-method=POST \
      --oidc-service-account-email="${SCHED_SA}" \
      --oidc-token-audience="${WORKER_URL}" \
      --project="${PROJECT_ID}" >/dev/null
  fi
}

upsert_scheduler_job "kw-gate-silence-sweep" "*/2 * * * *" "/tasks/gate-silence-sweep"
upsert_scheduler_job "kw-expiry-sweep" "*/15 * * * *" "/tasks/expiry-sweep"
upsert_scheduler_job "kw-reminders-daily" "0 9 * * *" "/tasks/send-reminders"
upsert_scheduler_job "kw-media-retention" "0 3 * * *" "/tasks/media-retention-cleanup"
upsert_scheduler_job "kw-bq-export" "0 2 * * *" "/tasks/bigquery-export"

echo "==> Deployment complete!"
echo "    kw-api:    ${API_URL}"
echo "    kw-worker: ${WORKER_URL}"
