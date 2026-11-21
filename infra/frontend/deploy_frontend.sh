#!/usr/bin/env bash
set -euo pipefail

# Deploy Keepwell frontend Hosting targets + Firestore rules & indexes.
#
# Usage:
#   FIREBASE_PROJECT_ID=keepwell-prod ./infra/frontend/deploy_frontend.sh --dry-run
#   FIREBASE_PROJECT_ID=keepwell-prod ./infra/frontend/deploy_frontend.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DRY_RUN="false"
PROJECT_ID="${FIREBASE_PROJECT_ID:-}"

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN="true"
      ;;
    --project=*)
      PROJECT_ID="${arg#*=}"
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: $0 [--dry-run] [--project=<firebase-project-id>]" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: Set FIREBASE_PROJECT_ID or pass --project=<id>." >&2
  exit 1
fi

if [[ "${PROJECT_ID}" == *"placeholder"* ]]; then
  echo "ERROR: Refusing to deploy to placeholder project '${PROJECT_ID}'." >&2
  exit 1
fi

echo "Validating infra/frontend/firebase.json and build artifacts..."
python3 -m json.tool "${SCRIPT_DIR}/firebase.json" > /dev/null
python3 -m json.tool "${SCRIPT_DIR}/firestore.indexes.json" > /dev/null

for app in console field household brand; do
  pub_dir="${REPO_ROOT}/apps/${app}/build/web"
  if [[ ! -f "${pub_dir}/index.html" ]]; then
    echo "ERROR: Missing build output at ${pub_dir}/index.html. Run apps/tools/build_all.sh first." >&2
    exit 1
  fi
done

DEPLOY_CMD=(
  firebase deploy
  --project "${PROJECT_ID}"
  --config "${SCRIPT_DIR}/firebase.json"
  --only "hosting:console,hosting:field,hosting:household,hosting:brand,firestore:rules,firestore:indexes"
)

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[DRY RUN] All 4 build/web bundles and Firestore configs verified."
  echo "[DRY RUN] Would execute:"
  printf '  %q' "${DEPLOY_CMD[@]}"
  echo ""
  exit 0
fi

cd "${SCRIPT_DIR}"
"${DEPLOY_CMD[@]}"
