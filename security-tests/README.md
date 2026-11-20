# security-tests — attacker-style regression suite

Raw-HTTP attacks (pytest + httpx) against a running CRATE-SCAN API. The UI is never involved. Tokens come from the Firebase Auth
**emulator** at run time and are redacted in output; nothing secret is stored in these files.

| File | Covers |
|------|--------|
| `test_01_authentication.py` | bad/forged/expired/replayed tokens on every protected route, unverified and pending accounts, disabled/revoked users |
| `test_02_authorization.py` | admin routes vs non-admins, profile/role escalation, header spoofing, plain admin vs Super Admin, demotion |
| `test_03_idor.py` | inspector B vs inspector A on every `{inspection_id}` route, scoped lists/exports, ID enumeration, mass assignment |
| `test_04_injection.py` | NoSQL operators in queries and bodies, `$`/dotted keys, malformed IDs, pagination/ReDoS, malicious uploads, pixel bombs |
| `test_05_concurrency_and_limits.py` | atomic AI quota under parallel calls, unique IDs, rate limit and `X-Forwarded-For` spoofing |
| `test_06_headers_cors_prod.py` | CORS, headers/CSP, production-mode behaviour (docs hidden, HSTS, refuses emulator) |
| `test_07_authz_matrix.py` | writes `last-run/authz-matrix.md` (route × identity statuses) |

## Run locally
Needs the local stack (MongoDB + Auth emulator + API with the seeded Super Admin): `scripts/local-stack.sh --fresh`.

```bash
security-tests/start-instances.sh
```

```bash
cd backend
export SEC_REALMODE_URL=http://localhost:8012 SEC_PROD_URL=http://localhost:8013 SEC_RATELIMIT_URL=http://localhost:8014
uv run pytest ../security-tests -q --no-cov -p no:cacheprovider --rootdir=../security-tests
```

Without the three extra instances the tests that need them are **skipped** (never silently passed): real token verification (emulator
off), production mode, and the rate-limit/`X-Forwarded-For` test. `start-instances.sh` uses a throwaway fake service account
(`fake_service_account.py`), never a real credential.

## Staging
`SEC_API_URL=https://staging… SEC_ALLOW_REMOTE=1` plus a staging Firebase **emulator-compatible** setup is only appropriate for a dedicated
staging stack with disposable data. The suite refuses non-local URLs without `SEC_ALLOW_REMOTE=1`. **Never point it at production.**

## CI
The `tests` job in `.github/workflows/ci.yml` runs this suite after Playwright (same MongoDB, emulator and API).

## Cleanup
Attack accounts are `sec-*@example.com` in the emulator and local dev database; both are disposable (`scripts/local-stack.sh --fresh`).
