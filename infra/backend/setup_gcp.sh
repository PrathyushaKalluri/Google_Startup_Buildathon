#!/usr/bin/env bash
# ============================================================================
# Keepwell GCP Bootstrap Script (Idempotent)
# Region: asia-south1 (Mumbai) — all personal data stays in India.
# Cost note: Cloud SQL db-f1-micro incurs small hourly cost (~$0.015/hr).
# Usage:
#   GCP_PROJECT_ID=<your-project> ./infra/backend/setup_gcp.sh
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID before running}"
REGION="${GCP_REGION:-asia-south1}"
SQL_INSTANCE="${KW_SQL_INSTANCE:-keepwell-pg}"
SQL_TIER="${KW_SQL_TIER:-db-f1-micro}"
SQL_DB="${KW_SQL_DB:-keepwell}"
AR_REPO="${KW_AR_REPO:-keepwell}"
BUCKET_MEDIA="${GCS_BUCKET_MEDIA:-${PROJECT_ID}-keepwell-media}"
BUCKET_KB="${GCS_BUCKET_KB:-${PROJECT_ID}-keepwell-kb}"
BQ_DATASET="${KW_BQ_DATASET:-keepwell_analytics}"

echo "==> Configuring gcloud project: ${PROJECT_ID} (region: ${REGION})"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "==> 1. Enabling required Google Cloud APIs..."
APIS=(
  run.googleapis.com
  cloudbuild.googleapis.com
  artifactregistry.googleapis.com
  sqladmin.googleapis.com
  firestore.googleapis.com
  firebase.googleapis.com
  secretmanager.googleapis.com
  pubsub.googleapis.com
  cloudscheduler.googleapis.com
  cloudtasks.googleapis.com
  bigquery.googleapis.com
  storage.googleapis.com
  aiplatform.googleapis.com
  generativelanguage.googleapis.com
  modelarmor.googleapis.com
  routes.googleapis.com
  geocoding-backend.googleapis.com
  addressvalidation.googleapis.com
  places-backend.googleapis.com
  cloudtrace.googleapis.com
  logging.googleapis.com
  monitoring.googleapis.com
)
gcloud services enable "${APIS[@]}" --project="${PROJECT_ID}"

echo "==> 2. Creating Artifact Registry repository (${AR_REPO})..."
if ! gcloud artifacts repositories describe "${AR_REPO}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Keepwell backend container images" \
    --project="${PROJECT_ID}"
fi

echo "==> 3. Creating least-privilege service accounts..."
ensure_sa() {
  local sa_name="$1"
  local display_name="$2"
  local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
  if ! gcloud iam service-accounts describe "${sa_email}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${sa_name}" \
      --display-name="${display_name}" \
      --project="${PROJECT_ID}"
  fi
}

ensure_sa "kw-api-sa" "Keepwell API Service Account"
ensure_sa "kw-worker-sa" "Keepwell Worker Service Account"
ensure_sa "kw-scheduler-sa" "Keepwell Scheduler Invoker Service Account"

bind_role() {
  local member="$1"
  local role="$2"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${member}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="${role}" \
    --quiet >/dev/null
}

for sa in kw-api-sa kw-worker-sa; do
  bind_role "${sa}" "roles/cloudsql.client"
  bind_role "${sa}" "roles/datastore.user"
  bind_role "${sa}" "roles/secretmanager.secretAccessor"
  bind_role "${sa}" "roles/storage.objectAdmin"
  bind_role "${sa}" "roles/pubsub.publisher"
  bind_role "${sa}" "roles/cloudtasks.enqueuer"
  bind_role "${sa}" "roles/cloudtrace.agent"
  bind_role "${sa}" "roles/logging.logWriter"
done
bind_role "kw-worker-sa" "roles/bigquery.dataEditor"
bind_role "kw-worker-sa" "roles/bigquery.jobUser"
bind_role "kw-worker-sa" "roles/pubsub.subscriber"
bind_role "kw-scheduler-sa" "roles/run.invoker"

