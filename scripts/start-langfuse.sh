#!/usr/bin/env bash
# Start self-hosted Langfuse (Docker) for the ParcelCo workshop.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$ROOT/docker/langfuse"

cd "$COMPOSE_DIR"
if [ ! -f .env ]; then
  cp .env.example .env
fi
echo "Starting Langfuse stack from $COMPOSE_DIR …"
docker compose --env-file .env up -d

echo ""
echo "Waiting for http://localhost:3000 …"
for i in $(seq 1 60); do
  if curl -fsS -o /dev/null http://localhost:3000 2>/dev/null; then
    echo "Langfuse UI:  http://localhost:3000"
    echo "Login:        workshop@parcelco.local / WorkshopDemo1!"
    echo ""
    echo "Put these in the workshop .env (repo root):"
    echo "  LANGFUSE_PUBLIC_KEY=pk-lf-workshop-aa8504fbeda3a221cb5d6a06dd9bd83c"
    echo "  LANGFUSE_SECRET_KEY=sk-lf-workshop-4bfad518fa4844a0a79e1d3cd0585409"
    echo "  LANGFUSE_HOST=http://localhost:3000"
    exit 0
  fi
  sleep 2
done

echo "Langfuse did not become ready in time. Check: docker compose -f $COMPOSE_DIR/docker-compose.yml logs"
exit 1
