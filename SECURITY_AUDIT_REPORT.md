# SECURITY_AUDIT_REPORT — CRATE-SCAN (pre-production audit, 2026-11-20)

> "Safe to deploy" would only mean *no known critical or high issues in the tested scope*; it is not a guarantee. This audit's
> verdict is **NOT SAFE TO DEPLOY** (see §10): exposed secrets are not yet confirmed rotated, and core areas (Atlas user
> privileges, Firebase project settings and unused products) could not be inspected.

## 1. Scope and environment
| | |
|---|---|
| Tested | The repository and its full Git history; the FastAPI backend, run **locally** against a local MongoDB 7 and the Firebase Auth emulator; three extra local instances (real token verification with the emulator off; `APP_ENV=production`; default proxy trust with a 5/min limit); the Next.js production build and headers; Render/CI configuration files; read-only GitHub repository settings |
| Not attacked | The **deployed** Render services and Atlas (no authorisation to attack production was given; no production data was touched) |
| Not accessible | MongoDB Atlas, Firebase console, Render dashboard, GitHub secrets/environments, Google Cloud API-key settings |
| Test identities | ANON, PENDING, UNVERIFIED, INSPECTOR A, INSPECTOR B (attacker), ADMIN, SUPER ADMIN, plus 7 invalid-token forms (3 more in real-verification mode). TENANT_2 does not apply (single-tenant app). All were created in the emulator; local dev data is disposable and was left in place |
| Tooling | `security-tests/` (pytest + httpx, raw HTTP, 49 tests), gitleaks 8.30.1, pip-audit 2.10.0, pnpm audit, Bandit, actionlint, `gh api` (read-only) |

## 2. Checks performed (C1–C18)
| # | Area | Status |
|---|------|--------|
| C1 | Secrets in Git history / tree / build / source maps | **Tested**: gitleaks full history clean; targeted history searches clean; only `.env.example` files tracked; bundle scan clean; no source maps. **But see SEC-006 (secrets exposed in chat)** |
| C2 | Authentication | **Tested** locally: 7 bad-token forms × 74 protected operations → 401; query-string tokens ignored; unsigned/expired/replayed tokens → 401 with the emulator **off**; disabled and revoked users blocked. **NOT VERIFIED:** signature checking against Google's real certificates and Firebase console settings (sign-up, anonymous auth, enumeration protection, authorised domains) |
| C3 | Role authorization / escalation | **Tested**: profile/role/claims injection, header spoofing, plain admin vs privileged roles, last Super Admin, demotion with stale tokens |
| C4 | IDOR / data-access layer | **Tested**: every `{inspection_id}` route as another inspector → identical to "not found"; lists/exports scoped; sequential-ID enumeration; DAL architecture test proven to fail on a violation |
| C5 | NoSQL injection | **Tested**: operator strings/objects in every query parameter and key bodies, `$`/dotted keys, malformed IDs, pagination abuse, regex (ReDoS) → SEC-002 found and fixed |
| C6 | Mass assignment | **Tested**: 8 protected fields on 7 write bodies → 422; strict models |
| C7 | File storage | App uses **GridFS, not Firebase Storage**. Upload abuse **tested** (HTML/SVG/PHP/EXE, polyglots, size, pixel bomb → SEC-001). **NOT VERIFIED:** whether Firebase Storage/Firestore/RTDB are enabled in the project and their rules |
| C8 | XSS / SSRF / redirects | **Tested/inspected**: no HTML sinks beyond fixed icons; stored markup returned as JSON with nosniff; no user-supplied outbound URLs; sign-in redirect limited to own area; SEC-009 fixed |
| C9 | Races and rate limits | **Tested**: 30 parallel AI calls vs limit 5 (never exceeded), 25 parallel creates (unique ids), parallel state changes; rate limit works; **X-Forwarded-For bypass found (SEC-003) and fixed** |
| C10 | FastAPI config, errors, disclosure | **Tested**: docs/openapi 404 in production mode, uniform errors, no stack traces, minimal `/health`, CORS exact-origin |
| C11 | Debug/dev configuration | **Tested**: production refuses emulator host, fake AI and (new) missing credentials; `APP_ENV` defaults to development → SEC-011 |
| C12 | HTTP headers | **Tested**: API and website headers and CSP on the local production build. Real-browser Google sign-in under the CSP **not tested** (`CSP_REPORT_ONLY` switch exists) |
| C13 | Dependencies | **Tested**: pip-audit and pnpm audit clean; lockfiles committed, installs frozen in CI |
| C14 | Atlas configuration | **NOT VERIFIED** (no access) |
| C15 | Backend host (Render) | **Partly**: file inspected (no secrets, auto-deploy only after checks); dashboard **NOT VERIFIED** |
| C16 | Frontend host | Frontend is a Render service (Netlify no longer used, so no Netlify secrets-scanning exclusions apply). Dashboard **NOT VERIFIED** |
| C17 | GitHub / CI | **Tested** (read-only): workflows reviewed clean; **no branch protection (SEC-005)**; Dependabot security updates off (SEC-012) |
| C18 | Firebase project settings | **NOT VERIFIED** (no access) |

