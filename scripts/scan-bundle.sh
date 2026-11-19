#!/usr/bin/env bash
# Fail if server-only secrets or their names leak into the built frontend bundle (master prompt §4.6).
# Usage: scripts/scan-bundle.sh [frontend/.next]
# Note: the Firebase *web* API key (AIza...) is public by design and is not flagged.
set -euo pipefail
DIR="${1:-frontend/.next}"
[[ -d "$DIR" ]] || { echo "No build output at $DIR (run pnpm build first)" >&2; exit 2; }
PATTERNS=(
  'BEGIN (RSA |EC )?PRIVATE KEY'
  'mongodb(\+srv)?://[^"<[:space:]]*:[^"<[:space:]]*@'
  'MONGODB_URI'
  'FIREBASE_SERVICE_ACCOUNT'
  '"private_key_id"'
  'GEMINI_API_KEY'
  'NVIDIA_API_KEY'
  'HF_API_KEY'
  'SUPER_ADMIN_EMAIL'
  'nvapi-[A-Za-z0-9_-]{20,}'
  'hf_[A-Za-z0-9]{30,}'
)
found=0
for p in "${PATTERNS[@]}"; do
  if grep -rIlE --include='*.js' --include='*.html' --include='*.json' --include='*.rsc' "$p" "$DIR/static" "$DIR/server/app" 2>/dev/null; then
    echo "::error::bundle contains forbidden pattern: $p" >&2
    found=1
  fi
done
[[ $found -eq 0 ]] && echo "Bundle secret scan: clean ($DIR)"
exit $found
