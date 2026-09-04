#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/docker/langfuse"
docker compose --env-file .env down
echo "Langfuse stopped."
