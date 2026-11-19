# CRATE-SCAN — Test Report

Results are recorded exactly as executed. "Not run" items are listed with the reason.

## Phase 1 — Backend (2026-11-19)

**Environment:** Linux container · Python 3.12 (uv) · MongoDB 7.0 in Docker (`mirror.gcr.io/library/mongo:7`) ·
Firebase Auth emulator (firebase-tools 14.27, project `demo-cratescan`) · AI provider `fake` (deterministic test
provider) · real Gemini / NVIDIA / Hugging Face **not called** (no keys).

| Check | Command (in `backend/`) | Result |
|-------|-------------------------|--------|
| Lint | `uv run ruff check .` | ✅ All checks passed |
| Format | `uv run ruff format --check .` | ✅ 73 files formatted |
| Types | `uv run mypy app migrations scripts` (strict) | ✅ No issues in 63 files |
| Security static analysis | `uv run bandit -c pyproject.toml -r app migrations scripts` | ✅ 0 issues (B101 asserts skipped; security-relevant asserts replaced by `ensure_admin`, T-21) |
| Dependency audit | `uv export --no-dev --no-hashes --no-emit-project > req.txt && uv run pip-audit -r req.txt` | ✅ No known vulnerabilities |
| Tests + coverage | `uv run pytest --cov=app` | ✅ **59 passed**, coverage **89 %** |
| Migrations | `python -m scripts.migrate` twice on empty DB | ✅ 1st: 3 applied · 2nd: nothing applied; `test_migrations_idempotent` re-runs every `up()` |
| Server start | `uvicorn app.main:app` + `curl /health` | ✅ `{"status":"ok","database":"ok"}`; unauthenticated `/api/v1/me` → 401 JSON error; 58 OpenAPI paths |
| PDF visual check | sample report rendered to PNG and inspected | ✅ 13 sections in order, photos embedded, tables readable |

### What the tests cover
- **Auth (real token verification via emulator):** missing / malformed / oversized tokens → 401; pending users blocked
  (403 `account_pending`); Super Admin bootstrap; unverified email never bootstraps; approval → `claims_stale` →
  refresh; disable blocks immediately; demotion removes admin access; role-escalation attempts (body fields, inspector
  calling admin APIs, admin granting admin roles, self-changes) rejected; last Super Admin protected; invitations.
- **Isolation:** inspector B gets 404 for A's inspection, photo, extraction, field edit, note, report, delete; lists
  never include others' data; Ask-AI context cannot use another inspector's inspection; proposals isolated.
- **Workflow:** upload validation (decoded image, empty, non-image, 5-photo cap), blur warning, crop validation, thumbnails,
  extraction with 22 fields, auto-confirm vs pending, corrections keep `ai_value` + history, licence-format validation,
  analysis blocked until fields reviewed, findings (reference, licence, compliance, claims), finding decisions,
  provisional suggestion, decision/report gating, PDF section order + signature disclaimer, originals deleted after
  report, completed inspections immutable, follow-up notes, history filters, NoSQL-operator text treated literally,
  page-size limit, CSV/XLSX export, provider failure → `incomplete` with evidence kept → retry succeeds, daily AI quota
  429, retention cleanup.
- **Admin:** reference CRUD/archive/restore, delete Super-Admin-only, audit entries, packaging versions + images,
  AI-assisted draft (not saved), CSV + XLSX import preview/commit, rules create/validate/version history/archive,
  proposal lifecycle (report required, info request → reply, approve → demo reference record, no re-decision),
  settings + site images (public read), analytics/storage/audit export, audit read-only.
- **Providers (mocked HTTP — not proof of real API behaviour):** Gemini sends the full-quality original, key in header
  not URL, web-research tool only when requested, grounding sources parsed, HTTP errors; OpenAI-compatible merge for
  single-image models; chain skips unconfigured providers and records attempts; OCR unavailable path; fake provider
  refused in production; secret scrubbing in error messages; resize only above a limit.
- **Architecture:** routers never import `app.db`/`pymongo`/`gridfs` or call collection methods; every non-public route
  depends on token verification.

