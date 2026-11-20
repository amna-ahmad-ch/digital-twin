#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker rm -f avatar >/dev/null 2>&1 || true
docker build -t avatar .
docker run -d --name avatar --env-file .env -p 8000:8000 avatar
echo "Avatar is running at http://localhost:8000  (admin at /admin)"
