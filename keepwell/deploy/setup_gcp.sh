#!/usr/bin/env bash
# ==============================================================================
# KeepWell: Google Cloud Deployment Automation Script
# Region: asia-south1 (Mumbai, India)
# ==============================================================================

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project)}"
REGION="asia-south1"
REPO_NAME="keepwell-repo"
SERVICE_NAME="keepwell-app"
BUCKET_NAME="${PROJECT_ID}-keepwell-media"

echo "============================================================"
echo "Deploying KeepWell to Google Cloud"
echo "Project: $PROJECT_ID | Region: $REGION"
echo "============================================================"

# 1. Enable Required Google Cloud APIs
echo "[1/6] Enabling Google Cloud Services..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  sqladmin.googleapis.com \
  aiplatform.googleapis.com \
  --project="$PROJECT_ID"

# 2. Create Artifact Registry Repository if not exists
echo "[2/6] Configuring Artifact Registry repository in $REGION..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="KeepWell Docker Container Repository" \
    --project="$PROJECT_ID"
fi

# 3. Create Cloud Storage Bucket for audio & image evidence
echo "[3/6] Configuring Cloud Storage Bucket in $REGION..."
if ! gcloud storage buckets describe "gs://$BUCKET_NAME" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --uniform-bucket-level-access
fi

# 4. Configure Secret Manager for Gemini API Key
echo "[4/6] Checking Secret Manager for GEMINI_API_KEY..."
if ! gcloud secrets describe GEMINI_API_KEY --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Enter your Gemini API key (or press enter to skip for now):"
  read -r KEY_INPUT || KEY_INPUT=""
  if [ -n "$KEY_INPUT" ]; then
    echo -n "$KEY_INPUT" | gcloud secrets create GEMINI_API_KEY --data-file=- --project="$PROJECT_ID"
  fi
fi

# 5. Build Container Image via Cloud Build
echo "[5/6] Building and pushing Docker container via Cloud Build..."
IMAGE_TAG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME:latest"
gcloud builds submit .. --config=cloudbuild.yaml --project="$PROJECT_ID"

# 6. Deploy to Google Cloud Run
echo "[6/6] Deploying to Cloud Run in $REGION (Mumbai)..."
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_TAG" \
  --region="$REGION" \
  --platform="managed" \
  --allow-unauthenticated \
  --set-env-vars="APP_ENV=production,GCP_REGION=$REGION,GCS_BUCKET_NAME=$BUCKET_NAME" \
  --project="$PROJECT_ID"

echo "============================================================"
echo "🎉 KeepWell is successfully deployed to Google Cloud Run!"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')
echo "Public Service URL: $SERVICE_URL"
echo "Agency Desk:        $SERVICE_URL/agency"
echo "Simulator:          $SERVICE_URL/simulator"
echo "============================================================"