### Not run / not verified in Phase 1
| Item | Reason |
|------|--------|
| Real Gemini / NVIDIA / Hugging Face calls | No API keys (owner adds keys in `.env`; D-10). |
| PaddleOCR fallback with the real engine | Optional extra not installed (D-06); code path tested for "unavailable". |
| Rate limiting (slowapi) | Disabled in `APP_ENV=test` (T-22); to be checked manually in Phase 4. |
| Atlas production cluster | Not provisioned in this session; local MongoDB 7 used. |
| Frontend, end-to-end, CI | Phases 2–4. |

## Phase 2 — Frontend (2026-11-19)

**Environment:** Node 22.23 · pnpm 10.28 · Next.js 16.4.6 (production build served with `next start`) · React 19.3 · Tailwind 4.3 ·
Playwright 1.63 (Chromium) · backend from Phase 1 on :8000 with `AI_PROVIDER_ORDER=fake`, MongoDB 7 (Docker), Firebase Auth emulator ·
data from `backend/scripts/dev_seed.py`. Re-run from a clean restart (services restarted, dev DB reset).

| Check | Command (in `frontend/`) | Result |
|-------|--------------------------|--------|
| Types | `pnpm typecheck` (strict) | ✅ no errors |
| Lint | `pnpm lint` (ESLint 9 + next config incl. React Hooks rules) | ✅ 0 errors, 0 warnings |
| Format | `pnpm format:check` | ✅ all files formatted |
| Unit/component tests | `pnpm test` (Vitest + Testing Library) | ✅ 8 passed (chips/labels, routing helper, stepper a11y, report 13-section order, API client: token header, `claims_stale` refresh+retry, error mapping, cold-start retry) |
| Production build | `pnpm build` | ✅ 22 app routes + not-found + icon |
| Screen sweep | `pnpm exec playwright test` | ✅ 10 passed — every route at 1440×900 and iPhone 14 (390): page renders, **no horizontal overflow**, **no console errors**; screenshots in `docs/screens/phase2/` |
| Backend regression | `uv run pytest --cov=app` (backend) | ✅ 59 passed, 89 % coverage; ruff/mypy/bandit clean |

### Visual comparison with `design/screenshots`
Side-by-side comparisons were made for Main, InspectorDashboard, NewInspection, VerifyFields, AIReview, InspectionResults, ReportPreview,
History, AskAI, AdminDashboard, ProductDetail, UserManagement, Analytics (desktop) and Main, AIReview, ReportPreview, InspectorDashboard
(mobile). Layout, tokens, typography, components and the ≤760 px mobile shell match. **Not pixel-perfect**; known, intentional
differences are listed in `DECISIONS.md` T-24…T-28 (validation flags instead of OCR chips, no Privacy/Terms links, no history PDF export,
validated chart colours). Values differ from the design because the screens show real API data, not the design's sample values.

### Notes / not verified in Phase 2
| Item | Status |
|------|--------|
| Real Google sign-in popup / redirect | Not testable here; emulator sign-in used (T-30). Verified in Phase 3/4 with a real Firebase project. |
| `apis.google.com` | Unreachable from the sandbox; Firebase preloads it on mobile user agents. Filtered in the sweep (environment limit). |
| Full user journeys (create → report, admin approve proposal…) through the UI | Phase 3 (the screens call the real endpoints; the sweep only renders them). |
| Netlify deploy, CSP in a real browser | Phase 4. |

## Phase 3 — Integration and end-to-end journeys (2026-11-19)

**Environment:** `scripts/local-stack.sh --fresh` → MongoDB 7 (Docker), Firebase Auth emulator, FastAPI with the fake AI provider
(`AI_PROVIDER_ORDER=fake`), Next.js **production** build on :3000. Browsers: Chromium 1440×900 ("desktop") and iPhone 14 profile 390
("mobile"). Every journey creates its own uniquely named users and data through the real UI (fixtures: `frontend/e2e/fixtures/*.png`).

| Check | Command | Result |
|-------|---------|--------|
| End-to-end journeys + screen sweep | `cd frontend && pnpm exec playwright test` | ✅ **36 passed**, 2 skipped (API-level security checks run once, on desktop) — 3.3 min |
| Repeat of the previously failing disable journey | `--repeat-each 3` (desktop + mobile) | ✅ 6/6 |
| Frontend static + unit | `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test` | ✅ clean · 9 Vitest passed |
| Backend | `uv run ruff check`, `ruff format --check`, `mypy`, `bandit`, `pytest --cov=app` | ✅ clean · 0 bandit issues · 60 passed, 89 % coverage |