## 3. Findings
| ID | Severity | Title | Location | Status |
|----|----------|-------|----------|--------|
| SEC-006 | **CRITICAL** | Live secrets pasted into a chat: Firebase service-account private key (key id `c6a9…023f`), Atlas user password (`57jJ…aMPE`), Gemini key (`AQ.A…LgFQ`), NVIDIA key (`nvap…DHQd`), Hugging Face token (`hf_j…teUN`) — shown 3×, plus a Gemini key in later messages | owner's local `backend/.env` shared in conversation | **Owner reports all keys rotated and the old Firebase key deleted (2026-11-20)**; I cannot verify rotation from here |
| SEC-005 | **HIGH** | `main` has no branch protection: direct and force pushes allowed, no required checks or reviews, on a **public** repo whose pushes auto-deploy | GitHub settings | **Closed — verified** (ruleset `protect-main` active: PR required, 6 required checks, no force push or deletion, no bypass actors) |
| SEC-007 | MEDIUM | Atlas must allow `0.0.0.0/0` for Render free; safety then depends on an unverified least-privilege user and password | Atlas | **Owner reports the Atlas user was restricted to `readWrite` on `crate_scan`**; not independently inspected |
| SEC-001 | MEDIUM | Memory-exhaustion by one image: images up to ~120 MP were accepted and decoded (≈360 MB RGB) — any inspector could crash a 512 MB instance | `services/images.py` | **Fixed and verified** |
| SEC-003 | MEDIUM | Rate limits bypassable by spoofing `X-Forwarded-For` (40/40 requests passed a 5/min limit with Render-style `--forwarded-allow-ips "*"`) | start command, `ratelimit.py` | **Fixed and verified locally**; production hop count to be confirmed via Diagnostics |
| SEC-002 | LOW | `?q=%00` made MongoDB reject the regex; any signed-in user could trigger 503 "database unavailable" | all `re.escape` search sites | **Fixed and verified** |
| SEC-004 | LOW | Missing Firebase credentials: server started, then every token check crashed with an unhandled 500 (fails closed, but noisy and confusing) | `auth.py` | **Fixed and verified** (production refuses to start; otherwise 503) |
| SEC-008 | LOW | `frontend/.env.example` was git-ignored, so the documented setup file was never committed | `frontend/.gitignore` | **Fixed** (file now trackable; needs `git add`) |
| SEC-009 | LOW | Ask-AI source links accepted any URL scheme | `ask/page.tsx` | **Fixed** |
| SEC-010 | LOW | `sign_in_provider` of `None` was accepted | `auth.py` | **Fixed** (must be `google.com`) |
| SEC-011 | LOW | `APP_ENV` defaults to `development`; if the variable were missing on Render, docs and the fake AI provider would be enabled | `config.py` | **Open** (blueprint sets `production`; Diagnostics shows it) |
| SEC-012 | LOW | GitHub Dependabot **security updates** are disabled | GitHub settings | **Closed — verified** (Dependabot security updates enabled) |

