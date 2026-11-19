# Phase 2 Handoff — Frontend (Next.js · React · Tailwind · Firebase Web SDK)

**Project:** CRATE-SCAN (repo `DubbakaSathwik/Food_inspection_toolkit`, branch `feature/initial-build`)
**Phase status:** ✅ Phase 2 complete — all 22 screens built (desktop + mobile), wired to the real API, verified by rendering
**Date:** 2026-11-19

---

## 1. What Phase 2 delivered

| Area | Where | Notes |
|------|-------|-------|
| App foundation | `frontend/` (Next.js 16.4, React 19.3, TS strict, Tailwind 4.3, pnpm) | `cacheComponents` off (T-23); Manrope via `@fontsource-variable/manrope` |
| Design system | `src/app/globals.css` | Tokens from `design/design-system/tokens.css` as CSS variables + Tailwind `@theme`; hover/ripple/press, page-enter stagger, loader + top progress bar, AI animations, `prefers-reduced-motion`; ≤760 px mobile shell rules (top bar, bottom tab bar, stacked-card tables, 2-col grids, compact stepper) |
| Icons & logo | `src/components/icon.tsx`, `icon-paths.ts` (generated from the 47 design SVGs + 9 tab-bar icons), `ui.tsx` `Logo` | `pnpm gen:icons` |
| Components | `src/components/ui.tsx` (Button + ripple, ButtonLink, IconButton, Chip/Pill, Panel, Metric, DemoNote, Notice, ErrorBox, Empty, Skeleton, Backlink, TextLink, TextField, TextArea, SelectField, SearchBox, Modal), `shell.tsx` (AppShell: Sidebar, MobileTopBar, BottomTabBar; PageHeader; RouteProgress loader; StartingServer banner), `inspection.tsx` (Stepper + compact, AIWorkingOverlay, CropDialog), `report.tsx` (ReportDocument, print ⇄ mobile view), `media.tsx` (ImageSlot for site images, AuthImage/useBlobUrl for authenticated photos, PackIllustration), `charts.tsx`, `reference-form.tsx`, `profile-view.tsx`, `auth-layout.tsx` | |
| Data & auth | `src/lib/api.ts`, `api-types.ts` (generated from `backend/openapi.json`), `auth.tsx`, `firebase.ts`, `env.ts`, `inspection.ts` | Bearer ID token on every call; one forced refresh + retry on `claims_stale`/`unauthenticated`; uniform `ApiError` (code, message, field map); cold-start retry with backoff + `/health` warm-up + "Starting the server…" banner; Google popup with redirect fallback; route guards by role/status |
| Screens (22) | `src/app/**/page.tsx` | `/`, `/signin`, `/pending`, `/inspector` (+ `new`, `verify/[id]`, `ai-review/[id]`, `findings/[id]`, `report/[id]`, `history`, `proposals`, `ask`, `profile`), `/admin` (+ `reference`, `reference/[id]`, `rules`, `proposals`, `users`, `analytics`, `audit`, `settings`) |
| Config | `frontend/.env.example`, root `netlify.toml` (security headers + CSP, T-29) | Only `NEXT_PUBLIC_*` values in the frontend |
| Tests | `src/__tests__/` (Vitest, 8), `e2e/` (Playwright sweep + helpers), `playwright.config.ts`, `vitest.config.ts` | |
| Backend changes | `app/config.py` + `app/auth.py` (emulator host from settings, refused in production), `InspectionOut.analysis_stale`, `scripts/dev_seed.py` | T-31 |
| Docs | `docs/TEST_REPORT.md` (Phase 2), `docs/DECISIONS.md` (T-23…T-31), `frontend/README.md`, `docs/screens/phase2/` (44 screenshots), FEATURE_MATRIX, PLAN, STATE | |

