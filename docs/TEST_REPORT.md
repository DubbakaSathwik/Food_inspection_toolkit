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