### Reproduction of the fixed findings (identity → request → before → after)
* **SEC-001** INSPECTOR → `POST /api/v1/inspections/{id}/photos` with an 8000×8000 (64 MP) PNG of ~60 KB → before: accepted (201, decoded); after: `413 image_too_large`. Regression: `backend/tests/test_inspections.py::test_pixel_bomb_is_rejected_before_decoding`, `security-tests/test_04_injection.py`.
* **SEC-002** INSPECTOR → `GET /api/v1/inspections?q=%00` → before: `503 database_unavailable`; after: `200`. Regression: `test_nul_byte_in_search_text_is_not_a_database_error`, `test_04_injection.py`.
* **SEC-003** ANON, 40× `GET /api/v1/public/site-images` with `X-Forwarded-For: 203.0.113.<i>` against a 5/min limit → before: all 200; after: 429 (header ignored unless `TRUSTED_PROXY_HOPS` is set; then read from the right). Regression: `test_ratelimit.py::test_forwarded_for_is_ignored_by_default_and_read_from_the_right_when_trusted`, `test_05_concurrency_and_limits.py`.
* **SEC-004** production start with no service account → before: server up, 500 on every request; after: refuses to start. Regression: `test_auth.py::test_production_refuses_to_start_without_firebase_credentials`.

### Behaviour worth knowing (not a defect)
The Firebase Auth **emulator** accepts unsigned and expired tokens by design. Those checks therefore run against an instance with the emulator
**off** (`SEC_REALMODE_URL`), where all 74 protected operations returned 401 for each of 3 forged/replayed token forms. This proves the app delegates to the Admin SDK's real verification;
it does not replace a test against the live Firebase project.

## 4. Fixes made
| Change | Files | Verified by |
|--------|-------|-------------|
| 50 MP pixel cap before decoding | `app/services/images.py` | exploit rerun → 413; backend + attack tests |
| NUL-safe literal search (`rx_escape`) | `app/repositories/base.py` + 5 repositories | exploit rerun → 200; tests |
| Trusted-proxy aware rate-limit key; `--no-proxy-headers`; `TRUSTED_PROXY_HOPS` (Render = 3, measured on the live site) | `app/ratelimit.py`, `config.py`, `main.py`, `render.yaml`, CI, `.env.example` | exploit rerun → 429; unit + attack tests |
| Fail-fast without Firebase credentials; 503 instead of crash | `app/auth.py`; CI start check uses a throwaway fake service account (`security-tests/fake_service_account.py`) | unit test; production-mode instance |
| Strict `google.com` provider | `app/auth.py` | full suites |
| Safe link schemes | `frontend/src/app/inspector/ask/page.tsx` | lint, types, browser suite |
| Track `frontend/.env.example` | `frontend/.gitignore` | `git check-ignore` |
| Diagnostics "Client address" check (to confirm the proxy hop count) | `app/services/diagnostics.py`, admin router | admin test |
| Attack suite added to CI (after Playwright) | `.github/workflows/ci.yml`, `security-tests/` | actionlint; **not yet run on GitHub** |

## 5. Authorization matrix (route × identity → HTTP status)
Generated by `security-tests/test_07_authz_matrix.py` with dummy path ids (so 404/422 after auth is expected); `–` = skipped (real side effect).
`ANON` no token · `PENDING` signed in, not approved · `INSPECTOR` approved inspector · `ADMIN` admin · `SUPER` Super Admin.

