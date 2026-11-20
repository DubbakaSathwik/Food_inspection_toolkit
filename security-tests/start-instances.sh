#!/usr/bin/env bash
# Starts the extra LOCAL API instances some attacks need (all use a throwaway fake service account, never real keys):
#   :8012  real token verification (Firebase emulator OFF)      -> SEC_REALMODE_URL
#   :8013  APP_ENV=production                                    -> SEC_PROD_URL
#   :8014  default proxy trust (X-Forwarded-For ignored) + 5 requests/minute limit  -> SEC_RATELIMIT_URL
# Requires the main local stack (scripts/local-stack.sh --fresh) to be running for MongoDB.
set -euo pipefail
cd "$(dirname "$0")/../backend"
LOGS="$(cd .. && pwd)/.local-logs"; mkdir -p "$LOGS"
SA=$(uv run python ../security-tests/fake_service_account.py 2>/dev/null)
base=(APP_ENV=development MONGODB_DB_NAME=crate_scan_dev FIREBASE_PROJECT_ID=demo-cratescan "FIREBASE_SERVICE_ACCOUNT_JSON=$SA" FIREBASE_AUTH_EMULATOR_HOST= SUPER_ADMIN_EMAIL=admin@example.com AI_PROVIDER_ORDER=fake)
pkill -f "uvicorn app.main:app --port 801[234]" 2>/dev/null || true
(env "${base[@]}" RATE_LIMIT_DEFAULT=100000/minute RATE_LIMIT_WRITE=100000/minute RATE_LIMIT_AI=100000/minute setsid nohup uv run uvicorn app.main:app --port 8012 >"$LOGS/api-8012.log" 2>&1 </dev/null &)
(env "${base[@]}" APP_ENV=production AI_PROVIDER_ORDER=gemini CORS_ALLOWED_ORIGINS=https://site.example setsid nohup uv run uvicorn app.main:app --port 8013 --no-proxy-headers >"$LOGS/api-8013.log" 2>&1 </dev/null &)
(env "${base[@]}" RATE_LIMIT_DEFAULT=5/minute RATE_LIMIT_WRITE=5/minute RATE_LIMIT_AI=5/minute setsid nohup uv run uvicorn app.main:app --port 8014 --no-proxy-headers >"$LOGS/api-8014.log" 2>&1 </dev/null &)
for port in 8012 8013 8014; do
  for _ in $(seq 1 40); do curl -sf "localhost:$port/health" >/dev/null && break; sleep 1; done
  curl -sf "localhost:$port/health" >/dev/null && echo "up :$port" || echo "FAILED :$port (see $LOGS/api-$port.log)"
done
echo "export SEC_REALMODE_URL=http://localhost:8012 SEC_PROD_URL=http://localhost:8013 SEC_RATELIMIT_URL=http://localhost:8014"
