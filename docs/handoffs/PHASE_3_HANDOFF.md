# Phase 3 Handoff — Backend–Frontend Integration (end-to-end journeys)

**Project:** CRATE-SCAN (repo `DubbakaSathwik/Food_inspection_toolkit`, branch `feature/initial-build`)
**Phase status:** ✅ Phase 3 complete — every mandatory feature driven through the real UI against the real API + MongoDB, desktop and mobile
**Date:** 2026-11-19

---

## 1. What Phase 3 delivered

| Area | Where | Notes |
|------|-------|-------|
| Local integration stack | `scripts/local-stack.sh [--fresh]` | MongoDB (Docker) + Firebase Auth emulator + API (fake AI) + Next.js production build; `--fresh` resets data and runs `scripts/dev_seed.py` |
| E2E journeys | `frontend/e2e/j1-accounts`, `j2-inspection`, `j3-proposals`, `j4-admin`, `j5-assistant-coldstart`, `j6-security` (+ Phase 2 `screens`) | Real clicks, file uploads, crop drag, downloads; unique users per test; both viewports |
| Fixtures & helpers | `frontend/e2e/fixtures/*.png`, `e2e/helpers.ts` | Emulator sign-in, approved-user creation, API shortcut to a completed inspection |
| Test hook | `backend/app/services/ai/fake.py` (`CRATESCAN_FAKE_FAIL` marker) | Fake provider only (dev/test); drives the outage → retry journey (T-32) |
| Defect fixes | `components/ui.tsx` Modal, `lib/api.ts` + `lib/auth.tsx`, `tests/conftest.py`, `scripts/dev_seed.py` | See §3 |
| Docs | `docs/TEST_REPORT.md` (Phase 3), `docs/DECISIONS.md` (T-32…T-37), `FEATURE_MATRIX.md` (☑ per journey), PLAN, STATE | |

## 2. Verification (real results — `docs/TEST_REPORT.md` Phase 3)
| Check | Result |
|-------|--------|
| Playwright: 6 journey specs + screen sweep, desktop 1440 + mobile 390 | ✅ 36 passed · 2 skipped by design (API-level checks once) |
| Previously failing disable journey, repeated ×3 per viewport | ✅ 6/6 |
| Frontend typecheck / lint / format / Vitest | ✅ clean · 9 passed |
| Backend ruff / mypy / bandit / pytest | ✅ clean · 0 issues · 60 passed, 89 % |
| Direct-API authorization checks | ✅ 401 / 403 / 404 / 422 / 405 as designed; no secrets or private data in `.next/static` |
| Audit for TODOs, mock data, dead buttons | ✅ none in production paths |

FEATURE_MATRIX: **F01–F15, F18–F20 ☑**; **F16 Analytics, F17 Audit ◐** (rendered with live data; their filters/export not clicked through).

## 3. Defects found and fixed (with regression checks)
1. **Dialog switching** — "Add Product" menu → sub-dialog closed immediately (programmatic `close` fired `onClose`) → `Modal` reports only user closes (T-34); Vitest regression proven to fail without the fix.
2. **Admin demoted in an open session** stayed in the admin area → client reloads `/me` on `403 forbidden` (T-33).
3. **Disabled user in an open session** stuck on "Checking your access…" (token refresh refused after revocation) → keep the non-active profile and show the "account disabled" screen (T-37).
4. **Backend tests wiped all emulator accounts**, breaking the shared dev stack → removed (T-35).
5. **Dev seed** used a token issued before the bootstrap role claim → re-issues the token.

## 4. How to run
```bash
MONGO_IMAGE=mongo:7 scripts/local-stack.sh --fresh   # repo root; prints URLs when ready (web :3000, api :8000, emulator :9099)
cd frontend && pnpm exec playwright test             # all journeys + sweep, both viewports (~3.5 min)
pnpm exec playwright test e2e/j2-inspection.spec.ts --project desktop --headed   # watch one journey locally
cd ../backend && uv run pytest --cov=app
```
Seeded accounts: `admin@example.com` (Super Admin), `inspector@example.com`, `pending.person@example.com`. Journeys create their own users.