### Journeys (all passed on desktop and mobile)
Accounts (pending → approval in the admin UI → access with claims refresh; disable in an open session; admin demotion in an open session) ·
full inspection (3 photos incl. blurry warning, crop, AI reading, correction with original AI value kept, confirm all, AI review, finding
decisions with reasons, classification, remarks, report, PDF download `%PDF` > 20 KB, follow-up note, history filter, CSV + Excel export,
another inspector gets "Inspection not found" on findings/report/verify URLs) · AI outage → incomplete → dashboard badge → change photo →
retry → fields · proposal submit → info request → reply → approve → new demo reference record visible in the reference database · reference
manual entry with server-side licence validation shown in the form, packaging version + photo, archive/restore, record history · AI-assisted
draft (not saved) · CSV import preview (1 valid, 1 invalid) and commit · compliance rule create/edit → v2 in history · website hero image
upload visible to an anonymous visitor on `/`, then reset · Ask AI without web (no sources) and with web research (sources), history kept
after reload · cold start: API unreachable → "Starting the server…" → recovers and loads data · direct API calls: no/forged token 401,
other owner 404, inspector on admin APIs 403, role escalation 422, pending account 403, audit log DELETE 405 · `.next/static` contains no
connection strings, keys or seeded emails.

### Defects found and fixed in Phase 3 (each with a regression check)
| # | Defect | Fix | Regression check |
|---|--------|-----|------------------|
| 1 | Choosing an option in the "Add Product" menu closed the newly opened dialog (programmatic `<dialog>.close()` fired `onClose`). | `Modal` reports only user-initiated closes (T-34). | Vitest "Modal … dialog switching regression" (fails without the fix) + `j4-admin` |
| 2 | A demoted admin stayed in the admin area with failing pages until reload. | Client reloads `/me` on `403 forbidden` (T-33). | `j1-accounts` demotion journey |
| 3 | A disabled user in an open session was stuck on "Checking your access…" (forced token refresh refused after revocation). | Keep the non-active profile when the refresh fails (T-37). | `j1-accounts` disable journey (×3 per viewport) |
| 4 | Backend test setup wiped all emulator accounts, breaking a shared dev stack. | Removed the global wipe (T-35). | Backend suite + e2e run back to back |
| 5 | `dev_seed.py` kept a token from before the bootstrap role claim existed (401 on a fresh emulator). | Re-issue the token when `/me` reports `claims_stale`. | `local-stack.sh --fresh` |

### Audit
No `TODO`/`FIXME`/mock markers in `frontend/src` or `backend/app`; every `<Button>` has a handler or is a submit/disabled state; the only
illustrative content is labelled ("Sample preview" on the landing page, pack illustration only when a photo is unavailable).

### Not verified in Phase 3
Real Google sign-in popup/redirect and real Firebase project · real AI providers (no keys) · PaddleOCR · rate limits (disabled in tests) ·
Analytics/Audit filters clicked through the UI (rendered with live data; audit export covered by backend tests) · deployment (Phase 4).

## Phase 4 — CI/CD, security review, final checks (2026-11-19)

### Local runs (same commands as CI)
| Check | Result |
|-------|--------|
| ruff check / ruff format --check / mypy strict (backend) | clean (55 source files) |
| OpenAPI export + generated frontend types | no drift |
| ESLint / Prettier / tsc (frontend) | clean |
| pytest with coverage gate `--cov-fail-under=85` | **64 passed**, coverage **89.45 %** |
| Vitest (now vitest 5) | 9 passed |
| Playwright full suite, desktop 1440 + mobile iPhone 14 (fresh stack) | **40 passed, 2 skipped** (skips are by design, unchanged from Phase 3) |
| j7 analytics/audit journeys (new) | passed on desktop and mobile (F16, F17 now ☑) |
| Production-mode start (`APP_ENV=production`, Render start command) | `/health` 200 ok, `/docs` 404, `/api/v1/me` 401, HSTS present; emulator host refused in production |
| actionlint 1.7.12 on all workflows | clean |
| gitleaks 8.30.1 (full history) | no leaks |
| pip-audit 2.10.0 | no known vulnerabilities |
| pnpm audit (high) | was 1 high + 2 critical → fixed (vitest 5, @grpc/grpc-js override) → none |
| Bandit | clean |
| Bundle secret scan (`scripts/scan-bundle.sh`) | clean |