| Route | ANON | PENDING | INSPECTOR | ADMIN | SUPER | Expectation |
|---|---|---|---|---|---|---|
| `GET /api/v1/admin/analytics` | 401 | 403 | 403 | 200 | 200 | admin only |
| `GET /api/v1/admin/audit` | 401 | 403 | 403 | 200 | 200 | admin only |
| `GET /api/v1/admin/audit/export` | 401 | 403 | 403 | 200 | 200 | admin only |
| `GET /api/v1/admin/dashboard` | 401 | 403 | 403 | 200 | 200 | admin only |
| `GET /api/v1/admin/diagnostics` | 401 | 403 | 403 | 200 | 200 | admin only |
| `POST /api/v1/admin/diagnostics/{check_id}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `GET /api/v1/admin/proposals` | 401 | 403 | 403 | 200 | 200 | admin only |
| `GET /api/v1/admin/proposals/{proposal_id}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `POST /api/v1/admin/proposals/{proposal_id}/decision` | 401 | 403 | 403 | 422 | 422 | admin only |
| `GET /api/v1/admin/proposals/{proposal_id}/report.pdf` | 401 | 403 | 403 | 404 | 404 | admin only |
| `GET /api/v1/admin/reference` | 401 | 403 | 403 | 200 | 200 | admin only |
| `POST /api/v1/admin/reference` | 401 | 403 | 403 | 422 | 422 | admin only |
| `POST /api/v1/admin/reference/ai-extract` | 401 | 403 | 403 | 422 | 422 | admin only |
| `POST /api/v1/admin/reference/import/commit` | 401 | 403 | 403 | 422 | 422 | admin only |
| `POST /api/v1/admin/reference/import/preview` | 401 | 403 | 403 | 422 | 422 | admin only |
| `GET /api/v1/admin/reference/stats` | 401 | 403 | 403 | 200 | 200 | admin only |
| `DELETE /api/v1/admin/reference/{ref_id}` | 401 | 403 | 403 | 403 | 404 | admin only |
| `GET /api/v1/admin/reference/{ref_id}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `PATCH /api/v1/admin/reference/{ref_id}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `POST /api/v1/admin/reference/{ref_id}/archive` | 401 | 403 | 403 | 404 | 404 | admin only |
| `DELETE /api/v1/admin/reference/{ref_id}/images/{file_id}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `POST /api/v1/admin/reference/{ref_id}/restore` | 401 | 403 | 403 | 404 | 404 | admin only |
| `POST /api/v1/admin/reference/{ref_id}/versions` | 401 | 403 | 403 | 422 | 422 | admin only |
| `POST /api/v1/admin/reference/{ref_id}/versions/{version_id}/images` | 401 | 403 | 403 | 422 | 422 | admin only |
| `GET /api/v1/admin/rules` | 401 | 403 | 403 | 200 | 200 | admin only |
| `POST /api/v1/admin/rules` | 401 | 403 | 403 | 422 | 422 | admin only |
| `GET /api/v1/admin/rules/stats` | 401 | 403 | 403 | 200 | 200 | admin only |
| `GET /api/v1/admin/rules/{rule_id}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `PATCH /api/v1/admin/rules/{rule_id}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `POST /api/v1/admin/rules/{rule_id}/archive` | 401 | 403 | 403 | 404 | 404 | admin only |
| `GET /api/v1/admin/settings` | 401 | 403 | 403 | 200 | 200 | admin only |
| `PATCH /api/v1/admin/settings` | 401 | 403 | 403 | 200 | 200 | admin only |
| `DELETE /api/v1/admin/settings/images/{key}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `PUT /api/v1/admin/settings/images/{key}` | 401 | 403 | 403 | 422 | 422 | admin only |
| `GET /api/v1/admin/storage` | 401 | 403 | 403 | 200 | 200 | admin only |
| `POST /api/v1/admin/storage/cleanup` | 401 | 403 | 403 | – | – | admin only |
| `GET /api/v1/admin/users` | 401 | 403 | 403 | 200 | 200 | admin only |
| `GET /api/v1/admin/users/invites` | 401 | 403 | 403 | 200 | 200 | admin only |
| `POST /api/v1/admin/users/invites` | 401 | 403 | 403 | 422 | 422 | admin only |
| `DELETE /api/v1/admin/users/invites/{email}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `GET /api/v1/admin/users/{uid}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `PATCH /api/v1/admin/users/{uid}` | 401 | 403 | 403 | 404 | 404 | admin only |
| `POST /api/v1/admin/users/{uid}/approve` | 401 | 403 | 403 | 404 | 404 | admin only |
| `POST /api/v1/admin/users/{uid}/decline` | 401 | 403 | 403 | 404 | 404 | admin only |
| `DELETE /api/v1/assistant/messages` | 401 | 403 | 200 | 403 | 403 | active inspector/admin |
| `GET /api/v1/assistant/messages` | 401 | 403 | 200 | 403 | 403 | active inspector/admin |
| `POST /api/v1/assistant/messages` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `GET /api/v1/inspections` | 401 | 403 | 200 | 403 | 403 | active inspector/admin |
| `POST /api/v1/inspections` | 401 | 403 | 201 | 403 | 403 | active inspector/admin |
| `GET /api/v1/inspections/export` | 401 | 403 | 200 | 403 | 403 | active inspector/admin |
| `DELETE /api/v1/inspections/{inspection_id}` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `GET /api/v1/inspections/{inspection_id}` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `POST /api/v1/inspections/{inspection_id}/analyze` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `PUT /api/v1/inspections/{inspection_id}/category` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `PUT /api/v1/inspections/{inspection_id}/decision` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `POST /api/v1/inspections/{inspection_id}/extract` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `POST /api/v1/inspections/{inspection_id}/fields/confirm` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `PATCH /api/v1/inspections/{inspection_id}/fields/{key}` | 401 | 403 | 400 | 403 | 403 | active inspector/admin |
| `PATCH /api/v1/inspections/{inspection_id}/findings/{finding_id}` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `POST /api/v1/inspections/{inspection_id}/notes` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `POST /api/v1/inspections/{inspection_id}/photos` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `DELETE /api/v1/inspections/{inspection_id}/photos/{photo_id}` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `GET /api/v1/inspections/{inspection_id}/photos/{photo_id}` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `PATCH /api/v1/inspections/{inspection_id}/photos/{photo_id}` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `POST /api/v1/inspections/{inspection_id}/report` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `GET /api/v1/inspections/{inspection_id}/report.pdf` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `GET /api/v1/inspector/dashboard` | 401 | 403 | 200 | 403 | 403 | active inspector/admin |
| `GET /api/v1/me` | 401 | 200 | 200 | 200 | 200 | any signed-in user |
| `PATCH /api/v1/me` | 401 | 200 | 200 | 200 | 200 | any signed-in user |
| `GET /api/v1/proposals` | 401 | 403 | 200 | 403 | 403 | active inspector/admin |
| `POST /api/v1/proposals` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `GET /api/v1/proposals/{proposal_id}` | 401 | 403 | 404 | 403 | 403 | active inspector/admin |
| `POST /api/v1/proposals/{proposal_id}/reply` | 401 | 403 | 422 | 403 | 403 | active inspector/admin |
| `GET /api/v1/reference-images/{file_id}` | 401 | 403 | 404 | 404 | 404 | active inspector/admin |

