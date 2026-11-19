# Phase 1 Handoff — Backend (FastAPI · MongoDB Atlas · Firebase Auth)

**Project:** CRATE-SCAN (repo `DubbakaSathwik/Food_inspection_toolkit`, branch `feature/initial-build`)
**Phase status:** ✅ Phase 1 complete — backend implemented and verified locally (frontend not started)
**Date:** 2026-11-19

---

## 1. What Phase 1 delivered

| Area | Where | Notes |
|------|-------|-------|
| App factory, middleware | `backend/app/main.py` | CORS allow-list, body-size limit (413), security headers, slowapi rate limits, uniform error JSON, docs off in production |
| Config | `backend/app/config.py`, `backend/.env.example` | Every variable documented; no secrets in code |
| Auth | `backend/app/auth.py`, `routers/me.py` | Firebase ID-token verification on every protected route; custom claims `{role, active}` + DB status; `claims_stale` refresh flow; revocation check on admin writes; `SUPER_ADMIN_EMAIL` bootstrap; invitations |
| Data-access layer | `backend/app/repositories/*` | Only code touching MongoDB/GridFS; `owner_uid` on all user data; 404 for foreign IDs; `ensure_admin()` on admin paths; architecture test enforces it |
| Models | `backend/app/models/*` | Pydantic request (extra=forbid) and response models; `openapi.json` exported |
| Files | GridFS buckets `photos` / `reports` / `refimages` / `siteimages` | Temporary originals with retention + cleanup; PDFs permanent |
| AI | `backend/app/services/ai/*` | Gemini → NVIDIA → Hugging Face → optional PaddleOCR → `incomplete`+retry; full-quality originals; resize only above provider limits; `fake` provider (dev/test only); per-user daily quota |
| Domain services | `services/workflow.py`, `matching.py`, `compliance.py`, `classification.py`, `report_pdf.py`, `importer.py`, `maintenance.py` | 22 fields / 7 groups, validation, corrections with history, reference matching, demo licence check, packaging comparison, compliance engine, provisional suggestion, 13-section PDF |
| Migrations | `backend/migrations/m0001…m0003` + `scripts/migrate.py` | `$jsonSchema` validators (strict), indexes, fictional demo seed (5 reference records, 17 demo rules) |
| Scripts | `backend/scripts/` | `migrate`, `grant_role`, `cleanup`, `export_openapi` |
| Tests | `backend/tests/` | 59 tests against real MongoDB + Auth emulator |
| Docs | `docs/DATABASE.md`, `docs/TEST_REPORT.md`, `backend/README.md`, updated `DECISIONS.md` (T-12…T-22), `FEATURE_MATRIX.md`, `IMPLEMENTATION_PLAN.md`, `PROJECT_STATE.md` | |

### API surface (58 paths, `/api/v1`)
- **Public:** `GET /health`, `GET /public/site-images[/{key}]`
- **Me:** `GET/PATCH /me`
- **Inspector:** `/inspector/dashboard`; `/inspections` (list, filters, export CSV/XLSX, create, get, delete draft);
  `/photos` (upload, get + `?thumb`, label/crop, delete); `/extract`; `/fields/{key}`; `/fields/confirm`; `/category`;
  `/analyze`; `/findings/{id}`; `/decision`; `/report` + `/report.pdf`; `/notes`; `/reference-images/{id}`;
  `/proposals` (create, list, get, reply); `/assistant/messages` (history, ask with `web`, clear)
- **Admin:** `/admin/dashboard`; `/admin/reference` (CRUD, stats, archive/restore, delete = Super Admin, versions, images,
  `ai-extract`, `import/preview`, `import/commit`); `/admin/rules` (+ stats, archive); `/admin/proposals` (+ report.pdf,
  decision); `/admin/users` (+ detail, approve, decline, patch, invites); `/admin/analytics`; `/admin/audit` (+ export);
  `/admin/settings` (+ images); `/admin/storage` (+ cleanup)

## 2. Verification (real results — details in `docs/TEST_REPORT.md`)
| Check | Result |
|-------|--------|
| `ruff check` / `ruff format --check` | ✅ clean |
| `mypy` strict (app, migrations, scripts) | ✅ 0 issues |
| `bandit` | ✅ 0 issues |
| `pip-audit` (runtime deps) | ✅ no known vulnerabilities |
| `pytest --cov` | ✅ 59 passed · 89 % coverage |
| Migrations run twice | ✅ idempotent |
| `uvicorn` smoke test | ✅ `/health` ok, 401 JSON for unauthenticated calls |
| Sample PDF visual check | ✅ 13 sections in order |

**Not verified:** real Gemini/NVIDIA/HF calls (no keys; adapters tested against mocked HTTP only), real PaddleOCR, rate
limits (disabled in tests), Atlas cluster (local Mongo used).

## 3. Decisions made in Phase 1 (see `docs/DECISIONS.md` T-12…T-22)
- 22 extraction fields (design is authoritative, not "24").
- Analysis requires every non-auto field to be confirmed/edited; editing after analysis marks it stale.
- Completed inspections are immutable except follow-up notes; originals deleted at report time.
- Admin role grants only by Super Admin; no self role/status changes; last Super Admin protected.
- `user_invites` collection for pre-authorised emails (verified email only).
- Cleanup is opportunistic (no cron on Render free) + script + admin button.

