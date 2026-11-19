#!/usr/bin/env bash
# CI variant of local-stack.sh: MongoDB (service container) and the Auth emulator are already running.
# Starts the API (fake AI, high rate limits — T-39), seeds demo accounts and serves the built frontend.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGS="$ROOT/.local-logs"; mkdir -p "$LOGS"
cd "$ROOT/backend"
export APP_ENV=development MONGODB_URI="mongodb://localhost:27017/?directConnection=true" MONGODB_DB_NAME=crate_scan_e2e \
  FIREBASE_PROJECT_ID=demo-cratescan FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 AI_PROVIDER_ORDER=fake \
  SUPER_ADMIN_EMAIL=admin@example.com CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 \
  RATE_LIMIT_DEFAULT=100000/minute RATE_LIMIT_WRITE=100000/minute RATE_LIMIT_AI=100000/minute
uv run python -m scripts.migrate
nohup uv run uvicorn app.main:app --port 8000 >"$LOGS/api.log" 2>&1 &
for _ in $(seq 1 90); do curl -sf localhost:8000/health >/dev/null && break; sleep 1; done
curl -sf localhost:8000/health >/dev/null || { cat "$LOGS/api.log"; exit 1; }
uv run python -m scripts.dev_seed
cd "$ROOT/frontend"
nohup pnpm start --port 3000 >"$LOGS/next.log" 2>&1 &
for _ in $(seq 1 60); do curl -sf -o /dev/null localhost:3000/ && exit 0; sleep 1; done
cat "$LOGS/next.log"; exit 1