Reading the matrix: every `admin` route returns 401/403 for ANON, PENDING and INSPECTOR; every other route returns 401/403 for ANON and PENDING.

## 6. Hosting, Atlas, Firebase and GitHub results
* **Render** (file only): no secret values in `render.yaml`; auto-deploy only from `main` after checks; no deploy hook exists. Start command no longer trusts proxy headers.
* **Netlify**: not used any more; its secrets-scanning exclusions do not apply. The Firebase web key is public by design but should be restricted to the site's domain in Google Cloud (manual).
* **Atlas / Firebase**: **NOT VERIFIED** (no access). Exact manual checks are in `SECURITY.md` §"Audit follow-ups".
* **GitHub**: repo public; secret scanning + push protection on; **no branch protection**; Dependabot security updates off; workflows clean.

## 7. Tests actually executed (final code)
| Command | Result |
|---------|--------|
| `uv run pytest --cov=app` (backend, gate 85 %) | **73 passed**, 88.94 % |
| `uv run pytest ../security-tests` (all 3 extra instances up) | **49 passed**, 0 skipped |
| `pnpm lint`, `pnpm typecheck`, `pnpm format:check` | clean |
| `pnpm test` (Vitest) | 9 passed |
| `pnpm exec playwright test` (desktop + mobile, security headers active) | **42 passed, 2 skipped** (skips by design) |
| `ruff`, `ruff format --check`, `mypy` (strict), Bandit | clean |
| gitleaks (full history), pip-audit, `pnpm audit` | no leaks / no known vulnerabilities |
| `scripts/scan-bundle.sh`, source-map search | clean / none |
| actionlint | clean |
| GitHub Actions on the new commit | **not run** (nothing was committed or pushed, per the audit rules) |