echo "==> 4. Provisioning Cloud SQL for PostgreSQL 16 (${SQL_INSTANCE}, tier=${SQL_TIER})..."
if ! gcloud sql instances describe "${SQL_INSTANCE}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud sql instances create "${SQL_INSTANCE}" \
    --database-version=POSTGRES_16 \
    --region="${REGION}" \
    --tier="${SQL_TIER}" \
    --storage-size=10GB \
    --storage-auto-increase \
    --availability-type=zonal \
    --database-flags=cloudsql.enable_pgcrypto=on \
    --project="${PROJECT_ID}"
fi

if ! gcloud sql databases describe "${SQL_DB}" --instance="${SQL_INSTANCE}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud sql databases create "${SQL_DB}" --instance="${SQL_INSTANCE}" --project="${PROJECT_ID}"
fi

echo "==> 5. Creating Cloud Storage buckets in ${REGION}..."
for bucket in "${BUCKET_MEDIA}" "${BUCKET_KB}"; do
  if ! gcloud storage buckets describe "gs://${bucket}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${bucket}" \
      --location="${REGION}" \
      --uniform-bucket-level-access \
      --project="${PROJECT_ID}"
  fi
done

# 48-hour retention policy on unconsented raw media prefix
cat <<'EOF' > /tmp/kw_media_lifecycle.json
{
  "rule": [
    {
      "action": { "type": "Delete" },
      "condition": { "age": 2, "matchesPrefix": ["ephemeral/"] }
    }
  ]
}
EOF
gcloud storage buckets update "gs://${BUCKET_MEDIA}" --lifecycle-file=/tmp/kw_media_lifecycle.json --project="${PROJECT_ID}"
rm -f /tmp/kw_media_lifecycle.json

echo "==> 6. Creating Firestore Native database in ${REGION}..."
if ! gcloud firestore databases describe --database="(default)" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud firestore databases create \
    --database="(default)" \
    --location="${REGION}" \
    --type=firestore-native \
    --project="${PROJECT_ID}"
fi

echo "==> 7. Creating BigQuery dataset (${BQ_DATASET}) in ${REGION}..."
if ! bq --project_id="${PROJECT_ID}" show "${BQ_DATASET}" >/dev/null 2>&1; then
  bq --project_id="${PROJECT_ID}" --location="${REGION}" mk --dataset \
    --description="Keepwell pseudonymous analytics dataset" \
    "${PROJECT_ID}:${BQ_DATASET}"
fi

echo "==> 8. Creating Pub/Sub topics..."
TOPICS=(
  kw-events
  kw-projections
  kw-notifications
  kw-dlq
)
for topic in "${TOPICS[@]}"; do
  if ! gcloud pubsub topics describe "${topic}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud pubsub topics create "${topic}" --project="${PROJECT_ID}"
  fi
done

echo "==> 9. Creating Secret Manager secret placeholders (C4 contract)..."
SECRETS=(
  DATABASE_URL
  GEMINI_API_KEY
  GOOGLE_MAPS_API_KEY
  WHATSAPP_VERIFY_TOKEN
  WHATSAPP_APP_SECRET
  WHATSAPP_ACCESS_TOKEN
  MAGIC_LINK_SIGNING_KEY
  PHONE_HASH_KEY
  PAYMENT_WEBHOOK_SECRET
)
for secret in "${SECRETS[@]}"; do
  if ! gcloud secrets describe "${secret}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud secrets create "${secret}" \
      --replication-policy="user-managed" \
      --locations="${REGION}" \
      --project="${PROJECT_ID}"
  fi
done

echo "==> 10. Note on Cloud Scheduler jobs..."
echo "    Cloud Scheduler jobs targeting kw-worker are created/updated in deploy_backend.sh once kw-worker URL is known."
echo "==> GCP bootstrap complete for ${PROJECT_ID} (${REGION})."