### Defects found in Phase 4
1. **Rate limiting was not enforced** (slowapi middleware never matched our routes). Replaced by `app/ratelimit.py`; verified
   live (`200 200 200 200 429 429 429`, `Retry-After`, CORS on 429) and by `tests/test_ratelimit.py` (T-38).
2. Vulnerable dev/transitive JavaScript dependencies (see table) — upgraded/overridden.
3. **Unstable ordering** (found by the first GitHub Actions run): two chat messages written in the same millisecond could come back
   in the wrong order, and any paged list with equal timestamps could repeat/skip items between pages. `paginate()` now always adds
   an `_id` tiebreaker; `test_assistant.py` re-run repeatedly.
4. `HEAD /health` returned 405 (uptime monitors use HEAD) — now 200, hidden from the schema; tested.

### GitHub Actions
- Run 1 (`44542170646`, commit 13a26d9): Quality ✓, CodeQL Python ✓, CodeQL JS/TS ✓; Security ✗ (only the DAL-rule step: it loaded
  the DB fixture without a database — now runs with `--noconftest`; gitleaks/pip-audit/Bandit passed); Tests ✗ (defect 3 above).
- Run 2 (`44542863042`, commit d123a6e): **success** — Quality ✓, Security ✓ (gitleaks, pip-audit, Bandit, DAL rule, pnpm audit),
  CodeQL Python ✓, CodeQL JS/TS ✓, Tests ✓ (pytest 64 passed / 89.45 %, Vitest 9 passed, Playwright 40 passed + 2 skipped on
  desktop and mobile), Build ✓ (bundle scan clean, production start `/health` ok). Deploy and smoke: skipped as designed (they run
  only on pushes to `main`; no deployment secrets exist yet).

- Run 3 (`44545482817`, commit 73678c9, docs only): Tests ✗ — flaky e2e assertion in `j2-inspection` (after "Confirm issue"
  the card shows that text on both the status chip and the still-present button; Playwright strict mode found two matches depending
  on timing). Test now asserts on the status chip; j2 re-run 3× on desktop and mobile locally: 12/12 passed. App code unchanged.

### Not verified in Phase 4
Deploy and smoke jobs (need `main` + owner's Render/Netlify secrets) · real Google sign-in · real AI providers · Atlas ·
Render's handling of `render.yaml` (render.com docs were not reachable from the build environment; values follow standard Render
Python settings and are documented as manual fallback in `docs/DEPLOYMENT.md` §3).

### New tests
`tests/test_ratelimit.py` (limit parsing, buckets, 429 format), `test_health.py` (HEAD, NoSQL operator objects rejected /
treated as literal text), e2e `j7-analytics-audit.spec.ts`.

## Post-handoff addition — Admin diagnostics page (2026-11-19)
Requested by the owner after local testing with real keys failed with opaque errors ("HTTP 503/410/403").
- New page **Admin → Diagnostics** (`/admin/diagnostics`) and endpoints `GET /api/v1/admin/diagnostics`,
  `POST /api/v1/admin/diagnostics/{check}`: configuration sanity (placeholders, example admin email, CORS), MongoDB, GridFS,
  Firebase service account (live call), a live test call to each configured AI provider (Gemini, NVIDIA, Hugging Face) and OCR.
  Each result shows status, the real reason and fix hints; no keys, passwords or URIs are ever returned. Admin-only.
- Provider errors now include the provider's own reason (e.g. `HTTP 403 — API key not valid`) via `http_error()`.
- Tests: `test_diagnostics_admin_only_and_secret_free` (65 backend tests, 88.6 %), e2e `diagnostics` journey (desktop + mobile;
  j7 + screens 16/16 passed). Real-provider results themselves are not verifiable from the build environment.

### AI provider overload handling (2026-11-19)
Real-key testing showed Gemini returning `HTTP 503 — high demand`. Providers now retry temporary 5xx answers twice
(after 2 s, then 5 s) before the chain moves to the next provider (`post_with_retry`). Tests: 503 → retry → success, and a persistent 503
reports the provider's own reason. 67 backend tests passed (88.6 %). Not verified against the live Gemini service.