## 8. Remaining issues and manual actions
1. **Rotate now (SEC-006):** Firebase → delete the service-account key `c6a9…023f` and create a new one; Atlas → change the `dubbakasathwik_db_user` password; Google AI Studio, build.nvidia.com and Hugging Face → revoke and recreate the keys. Put new values only in Render. Check Atlas/Firebase/provider activity logs for use since the exposure.
2. **Protect `main` (SEC-005):** GitHub → Settings → Branches → rule for `main`: require a pull request, require the status checks `Quality`, `Tests`, `Security`, `CodeQL (python)`, `CodeQL (javascript-typescript)`, `Build`; block force pushes and deletions.
3. **Atlas (SEC-007):** confirm the app user has `readWrite` on `crate_scan` only; strong password; separate users for any other environment; note free tier has no backups.
4. **Firebase (C18/C7):** Google provider only; anonymous auth off; authorised domains = your real site only (remove `localhost` if unused); confirm Firestore / Realtime Database / Cloud Storage are **disabled or deny-all**; restrict the web API key to your site's referrer; keep one service-account key.
5. **Render:** confirm `APP_ENV=production`, `TRUSTED_PROXY_HOPS=3`, no preview environments; after deploy open **Admin → Diagnostics → Client address** and confirm it shows *your* public IP (if it shows a Render/Cloudflare address, raise the hop count).
6. **GitHub:** enable Dependabot security updates (SEC-012); verify the `production`-style secrets list is empty (none are needed).
7. Run the new attack suite in CI by committing these changes (not done here) and review the first run.
8. Run a live check of Google sign-in under the CSP; if blocked, set `CSP_REPORT_ONLY=true`.
9. Optional: default `APP_ENV` to `production` (SEC-011).

## 9. Final production security report — summary
Scope: local stack attacks plus repository, history, build and read-only GitHub inspection. Production, Atlas and Firebase were **not** inspected.
Found: 1 critical (open), 1 high (open), 3 medium (1 open/not verified, 2 fixed and verified), 7 low (5 fixed, 2 open).
Core areas: token verification (tested, locally), role checks (tested), data-access layer and IDOR (tested), NoSQL injection (tested), secret exposure in code/history/build (tested — clean) **but exposed in chat**, file rules / Firebase project (NOT VERIFIED), Atlas user privileges (NOT VERIFIED), CI deploy gate (partly: no branch protection).

## 10. Final verdict
**NOT SAFE TO DEPLOY.** Live secrets were exposed in a chat and their rotation is unconfirmed (SEC-006), `main` is unprotected on a public repo that auto-deploys (SEC-005), and the Atlas user privileges and Firebase project settings — both core areas — could not be verified. The application code itself held up well against the attacks that were run, and the four code-level weaknesses found are fixed and verified; once items 1–4 in §8 are done and re-checked, this verdict can be re-evaluated.

## 11. Update after owner actions (2026-11-20)
Verified by me: `main` protected by the `protect-main` ruleset (pull request required, the six CI checks required, no force push, no deletion, no bypass actors);
Dependabot security updates enabled; secret scanning and push protection enabled; CI green on `main` (PR #10) and on the audit and CSP-fix commits;
gitleaks clean over the full history and no key-like strings in the tree; **Admin → Diagnostics → Client address on the live site shows the visitor's own
public address with `TRUSTED_PROXY_HOPS=3`** (SEC-003 confirmed in production).
Reported by the owner but **not inspected by me**: all exposed keys rotated and old Firebase service-account key deleted (SEC-006); Atlas user restricted to
`readWrite` on `crate_scan`; Firebase Google-only sign-in, authorised domains, and Firestore / Realtime Database / Storage disabled or deny-all.
Owner decision: the Firebase web API key is **not** being restricted in Google Cloud for now (accepted risk; the key is public by design and the API still requires an approved account).
Strictly applied, the verdict criteria require core areas to be inspected rather than assumed, so the formal verdict stays at the level below until the three owner-reported
items are shown (screenshots or read-only exports); the remaining risk is limited to the owner's own dashboard settings, not to the application code.
