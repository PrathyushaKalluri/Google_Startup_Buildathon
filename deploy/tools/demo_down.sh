#!/usr/bin/env bash
# ============================================================================
# Keepwell Demo Down — Stops Cloud SQL and keeps Cloud Run scale-to-zero (min=0)
# ============================================================================
set -euo pipefail
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0527907563}"
REGION="${GCP_REGION:-asia-south1}"
SQL_INSTANCE="${KW_SQL_INSTANCE:-kw-pg-verify}"

echo "==> Stopping Cloud SQL instance ${SQL_INSTANCE} (activation-policy=NEVER)..."
/opt/homebrew/bin/gcloud sql instances patch "${SQL_INSTANCE}" \
  --activation-policy=NEVER \
  --clear-authorized-networks \
  --project="${PROJECT_ID}" \
  --quiet

for svc in kw-api kw-worker; do
  if /opt/homebrew/bin/gcloud run services describe "${svc}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    /opt/homebrew/bin/gcloud run services update "${svc}" \
      --min-instances=0 \
      --max-instances=2 \
      --region="${REGION}" \
      --project="${PROJECT_ID}" \
      --quiet >/dev/null
  fi
done

/opt/homebrew/bin/gcloud sql instances describe "${SQL_INSTANCE}" --project="${PROJECT_ID}" --format="table(name,state,settings.activationPolicy)"
echo "==> Keepwell demo environment is DOWN (zero compute cost)."
