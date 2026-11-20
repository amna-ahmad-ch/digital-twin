#!/usr/bin/env bash
# Build and deploy Avatar to fly.io. Pick your own APP name in this file and in fly.toml.
set -euo pipefail

APP="avatar-amna"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

command -v flyctl >/dev/null || { echo "flyctl not found. Install it first."; exit 1; }
flyctl auth whoami >/dev/null || { echo "Not logged in. Run fly auth login."; exit 1; }

flyctl status -a "$APP" >/dev/null 2>&1 || { echo "Creating $APP..."; flyctl apps create "$APP"; }

KEYS="OPENAI_API_KEY MODEL OWNER_NAME ADMIN_PASSWORD SUPABASE_URL SUPABASE_KEY SESSION_SECRET"
args=()
for k in $KEYS; do
  v=$(grep -E "^${k}=" .env | head -1 | cut -d= -f2-)
  v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
  [ -n "$v" ] && args+=("${k}=${v}")
done
[ ${#args[@]} -gt 0 ] && flyctl secrets set --stage -a "$APP" "${args[@]}"

flyctl deploy --config scripts/fly.toml --dockerfile Dockerfile -a "$APP" --ha=false
echo "Deployed: https://${APP}.fly.dev  (admin at /admin)"