### Screen behaviour highlights
- **New Inspection:** category radio cards (saved via API), camera + gallery + drag-and-drop upload, horizontal photo strip (never wraps), preview with green/orange border and "Issue found in Photo N" note from the server quality check, side label select, crop dialog (drag rectangle; original untouched), replace/remove, capture-guidance block, Save draft / Extract.
- **Verify Fields:** AI-reading overlay runs while the real `/extract` call is in flight; 22 fields in 7 groups; auto-confirmed vs "Needs check"; Correct / Fix value / Not on pack / Edit / Restore AI value (original AI value kept); Confirm all remaining; Replay AI reading; category select; failure state with attempts + Retry.
- **AI Review:** six-step animation that holds on the last step until `/analyze` returns; error states (`fields_unconfirmed` → back to Verify; others → Retry).
- **Findings:** photo switcher + preview, five summary cards, approved values (AI value shown beside corrections), reference comparison table, packaging summary, finding cards with kind-specific decisions (Confirm / dismiss with reason / Correct value), provisional suggestion, final classification + remarks, stale-analysis warning.
- **Report:** HTML preview of the same 13 sections (print ⇄ mobile view), typed signature + reviewed checkbox, generating overlay, Download / Print / Share (Web Share API with PDF file, download fallback), follow-up notes, proposal submission dialog.
- **Admin:** dashboard with live counts; reference DB with manual / AI-assisted / CSV-Excel import (preview → commit); product detail with edit mode, packaging versions + image upload, history from the audit log, archive/restore, Super-Admin delete; rules with version history; proposals review (edit before approve, request info, reject, keep pending, open PDF); users (approve with role, decline, view, change role, disable/enable, pre-authorise, protected rows); analytics (validated chart colours, tooltips/table view, storage meter with 80 % warning); audit (filters, field diffs, CSV); settings (Website Images upload/replace/reset, General, AI & OCR provider status, Limits & Usage, My account; mobile "More" links).

## 2. Verification (real results — `docs/TEST_REPORT.md` Phase 2)
| Check | Result |
|-------|--------|
| `pnpm typecheck` / `pnpm lint` / `pnpm format:check` | ✅ clean (0 errors, 0 warnings) |
| `pnpm test` (Vitest) | ✅ 8 passed |
| `pnpm build` | ✅ 22 routes |
| Playwright sweep (production build, real API + Mongo + Auth emulator, fake AI) | ✅ 10/10 — every route at 1440 and 390: renders, no horizontal overflow, no console errors |
| Backend regression | ✅ 59 pytest, ruff/mypy/bandit clean |
| Visual comparison vs `design/screenshots` | ✅ layout/tokens/components match; not pixel-perfect; intentional differences in T-24…T-28 |

**Not verified yet:** full click-through journeys (Phase 3), real Google sign-in, real AI providers (no keys), Netlify/Render deploys and CSP in production (Phase 4).

## 3. Decisions made in Phase 2 (`docs/DECISIONS.md` T-23…T-31)
Cache Components off · validation flags instead of invented "OCR agrees" chips · no Privacy/Terms/History-PDF dead links · chart palette validated
with the dataviz script · admin "More" → Settings with links · CSP with `'unsafe-inline'` · emulator-only test sign-in helper · backend emulator
setting, `analysis_stale`, dev seed script.

## 4. How to run what exists now
```bash
docker run -d --name cs-mongo -p 27017:27017 mongo:7
firebase emulators:start --only auth --project demo-cratescan        # repo root
cd backend && cp .env.example .env   # APP_ENV=development, FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099,
                                     # FIREBASE_PROJECT_ID=demo-cratescan, AI_PROVIDER_ORDER=fake, SUPER_ADMIN_EMAIL=admin@example.com
uv sync && uv run python -m scripts.migrate && uv run uvicorn app.main:app --port 8000
uv run python -m scripts.dev_seed                                     # demo users + inspections at every stage
cd ../frontend && cp .env.example .env.local   # NEXT_PUBLIC_USE_AUTH_EMULATOR=true, PROJECT_ID=demo-cratescan, API_KEY=demo-api-key
pnpm install && pnpm dev                       # http://localhost:3000  (sign in via emulator account picker)
pnpm test && pnpm build && pnpm start & pnpm e2e
```
Seeded accounts: `admin@example.com` (Super Admin), `inspector@example.com` (Inspector), `pending.person@example.com` (Pending).

