#!/usr/bin/env bash
set -euo pipefail
docker rm -f avatar >/dev/null 2>&1 || true
echo "Stopped."
