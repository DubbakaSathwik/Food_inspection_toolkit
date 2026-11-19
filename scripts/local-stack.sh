#!/usr/bin/env bash
# Start the full local stack for development / e2e tests (never production):
#   MongoDB 7 (Docker) · Firebase Auth emulator · FastAPI backend (fake AI) · Next.js production build.
# Usage: scripts/local-stack.sh [--fresh]   (--fresh drops the dev database and reseeds demo data)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGS="${LOGS:-$ROOT/.local-logs}"; mkdir -p "$LOGS"
MONGO_IMAGE="${MONGO_IMAGE:-mongo:7}"

docker info >/dev/null 2>&1 || { (setsid dockerd >"$LOGS/dockerd.log" 2>&1 &); for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done; }
docker start cs-mongo >/dev/null 2>&1 || docker run -d --name cs-mongo -p 27017:27017 "$MONGO_IMAGE" >/dev/null

if ! curl -sf 127.0.0.1:9099/ >/dev/null; then
  (cd "$ROOT" && setsid nohup firebase emulators:start --only auth --project demo-cratescan >"$LOGS/emulator.log" 2>&1 &)
  for _ in $(seq 1 60); do curl -sf 127.0.0.1:9099/ >/dev/null && break; sleep 1; done
fi

cd "$ROOT/backend"
export APP_ENV=development MONGODB_DB_NAME="${MONGODB_DB_NAME:-crate_scan_dev}" FIREBASE_PROJECT_ID=demo-cratescan \
  FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 AI_PROVIDER_ORDER="${AI_PROVIDER_ORDER:-fake}" SUPER_ADMIN_EMAIL=admin@example.com \
  CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
if [[ "${1:-}" == "--fresh" ]]; then
  docker exec cs-mongo mongosh --quiet "$MONGODB_DB_NAME" --eval 'db.dropDatabase()' >/dev/null
  curl -s -X DELETE "127.0.0.1:9099/emulator/v1/projects/demo-cratescan/accounts" >/dev/null
fi
uv run python -m scripts.migrate
pkill -f "uvicorn app.main:app" 2>/dev/null || true
setsid nohup uv run uvicorn app.main:app --port 8000 >"$LOGS/api.log" 2>&1 &
for _ in $(seq 1 30); do curl -sf localhost:8000/health >/dev/null && break; sleep 1; done
[[ "${1:-}" == "--fresh" ]] && uv run python -m scripts.dev_seed

cd "$ROOT/frontend"
pkill -f "next-server|next start" 2>/dev/null || true
[[ -d .next ]] || pnpm build
setsid nohup pnpm start --port 3000 >"$LOGS/next.log" 2>&1 &
for _ in $(seq 1 30); do curl -sf -o /dev/null localhost:3000/ && break; sleep 1; done
echo "Local stack ready: web http://localhost:3000 · api http://localhost:8000 · emulator 127.0.0.1:9099 · logs $LOGS"
