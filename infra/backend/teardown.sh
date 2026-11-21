#!/usr/bin/env bash
# ============================================================================
# Keepwell Backend GCP Teardown Script
# Deletes Cloud Run services, Cloud Scheduler jobs, Pub/Sub topics, and
# optionally the Cloud SQL instance (--delete-db).
# Usage:
#   GCP_PROJECT_ID=<your-project> ./infra/backend/teardown.sh [--delete-db]
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID before running}"
REGION="${GCP_REGION:-asia-south1}"
SQL_INSTANCE="${KW_SQL_INSTANCE:-keepwell-pg}"
DELETE_DB=false

for arg in "$@"; do
  case "${arg}" in
    --delete-db) DELETE_DB=true ;;
    *) echo "Unknown argument: ${arg}"; exit 1 ;;
  esac
done

echo "==> Tearing down Keepwell backend in ${PROJECT_ID} (${REGION})..."

echo "==> 1. Deleting Cloud Scheduler jobs..."
for job in kw-gate-silence-sweep kw-expiry-sweep kw-reminders-daily kw-media-retention kw-bq-export; do
  gcloud scheduler jobs delete "${job}" --location="${REGION}" --project="${PROJECT_ID}" --quiet 2>/dev/null || true
done

echo "==> 2. Deleting Cloud Run services..."
for svc in kw-api kw-worker; do
  gcloud run services delete "${svc}" --region="${REGION}" --project="${PROJECT_ID}" --quiet 2>/dev/null || true
done

echo "==> 3. Deleting Pub/Sub topics..."
for topic in kw-events kw-projections kw-notifications kw-dlq; do
  gcloud pubsub topics delete "${topic}" --project="${PROJECT_ID}" --quiet 2>/dev/null || true
done

if [ "${DELETE_DB}" = true ]; then
  echo "==> 4. Deleting Cloud SQL instance (${SQL_INSTANCE})..."
  gcloud sql instances delete "${SQL_INSTANCE}" --project="${PROJECT_ID}" --quiet 2>/dev/null || true
else
  echo "==> 4. Skipping Cloud SQL instance deletion (pass --delete-db to remove ${SQL_INSTANCE})."
fi

echo "==> Teardown complete."