## 4. How to run what exists now
```bash
docker run -d --name cs-mongo -p 27017:27017 mongo:7         # or mirror.gcr.io/library/mongo:7
firebase emulators:start --only auth --project demo-cratescan  # repo root (firebase.json present)
cd backend && cp .env.example .env                             # set FIREBASE_AUTH_EMULATOR_HOST, AI_PROVIDER_ORDER=fake
uv sync && uv run python -m scripts.migrate
uv run uvicorn app.main:app --reload --port 8000               # http://localhost:8000/docs
uv run pytest --cov=app
```

## 5. Notes for Phase 2 (frontend)
- Generate TS types from `backend/openapi.json` (`openapi-typescript`); regenerate with `uv run python -m scripts.export_openapi`.
- Error format: `{"error":{"code","message","fields"?}}`. Codes the UI must handle: `unauthenticated`, `claims_stale`
  (call `getIdToken(true)` then retry once), `account_pending` / `account_declined` / `account_disabled` (→ `/pending`
  or sign-out), `fields_unconfirmed` (highlight `fields` keys), `analysis_stale`, `invalid_state`, `too_many_photos`,
  `ai_quota_exceeded` (429), `rate_limited`, `payload_too_large`, `unsupported_image`, `validation_error` (field map).
- `/me` returns `claims_stale: true` after approval/role change → force token refresh.
- Images: inspection photos and PDFs need the Bearer token → fetch as blob + `URL.createObjectURL` (no plain `<img src>`).
  Site images are public URLs (`/api/v1/public/site-images/{key}?v=…`).
- Extraction/analysis can take up to ~60 s per provider attempt with real AI — keep the AI-reading / AI-review
  animations running until the request resolves (not fixed timers).
- Demo values must stay labelled ("Demo" / "Sample") per BR-03 and the design.

---

## 6. ▶ PROMPT TO START PHASE 2 (copy into the next session)

```
You are continuing the CRATE-SCAN build in repo DubbakaSathwik/Food_inspection_toolkit,
branch feature/initial-build. Follow the MASTER BUILD PROMPT rules, but work PHASE BY PHASE:
complete only Phase 2, then stop and write docs/handoffs/PHASE_2_HANDOFF.md (same structure
as PHASE_1_HANDOFF.md, ending with the prompt to start Phase 3). Commit and push to
feature/initial-build.

Before coding, read: PROJECT_STATE.md, docs/DECISIONS.md, docs/PROJECT_SPEC.md,
docs/FEATURE_MATRIX.md, docs/ARCHITECTURE.md, docs/DATABASE.md, docs/handoffs/PHASE_1_HANDOFF.md
(§5 notes for the frontend), design/CLAUDE_CODE_HANDOFF.md. Do not re-ask the deployment gate.

PHASE 2 — FRONTEND (tasks T12–T15) in /frontend:
- Next.js 16 App Router + React 19 + TypeScript strict + Tailwind v4 with design tokens from
  design/design-system/tokens.css as CSS variables (@theme); global motion/hover/ripple/loader
  rules from design/design-system/*.css; Manrope via @fontsource-variable/manrope; pnpm.
- Icon component from design/assets/icons (47 SVGs, stroke 1.6) + mobile tab-bar icons; Logo.
- Components per handoff §5: Button, IconButton, Chip/Pill, Card, Metric, Sidebar, MobileTopBar,
  BottomTabBar, DataTable→stacked cards ≤760px, Stepper (+compact), Field/Select/SearchBox,
  ImageSlot (site images from /api/v1/public/site-images), PackIllustration (demo only), DemoNote,
  PhotoStrip+PhotoPreview, FieldCard, FindingCard, DecisionControl, AIWorkingOverlay,
  ReportDocument, Loader+TopProgress, StartingServer state.
- All 22 screens, one component per screen with desktop (1440) and mobile (390) layouts per
  design/screenshots and design/source (breakpoint 760px; no horizontal scroll; tablet = desktop).
  Routes: /, /signin, /pending, /inspector, /inspector/new, /inspector/verify/[id],
  /inspector/ai-review/[id], /inspector/findings/[id], /inspector/report/[id],
  /inspector/history, /inspector/proposals, /inspector/ask, /inspector/profile, /admin,
  /admin/reference, /admin/reference/[id], /admin/rules, /admin/proposals, /admin/users,
  /admin/analytics, /admin/audit, /admin/settings.
- Typed API client (types generated from backend/openapi.json) that attaches the Firebase ID
  token, retries once on claims_stale, maps error codes; Firebase Web SDK Google sign-in
  (popup with redirect fallback) and an auth/role context with route guards; /health warm-up and
  "starting server" state with retry/backoff. Wire screens to the real endpoints where the
  backend exists (that is integration-ready code); full end-to-end verification is Phase 3.
- frontend/.env.example (NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_FIREBASE_*,
  NEXT_PUBLIC_USE_AUTH_EMULATOR); netlify.toml with security headers.
- Accessibility basics, loading/empty/error/success states, reduced motion.
- Checks: tsc --noEmit, ESLint, Prettier, Vitest for key components, production build; Playwright
  screenshots of every route at 1440 and 390 compared with design/screenshots (no horizontal
  overflow). Record real results in docs/TEST_REPORT.md; update FEATURE_MATRIX, PLAN, STATE.
Stop after Phase 2 and deliver the Phase 2 handoff doc.
```
