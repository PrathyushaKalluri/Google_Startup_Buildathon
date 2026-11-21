#!/usr/bin/env bash
set -euo pipefail

# Build all 4 Keepwell Flutter web apps using strictly --dart-define values
# from the environment (no hard-coded localhost or demo defaults in release).
#
# Usage:
#   API_BASE_URL=https://kw-api.example.com/v1 \
#   LIVE_WS_URL=wss://kw-api.example.com/v1/live/call \
#   FIREBASE_PROJECT_ID=keepwell-prod \
#   FIREBASE_API_KEY=... \
#   FIREBASE_APP_ID=... \
#   FIREBASE_AUTH_DOMAIN=keepwell-prod.firebaseapp.com \
#   FIREBASE_MESSAGING_SENDER_ID=... \
#   DEMO_MODE=false \
#   PAYMENT_MODE=sandbox \
#   ./apps/tools/build_all.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEMO_MODE="${DEMO_MODE:-false}"
API_BASE_URL="${API_BASE_URL:-}"
LIVE_WS_URL="${LIVE_WS_URL:-}"
FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-}"
FIREBASE_API_KEY="${FIREBASE_API_KEY:-}"
FIREBASE_APP_ID="${FIREBASE_APP_ID:-}"
FIREBASE_AUTH_DOMAIN="${FIREBASE_AUTH_DOMAIN:-}"
FIREBASE_MESSAGING_SENDER_ID="${FIREBASE_MESSAGING_SENDER_ID:-}"
FIRESTORE_EMULATOR_HOST="${FIRESTORE_EMULATOR_HOST:-}"
FIREBASE_AUTH_EMULATOR_HOST="${FIREBASE_AUTH_EMULATOR_HOST:-}"
PAYMENT_MODE="${PAYMENT_MODE:-sandbox}"
GOOGLE_MAPS_API_KEY="${GOOGLE_MAPS_API_KEY:-}"
LOOKER_STUDIO_URL="${LOOKER_STUDIO_URL:-}"
WASM_FLAG="${WASM_FLAG:---wasm}"

if [[ "${DEMO_MODE}" != "true" ]]; then
  for var_name in API_BASE_URL LIVE_WS_URL FIREBASE_PROJECT_ID; do
    if [[ -z "${!var_name}" ]]; then
      echo "ERROR: ${var_name} must be set when DEMO_MODE=false." >&2
      exit 1
    fi
  done
  if [[ "${FIREBASE_PROJECT_ID}" == *"placeholder"* || "${API_BASE_URL}" == *"localhost"* || "${LIVE_WS_URL}" == *"localhost"* ]]; then
    echo "ERROR: Release build (DEMO_MODE=false) refuses placeholder/localhost endpoints." >&2
    exit 1
  fi
fi

DEFINES=(
  "--dart-define=DEMO_MODE=${DEMO_MODE}"
  "--dart-define=API_BASE_URL=${API_BASE_URL}"
  "--dart-define=LIVE_WS_URL=${LIVE_WS_URL}"
  "--dart-define=FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}"
  "--dart-define=FIREBASE_API_KEY=${FIREBASE_API_KEY}"
  "--dart-define=FIREBASE_APP_ID=${FIREBASE_APP_ID}"
  "--dart-define=FIREBASE_AUTH_DOMAIN=${FIREBASE_AUTH_DOMAIN}"
  "--dart-define=FIREBASE_MESSAGING_SENDER_ID=${FIREBASE_MESSAGING_SENDER_ID}"
  "--dart-define=FIRESTORE_EMULATOR_HOST=${FIRESTORE_EMULATOR_HOST}"
  "--dart-define=FIREBASE_AUTH_EMULATOR_HOST=${FIREBASE_AUTH_EMULATOR_HOST}"
  "--dart-define=PAYMENT_MODE=${PAYMENT_MODE}"
  "--dart-define=GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}"
  "--dart-define=LOOKER_STUDIO_URL=${LOOKER_STUDIO_URL}"
)

echo "Building all 4 Keepwell web apps (DEMO_MODE=${DEMO_MODE}, PROJECT=${FIREBASE_PROJECT_ID})..."
for app in console field household brand; do
  echo ">>> Building apps/${app}..."
  (
    cd "${APPS_DIR}/${app}"
    flutter build web ${WASM_FLAG} "${DEFINES[@]}"
  )
done

echo "All 4 Keepwell web builds complete:"
ls -lh "${APPS_DIR}"/{console,field,household,brand}/build/web/main.dart.wasm