## 5. Notes for Phase 4 (CI/CD, security, docs, acceptance)
- **CI services:** MongoDB service container (`mongo:7`), Firebase Auth emulator (`npx firebase-tools emulators:start --only auth` needs Java),
  backend with `APP_ENV=test`/`development` + `AI_PROVIDER_ORDER=fake`, frontend `pnpm build && pnpm start` with emulator env vars, then
  `pnpm exec playwright install --with-deps chromium` and `pnpm exec playwright test`. Upload traces/screenshots on failure.
- Coverage threshold suggestion: backend `--cov-fail-under=85` (currently 89 %).
- Deploy job: Render deploy hook → poll `/health` → Netlify CLI deploy; turn off both hosts' auto-deploys (master prompt §11).
- Production config: `SUPER_ADMIN_EMAIL`, `FIREBASE_SERVICE_ACCOUNT_JSON`, `MONGODB_URI`, `CORS_ALLOWED_ORIGINS` (Netlify URL), AI keys
  (owner), `APP_ENV=production` (refuses the fake provider and the emulator host); Render start command
  `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`. Check Render's current Python/uv support.
- Rate limits are disabled in tests (T-22): verify manually against a running `APP_ENV=development` instance.
- Real Google sign-in and real AI providers need the owner's Firebase project and keys — list them in DEPLOYMENT.md as manual steps.
- Still open: F16/F17 UI filters (◐), PaddleOCR (optional), real-provider verification (U-02).

---

## 6. ▶ PROMPT TO START PHASE 4 (copy into the next session)

```
You are continuing the CRATE-SCAN build in repo DubbakaSathwik/Food_inspection_toolkit,
branch feature/initial-build. Follow the MASTER BUILD PROMPT rules, but work PHASE BY PHASE:
complete only Phase 4, then stop and write docs/handoffs/PHASE_4_HANDOFF.md (same structure,
ending with the final project status and the owner's next steps). Commit and push to
feature/initial-build. Do not deploy anything yourself.

Before coding, read: PROJECT_STATE.md, docs/DECISIONS.md, docs/PROJECT_SPEC.md,
docs/FEATURE_MATRIX.md, docs/ARCHITECTURE.md, docs/DATABASE.md, docs/TEST_REPORT.md,
docs/handoffs/PHASE_3_HANDOFF.md (§5 notes). Do not re-ask the deployment gate.

PHASE 4 — TESTING, SECURITY, CI/CD, FINAL ACCEPTANCE (tasks T17–T19):
- GitHub Actions .github/workflows/ci.yml per master prompt §11: quality (ESLint, Prettier,
  tsc, Ruff, Ruff format, mypy, actionlint) → tests (pytest with coverage threshold against a
  MongoDB service container + Firebase Auth emulator, migrations run twice, Vitest, Playwright
  journeys at desktop+mobile against the built app, artifacts on failure) → security
  (gitleaks, pip-audit, pnpm audit high/critical, Bandit, CodeQL for Python + JS/TS, frontend
  bundle secret scan, data-access-layer rule) → build (Next.js for Netlify, backend start check
  for Render) → deploy (main only, F1: Render deploy hook → wait /health → Netlify CLI) →
  post-deploy smoke test. Pinned actions, least permissions, concurrency cancel.
- .github/dependabot.yml (npm, pip/uv, github-actions weekly) and
  .github/workflows/security-scheduled.yml (weekly + manual; optional health check per §12
  after checking Render's terms on keep-alive pings).
- Render config for the backend (render.yaml or documented settings; uv build, start command
  with $PORT, /health), Netlify already in netlify.toml; disable host auto-deploys.
- Security review per master prompt §4.6 (manual rate-limit check, CORS, headers, NoSQL
  injection, secrets, Atlas user/network notes) and finish F16/F17 UI journeys if feasible.
- Validate workflows locally (actionlint) and run every CI command locally first; push and
  report the real GitHub Actions result.
- Documentation: README.md (root), SECURITY.md, DEPLOYMENT.md (Atlas, Firebase, Render,
  Netlify, GitHub secrets/branch protection/Dependabot, migrations in production, cold
  starts, rollback, pre-launch checklist), finalize TEST_REPORT.md, HANDOFF.md, and assign the
  truthful overall status (COMPLETE AND VERIFIED / IMPLEMENTED WITH DOCUMENTED LIMITATIONS /
  BLOCKED).
Stop after Phase 4 and deliver the Phase 4 handoff doc.
```
