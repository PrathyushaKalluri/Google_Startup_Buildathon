#!/usr/bin/env bash
# Build all 4 Flutter web apps under one origin and assemble apps/hub/public.
# Re-run + `firebase deploy --only hosting:hub` to update the single combined link.
# Usage: HUB_URL=https://kw-console-0527.web.app ./apps/tools/build_hub.sh [console household field brand]
set -euo pipefail
APPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUB_URL="${HUB_URL:-https://kw-console-0527.web.app}"
PROJECT_ID="${FIREBASE_PROJECT_ID:-gen-lang-client-0527907563}"
APPS=("$@"); [[ ${#APPS[@]} -eq 0 ]] && APPS=(console household field brand)
for app in "${APPS[@]}"; do
  echo ">>> Building ${app} for ${HUB_URL}/app/${app}/"
  (cd "${APPS_DIR}/${app}" && flutter build web --wasm --base-href "/app/${app}/" \
    --dart-define=DEMO_MODE=true \
    --dart-define=API_BASE_URL="${HUB_URL}/v1" \
    --dart-define=LIVE_WS_URL="${HUB_URL/https:/wss:}/v1/live/call" \
    --dart-define=FIREBASE_PROJECT_ID="${PROJECT_ID}" \
    --dart-define=PAYMENT_MODE=sandbox)
  rm -rf "${APPS_DIR}/hub/public/app/${app}"
  mkdir -p "${APPS_DIR}/hub/public/app"
  cp -R "${APPS_DIR}/${app}/build/web" "${APPS_DIR}/hub/public/app/${app}"
done
echo "Hub assembled in apps/hub/public. Deploy: firebase deploy --only hosting:hub --project ${PROJECT_ID}"
