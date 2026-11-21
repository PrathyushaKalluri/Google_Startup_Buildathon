#!/usr/bin/env bash
# ============================================================================
# Keepwell Demo Up — Starts Cloud SQL on demand and warms Cloud Run kw-api
# ============================================================================
set -euo pipefail
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0527907563}"
REGION="${GCP_REGION:-asia-south1}"
SQL_INSTANCE="${KW_SQL_INSTANCE:-kw-pg-verify}"

echo "==> Starting Cloud SQL instance ${SQL_INSTANCE} (${PROJECT_ID})..."
/opt/homebrew/bin/gcloud sql instances patch "${SQL_INSTANCE}" \
  --activation-policy=ALWAYS \
  --project="${PROJECT_ID}" \
  --quiet

API_URL="$(/opt/homebrew/bin/gcloud run services describe kw-api --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)' 2>/dev/null || true)"
if [[ -n "${API_URL}" ]]; then
  echo "==> Warming kw-api at ${API_URL}/readyz..."
  curl -fsS "${API_URL}/readyz" && echo ""
fi
echo "==> Keepwell demo environment is UP."
