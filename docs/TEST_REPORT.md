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