## 5. Notes for Phase 3 (integration)
- Journeys to automate in Playwright (desktop + mobile): pending → admin approval → inspector access; full inspection (upload real image
  files, crop, extract, confirm/edit fields, AI review, decide findings, classification, report, download PDF, follow-up note); extraction
  failure → retry (`AI_PROVIDER_ORDER=fake_fail,fake` toggling needs a backend restart or a dedicated test port); proposal submit → admin request
  info → inspector reply → approve → record visible in reference DB; admin reference CRUD + image + import; rules edit + history; settings
  image upload visible on landing; role demotion/disable taking effect in an open session; isolation through the UI (inspector B opening
  inspector A's URLs → 404 states); cold-start banner (stop/start the API mid-session).
- Remove/confirm no mock data in production paths (`PackIllustration` is only a fallback when a photo is unavailable; landing workspace preview
  is labelled "Sample preview").
- Check the `claims_stale` flow in the browser after approval/role change (auth context refreshes the token).
- Keep the `ERR_TUNNEL_CONNECTION_FAILED` filter limited to `apis.google.com` (sandbox limit).

---

## 6. ▶ PROMPT TO START PHASE 3 (copy into the next session)

```
You are continuing the CRATE-SCAN build in repo DubbakaSathwik/Food_inspection_toolkit,
branch feature/initial-build. Follow the MASTER BUILD PROMPT rules, but work PHASE BY PHASE:
complete only Phase 3, then stop and write docs/handoffs/PHASE_3_HANDOFF.md (same structure
as PHASE_2_HANDOFF.md, ending with the prompt to start Phase 4). Commit and push to
feature/initial-build.

Before coding, read: PROJECT_STATE.md, docs/DECISIONS.md, docs/PROJECT_SPEC.md,
docs/FEATURE_MATRIX.md, docs/ARCHITECTURE.md, docs/TEST_REPORT.md,
docs/handoffs/PHASE_2_HANDOFF.md (§4 how to run, §5 notes). Do not re-ask the deployment gate.

PHASE 3 — BACKEND–FRONTEND INTEGRATION (task T16):
- Start MongoDB (Docker), the Firebase Auth emulator, the backend (fake AI provider) and the
  frontend production build; seed with backend/scripts/dev_seed.py where useful.
- Write Playwright end-to-end journeys (desktop 1440 and mobile 390) in frontend/e2e for every
  mandatory feature, driving the real UI against the real API and MongoDB:
  sign-in → pending → admin approval → access (claims refresh); full inspection from photo upload
  (real image files, crop) through extraction, field review/corrections, AI review, finding
  decisions, classification, report generation, PDF download, follow-up notes; extraction
  failure → incomplete → retry; proposal submit → info request → reply → approve → new demo
  reference record; admin reference manual/AI-assisted/CSV import, images, archive; rules
  create/edit/history; users approve/role change/disable (effect on an open session);
  settings site-image upload shown on landing; Ask AI with and without web research;
  history filters and CSV/Excel export; inspector isolation through the UI (404 states);
  cold-start "Starting the server" state when the API is down then back.
- Verify authorization end to end (direct API calls with curl/fetch cannot bypass the UI rules),
  no protected data in static output, no mock data in production paths, no dead buttons or
  TODOs for mandatory features; fix every defect found (with regression tests).
- Record real results in docs/TEST_REPORT.md (Phase 3), update FEATURE_MATRIX statuses to ☑
  only where a journey passed, IMPLEMENTATION_PLAN, PROJECT_STATE, DECISIONS.
Stop after Phase 3 and deliver the Phase 3 handoff doc.
```
