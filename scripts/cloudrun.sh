#!/usr/bin/env bash
# Build the Dockerfile and deploy it to Cloud Run. Secrets are read from the
# root .env and sent as environment variables. Their values are never printed.
set -euo pipefail

SERVICE="${CLOUD_RUN_SERVICE:-digital-twin}"
REGION="${CLOUD_RUN_REGION:-asia-south1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

command -v gcloud >/dev/null || { echo "gcloud not found. Install the Google Cloud CLI, then run: gcloud auth login"; exit 1; }
gcloud auth print-access-token >/dev/null 2>&1 || { echo "Not logged in. Run: gcloud auth login"; exit 1; }

PROJECT="${CLOUD_RUN_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
  echo "No Google Cloud project selected. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

[ -f .env ] || { echo "Missing .env in the project root."; exit 1; }

KEYS="OPENAI_API_KEY MODEL OWNER_NAME ADMIN_PASSWORD SUPABASE_URL SUPABASE_KEY SESSION_SECRET"
parts=("COOKIE_SECURE=1")
for k in $KEYS; do
  v=$(grep -E "^${k}=" .env | head -1 | cut -d= -f2-)
  v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
  if [ -z "$v" ]; then
    case "$k" in
      MODEL|SESSION_SECRET) ;;
      *) echo "Set ${k} in .env before deploying."; exit 1 ;;
    esac
    continue
  fi
  case "$v" in
    *"|"*) echo "${k} contains a | character, which this script cannot pass through."; exit 1 ;;
  esac
  parts+=("${k}=${v}")
done

joined=$(IFS='|'; echo "${parts[*]}")
echo "Deploying ${SERVICE} to ${REGION} in project ${PROJECT}."

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1 \
  --timeout 120 \
  --cpu-boost \
  --set-env-vars "^|^${joined}"

echo "Deployed. Admin is at /admin on the URL printed above."
echo "Set a Cloud Run spend cap in Billing → Budgets before sharing the link."
