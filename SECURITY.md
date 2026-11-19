# Security — CRATE-SCAN

CRATE-SCAN is a decision-support tool for FSSAI food-safety inspectors. It stores inspectors' photos, extracted label data,
reports and an audit trail. This page describes how it is protected, what was checked in Phase 4, and what the owner
must do before launch.

## Reporting a problem
Do not open a public issue for a vulnerability. Email the project owner (repository owner on GitHub) with steps to
reproduce. Rotate any exposed key first (see "Secrets" below).

## How the system is protected

| Area | Control | Where |
|------|---------|-------|
| Sign-in | Google sign-in only (Firebase Authentication). The backend verifies every Firebase ID token (signature, audience = project, expiry). | `backend/app/auth.py` |
| New accounts | Start **pending**; an admin must approve and assign a role. Pending and disabled accounts get 403 on every app API. | `auth.py`, `routers/admin.py` |
| Roles | `inspector`, `admin`, `super_admin` in Firebase custom claims **and** MongoDB; the database is authoritative. Admin writes re-check token revocation. Role changes revoke refresh tokens; stale claims return `401 claims_stale` and the app refreshes the token. | `auth.py`, `principal.py` |
| First super admin | Only the verified Google email in `SUPER_ADMIN_EMAIL` (server env). Cannot be granted from the UI. | `repositories/users.py` |
| Data isolation | Every inspector query goes through the repository layer with an `owner_uid` filter; another inspector's record returns 404 (not 403) so IDs cannot be probed. A test fails the build if a router touches MongoDB directly. | `app/repositories/*`, `tests/test_architecture.py` |
| Input validation | Pydantic v2 models with `extra="forbid"`, length limits and enums; search text is matched with `re.escape` (no operator injection). Upload type is checked by content (Pillow), size limited (12 MB) and requests over the body limit get 413. | `app/models/*`, `main.py` |
| Rate limiting | Per client address, fixed one-minute windows: 240 requests (all), 60 writes, 12 AI calls; 429 with `Retry-After`. `X-Forwarded-For` is ignored unless `TRUSTED_PROXY_HOPS` names how many of our proxies are in front (Render: 1), then read from the right. Plus an atomic per-user daily AI quota set by admins. | `app/ratelimit.py`, `repositories/usage.py` |
| CORS | Exact origin allow-list from `CORS_ALLOWED_ORIGINS`; no wildcard, no credentials (bearer tokens only). | `main.py` |
| Headers | API: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cache-Control: no-store`, HSTS in production. Site: CSP, HSTS, frame-deny etc. via `netlify.toml`. | `main.py`, `netlify.toml` |
| API surface | `/docs` and `/openapi.json` are off in production. Errors use one JSON format without stack traces. | `main.py`, `errors.py` |
| Exports | CSV/XLSX cells starting with `= + - @` are prefixed to block formula injection. | `app/http.py` |
| AI | Provider keys are server-only. The fake provider is refused when `APP_ENV=production`. Results are labelled "AI-assisted"; the inspector confirms every field and makes the decision. Internet research only when the inspector switches it on. | `services/ai/*` |
| Photos | Originals stay in GridFS only until the report is generated (then deleted); abandoned inspections are cleaned up after the retention period. | `services/maintenance.py` |
| Audit | Admin actions and inspection decisions are written to `audit_logs`; the API offers no update/delete for them. | `repositories/audit.py` |

## Phase 4 security review (2026-11-19)

| Check | Result |
|-------|--------|
| Rate limiting (manual) | **Defect found and fixed.** slowapi did not apply limits to our routes (7/7 requests passed a 5/minute limit). Replaced by `app/ratelimit.py` (T-38). Re-checked live: `200 200 200 200 429 429 429`, `Retry-After: 41`, CORS header present on the 429, JSON error body. Unit + app tests in `tests/test_ratelimit.py`. |
| CORS | Allowed origin echoed; unknown origin gets no `Access-Control-Allow-Origin` (`tests/test_health.py`). |
| Headers | Verified on a production-mode start: HSTS present, `/docs` 404, `/api/v1/me` without token 401. |
| NoSQL injection | All regex filters use `re.escape`; operator objects in bodies are rejected with 422; operator-looking query text matches literally (`test_nosql_operators_are_treated_as_data`). No `$where`/`$expr` built from input. |
| Authorization bypass | e2e `j6-security`: no/forged token 401, other owner 404, inspector on admin APIs 403, role escalation 422, pending account 403, audit log read-only 405. |
| Secrets in Git | gitleaks v8.30.1 over full history: no leaks. `.env` files are git-ignored; only `.env.example` files are committed. |
| Secrets in the browser bundle | `scripts/scan-bundle.sh` (CI) and e2e `j6`: no server key names, connection strings or private keys in `.next`. The Firebase web API key is public by design (restrict it — see below). |
| Dependencies | pip-audit: no known vulnerabilities. pnpm audit found 1 high + 2 critical (vitest/tinypool dev tooling, @grpc/grpc-js via firebase) — fixed by upgrading vitest to 5.x and overriding @grpc/grpc-js ≥ 1.14.7; now clean. |
| Static analysis | Bandit clean; CodeQL (Python, JS/TS, security-extended) runs in CI. |

## Owner checklist before launch
1. **MongoDB Atlas:** create a database user with `readWrite` on the app database only (not Atlas admin); strong generated password.
   Network access: Render free instances have no fixed outbound IP, so `0.0.0.0/0` is needed on the free plan — this is why
   the strong password and TLS (default in `mongodb+srv`) matter. With a paid Render plan, use its static outbound IPs instead.
2. **Firebase:** enable only the Google provider; add your website's Render address to *Authorized domains*; remove `localhost` before launch
   if you do not need it. In Google Cloud → APIs & Services → Credentials, restrict the browser API key to your website's address
   (HTTP referrers) and to the Identity Toolkit / Token Service APIs.
3. **Service account JSON:** store only in Render as `FIREBASE_SERVICE_ACCOUNT_JSON`. Never commit it.
4. **AI keys:** store in Render only. Set spending limits / quotas in each provider's console.
5. **GitHub:** protect `main` (require the CI checks, require PR review, block force-push); enable secret scanning + push
   protection and Dependabot alerts; keep deploy secrets in the `production` environment with required reviewers if wanted.
6. **CORS:** set `CORS_ALLOWED_ORIGINS` to your exact website URL (the `crate-scan-web` Render address) — no localhost in production.

## Secrets: if one leaks
Rotate it at the provider first (Atlas password, Firebase service-account key, AI keys, Render API keys),
update the value in Render/GitHub, redeploy, then remove it from Git history if it was committed.

## Known limitations
- Rate-limit counters are in memory per process: correct for one Render instance; scaling out needs a shared store.
- Render free has no static outbound IP, so Atlas must accept connections from anywhere (password + TLS protect it).
- Real Google sign-in, real Firebase project, real AI providers and the deployed environment were not available during the build
  and have **not** been verified (see `docs/TEST_REPORT.md`).

## Audit follow-ups (2026-11-20) — see `SECURITY_AUDIT_REPORT.md`
A pre-production attacker-style audit was run against the local stack (`security-tests/`). Fixed and verified: pixel-bomb uploads (50 MP cap),
NUL-byte search 503, `X-Forwarded-For` rate-limit bypass, crash on missing Firebase credentials, non-Google sign-in providers, unsafe link schemes.

**Open items for the owner (manual):**
1. Rotate every credential that appeared in chat: Firebase service-account key, Atlas password, Gemini / NVIDIA / Hugging Face keys.
2. Protect `main` (pull request + required checks + no force push); enable Dependabot security updates.
3. Atlas: app user `readWrite` on `crate_scan` only; network access `0.0.0.0/0` is an **accepted risk** on Render free (compensated by a long random password, TLS and the least-privilege user — verify them); no backups on the free tier.
4. Firebase: Google provider only, anonymous auth off, authorised domains = the real site only, Firestore/Realtime Database/Cloud Storage disabled or deny-all, web API key restricted to the site, one service-account key.
5. Render: `APP_ENV=production`, `TRUSTED_PROXY_HOPS=1`, no preview environments; confirm with **Admin → Diagnostics → Client address**.

**Accepted risks:** in-memory rate limits (single instance); the web API key is public by design; the CSP allows inline scripts/styles (no nonce pipeline yet);
the Firebase emulator accepts unsigned tokens (local only; production refuses the emulator host).
