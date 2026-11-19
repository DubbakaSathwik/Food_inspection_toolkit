# CRATE-SCAN — Decisions

Each entry: decision · reason · source. Changing a gate selection needs the owner's explicit instruction; update this file,
the deploy configuration, CI workflows and `DEPLOYMENT.md` together.

## Deployment Selection Gate (recorded 2026-11-19)

| # | Question | Selection | Reason |
|---|----------|-----------|--------|
| 1 | Backend host | **A1 Render** (free web service) | Default. AI calls and PDF generation run too long for serverless functions (A4). |
| 2 | Frontend host | **B1 Netlify** | Default. Netlify's Next.js runtime; no static-export restriction. |
| 3 | Database | **C1 MongoDB Atlas Free (512 MB)** | Default; prototype / portfolio scale. |
| 4 | Sign-in | **E2 Google sign-in only** | Owner instruction and design (single Google button). |
| 5 | File uploads | **D3 MongoDB GridFS** (owner-approved addition to the master prompt's D1/D2) | Owner instruction: "we are only using MongoDB". Product cannot work without photos, reference images and PDFs. |
| 6 | Expected active users | up to 60 | Default. |
| 7 | GitHub repository | Owner will connect a repository; `DubbakaSathwik/Food_inspection_toolkit` (attached 2026-11-19); work on `feature/initial-build`. | Owner instruction. |
| 8 | Deployment mode | **F1** automatic deploy from `main` after all CI checks pass | Default. |

## Conflict resolutions (owner answers, 2026-11-19)

| ID | Decision | Reason |
|----|----------|--------|
| D-01 | Next.js (App Router) replaces React + Vite from the design handoff. | Master prompt mandatory stack; owner confirmed. |
| D-02 | Tailwind CSS v4 with the design tokens defined once as CSS variables (`@theme`). | Master prompt requires Tailwind; owner wanted CSS-variable tokens — both satisfied. |
| D-03 | Files live in MongoDB **GridFS** buckets. Only metadata lives in normal documents. | Owner: MongoDB only. Master prompt rule "never store large files inside documents" is respected: GridFS splits files into 255 KB chunk documents. |
| D-04 | **Image handling:** AI extraction (Gemini → backup) and the OCR fallback always receive the **full-quality original**; resized only when a provider's documented request limit requires it. Crops are cut from the original at analysis time (crop rectangle stored, original untouched). Originals stay temporarily in GridFS until the report is generated, then are deleted. Abandoned inspections' originals are deleted after `PHOTO_RETENTION_DAYS` (default 7). Only the copies embedded in the PDF are compressed. | Owner instruction. |
| D-05 | Extraction order: primary AI (Gemini) → backup AI (NVIDIA or Hugging Face, configurable) → OCR fallback (PaddleOCR, if enabled) → save as **incomplete** with retry. | Owner instruction + MVP §5 failure workflow. |
| D-06 | PaddleOCR is an optional extra (`uv sync --extra ocr`), **disabled on Render** (needs ~1 GB RAM; free instance has 512 MB). Enabled locally with `OCR_ENABLED=true`. | Owner confirmed. |
| D-07 | Google sign-in only. New accounts are **pending** until an admin approves them and chooses the role. | Owner + design (Pending screen, UserManagement approvals). |
| D-08 | First Super Admin: the email in backend env `SUPER_ADMIN_EMAIL` becomes `super_admin` + active on first sign-in. `scripts/grant_role.py` is the backup bootstrap script. | Owner chose env var; master prompt asks for a script — both provided. |
| D-09 | Compliance rules are seeded as clearly labelled **demo rules** that admins edit. Verified / Not verified / Suspicious is a **provisional suggestion** computed by a simple, documented heuristic; the inspector always chooses. | Classification criteria are not finalised (PRD open decision 1). Master prompt forbids inventing regulatory rules. |
| D-10 | AI keys are supplied by the owner later via `.env`. Until then a deterministic `fake` provider (refused when `APP_ENV=production`) drives tests and local demos; real-provider calls are reported as **not verified**. | Owner: "make a .env example; I will add my keys and test". |

## Technical decisions

| ID | Decision | Reason |
|----|----------|--------|
| T-01 | MongoDB driver: **PyMongo native async API** (`AsyncMongoClient`, `gridfs.AsyncGridFSBucket`, PyMongo 4.20). Motor is deprecated in favour of it (MongoDB docs). | Master prompt §4 asks to verify and record. |
| T-02 | Python 3.12, managed with **uv** (`uv.lock`). Frontend uses **pnpm** (`pnpm-lock.yaml`). | Reproducible installs. |
| T-03 | Roles = Firebase custom claims `{role, active}` set only by server code. Every request **also** checks the user document's status so deactivation applies immediately; sensitive admin actions check token revocation. | Master prompt §1.3 + immediate disable requirement. |
| T-04 | Gemini model configured by `GEMINI_MODEL` (default alias `gemini-flash-latest`). Model names change often; the alias avoids hard-coding a retiring version. | Current model list was inconsistent at build time. |
| T-05 | AI providers are called through their REST APIs with `httpx` (no vendor SDKs). | Fewer dependencies; easy to fake in tests. |
| T-06 | PDF reports use ReportLab's built-in Helvetica; Manrope is used on screen (`@fontsource-variable/manrope`). | ReportLab needs TTF files; Manrope TTFs are not bundled. |
| T-07 | Desktop vs mobile: one component per screen, layout switches at **≤ 760 px** (design breakpoint). Tablets use the desktop layout. | Owner confirmed (answer 7). |
| T-08 | Inspection IDs `CS-YYYY-NNNN` from an atomic counter document. | Matches design. |
| T-09 | Per-inspector daily AI quota (`AI_DAILY_LIMIT_PER_USER`, default 60 calls) tracked in `usage_metrics`, plus HTTP rate limits (slowapi). | MVP: controlled API limits; no silent paid usage. |
| T-10 | No keep-alive pings to Render; the frontend wakes the backend via `/health` and shows a "Starting server" state. | Master prompt §12 rule on keep-alive pings. |
| T-11 | Playwright pinned to 1.63.0 locally to match the pre-installed browser; CI installs browsers for the same version. | Environment constraint. |

## Phase 1 implementation decisions (2026-11-19)

| ID | Decision | Reason |
|----|----------|--------|
| T-12 | Extraction schema has **22 fields in 7 groups**, exactly as in `design/source/VerifyFields.dc.html` (handoff prompt said "24"; the design is authoritative). | Design is the source for field labels. |
| T-13 | Auto-confirm = confidence ≥ threshold (default 0.85, admin setting) **and** the value passes validation. Analysis is blocked until every remaining field is confirmed or edited (BR-01). | Human review before findings. |
| T-14 | Editing a field after analysis sets `analysis_stale`; decision/report are blocked until the AI review is re-run. Completed inspections are immutable (only follow-up notes). | Report must reflect reviewed data. |
| T-15 | Admin pre-authorisation uses a separate `user_invites` collection (email → role); applied only to a **verified** Google email on first sign-in. | Keeps `users` keyed by Firebase UID. |
| T-16 | Custom claims are synced server-side by `/me` and admin actions. A role/status mismatch between token and DB returns 401 `claims_stale`; the client force-refreshes the token. Disable also revokes refresh tokens. | Immediate demotion/disable without trusting stale tokens. |
| T-17 | Admin/super-admin role grants and changes to admin accounts require Super Admin; nobody can change their own role/status; the last active Super Admin cannot be demoted/disabled. | Lock-out and escalation safety. |
| T-18 | Packaging comparison uses the newest reference packaging version with photos (max 2 images) against the inspector's "front" photo(s); provider failure → "not performed" (never blocks). | Observations only (BR-03). |
| T-19 | Reference-image downloads are allowed for any active user (inspectors see them in findings); inspection photos and reports only for their owner; site images are public. | Least privilege per file type. |
| T-20 | Opportunistic retention cleanup (≤ once/hour, triggered on inspection create) plus `scripts/cleanup.py` and an admin button — Render free has no cron. | No paid scheduler. |
| T-21 | Repository admin checks use `ensure_admin()` (raises 403) instead of `assert`, so they survive `python -O`. | Bandit B101 finding. |
| T-22 | Rate limiting is disabled when `APP_ENV=test` so the suite is deterministic; production/dev limits come from env. | Test stability; limits verified manually in Phase 4. |

## Phase 2 implementation decisions (2026-11-19)

| ID | Decision | Reason |
|----|----------|--------|
| T-23 | Next.js 16 `cacheComponents` / partial prefetching are **off**. App pages are client components; auth is the Firebase ID token in the browser (no session cookies to read on the server). | Cache Components would force Suspense boundaries around every session read for no benefit here. |
| T-24 | Verify Fields shows **validation flags** ("Looks unusual", "Not found") instead of the design's "OCR agrees / differs" chips. | The backend does not run a per-field OCR cross-check; showing agreement would be invented data. |
| T-25 | Landing footer omits the design's "Privacy" and "Terms" links (no such pages exist); sign-in copy says "authorised inspection work only". | No dead links. Owner to supply policy pages if needed. |
| T-26 | History page: "Export PDF" from the design is not offered (CSV and Excel are). Follow-up notes are read/added on each completed inspection's report page. | No API for a cross-inspection notes list or a history PDF; avoids fake buttons. |
| T-27 | Classification chart colours: Verified `#4E7A2A`, Not verified `#5F7C99`, Suspicious `#C07A1A` (validated with the dataviz palette script: CVD ΔE 14.2, normal-vision ΔE 16.0, contrast ≥ 3:1; the neutral slot is intentionally low-chroma and always carries a text label + %). Single-series charts use `#56703A`; every chart has hover tooltips or a table view. | The design's olive trio failed the colour-separation checks. |
| T-28 | Admin "More" tab opens Settings, which on mobile lists links to Compliance Rules, Proposals and Audit Logs (handoff: "More → Settings"). Settings also has a "My account" tab for admins. | Every admin page reachable on mobile. |
| T-29 | `netlify.toml` CSP allows `'unsafe-inline'` scripts/styles (Next.js bootstrap + design inline styles, no nonce pipeline yet), `connect-src` to `*.onrender.com` and Firebase Auth endpoints. | Tighten with nonces later if required. |
| T-30 | E2E tests sign in through the Auth emulator with a test-only `window.__csTestSignIn` helper that exists **only** when `NEXT_PUBLIC_USE_AUTH_EMULATOR=true`. | Real Google popups cannot be automated; production builds never expose the helper. |
| T-31 | Backend: `FIREBASE_AUTH_EMULATOR_HOST` is now a setting that is copied into the process environment (refused in production); `InspectionOut` exposes `analysis_stale`; `scripts/dev_seed.py` creates local demo data through the real API. | Found while wiring the frontend. |

## Phase 3 integration decisions (2026-11-19)

| ID | Decision | Reason |
|----|----------|--------|
| T-32 | Fake provider test hook: a photo containing the bytes `CRATESCAN_FAKE_FAIL` makes the **fake** provider fail (dev/test only; the fake provider is refused in production). | Lets the UI journey drive "AI outage → incomplete → retry" without restarting the backend. |
| T-33 | Any `403 forbidden` API answer (as well as `account_*` and 401) makes the client reload `/me`, so the route guards move a demoted admin out of the admin area in an open session. | Found by the role-demotion journey. |
| T-34 | `Modal` reports only user-initiated closes; a programmatic close no longer calls `onClose`. | Bug found by the admin journey: switching from the "Add Product" menu to a sub-dialog closed the new dialog immediately. Regression test added. |
| T-35 | Backend test setup no longer wipes all Auth-emulator accounts (it broke the shared local dev stack); test users use unique emails and the test DB is dropped. | Found while running backend tests next to the e2e stack. |
| T-36 | `scripts/local-stack.sh [--fresh]` starts MongoDB, the Auth emulator, the API (fake AI) and the frontend build for development and e2e. | Repeatable local integration environment. |
| T-37 | When the forced token refresh after a `claims_stale` answer fails (refresh tokens revoked on disable), the auth context keeps the non-active profile so the "account disabled" screen shows; after a full reload Firebase signs the revoked session out and signing in again shows the same screen. | Bug found by the disable journey on mobile: the user was stuck on "Checking your access…". |

## Phase 4 decisions (2026-11-19)

| ID | Decision | Reason |
|----|----------|--------|
| T-38 | **Rate limiting re-implemented** as `app/ratelimit.py` (ASGI middleware, per client IP, fixed one-minute windows: default / write / AI buckets, 429 JSON + `Retry-After`, placed inside CORS). slowapi removed. | Phase 4 manual check found slowapi 0.1.10's middleware never matched our route handlers, so **no limits applied** (7/7 requests passed a 5/minute limit). Now verified live (4×200 then 429) and by `tests/test_ratelimit.py`. In-memory counters are per process (single Render instance); a shared store is needed if scaled out. |
| T-39 | The local stack and CI run the API with very high rate limits for automated end-to-end runs (all traffic comes from one IP); production uses the defaults in `.env.example`. | Test traffic is not user traffic. |
