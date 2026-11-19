# CRATE-SCAN — Architecture

## 1. Request flow
```
Browser ──HTTPS──▶ Netlify (Next.js 16 App Router, client-rendered app pages)
   │  Firebase Web SDK: Google sign-in → ID token
   └──HTTPS + Authorization: Bearer <ID token>──▶ Render (FastAPI, Uvicorn)
                                                    ├─ Firebase Admin SDK: verify token / revocation / custom claims
                                                    ├─ MongoDB Atlas (PyMongo async): documents + GridFS buckets
                                                    └─ AI providers (HTTPS, server-side keys only):
                                                         Gemini → NVIDIA NIM / Hugging Face → PaddleOCR (optional, local)
```
The browser never talks to MongoDB or AI providers, and holds no server secrets.

## 2. Hosts and constraints
| Part | Host | Constraints handled |
|------|------|---------------------|
| Frontend | Netlify (Next.js runtime) | Only `NEXT_PUBLIC_*` browser-safe variables; security headers in `netlify.toml`. |
| Backend | Render free web service | Sleeps after ~15 min → frontend pings `/health` on load and shows "Starting server…" with retry/backoff. 512 MB RAM → OCR disabled; images streamed from GridFS, processed one at a time. Port from `$PORT`. No migrations on start. |
| Database | Atlas M0 (512 MB) | Photo originals temporary; PDF photos compressed (~1600 px, JPEG q72); storage usage shown in Analytics; cleanup job. |

## 3. Repository layout
```
backend/app/
  main.py            app factory, middleware (CORS, size limit, headers, rate limit), routers
  config.py          pydantic-settings (env)
  db.py              AsyncMongoClient, GridFS buckets
  auth.py            Firebase verification dependency, role guards
  errors.py          uniform error format {"error":{"code","message","fields"?}}
  models/            Pydantic models (requests, responses, stored documents)
  repositories/      **only** module allowed to touch collections (ownership enforced here)
  services/          ai/ (providers + chain), images, extraction, matching, compliance, packaging,
                     classification, report_pdf, importer, storage
  routers/           public, me, inspections, proposals, assistant, admin_*
backend/migrations/  0001_… ordered, idempotent (validators, indexes, seed)
backend/scripts/     migrate.py, grant_role.py, cleanup.py, backup.md
backend/tests/       pytest (real Mongo + Firebase Auth emulator)
frontend/src/app/    routes (see §6)
frontend/src/components/  design-system components
frontend/src/lib/    api client, auth context, types, hooks
design/              design handoff reference (tokens, icons, screenshots, source)
```

## 4. API design
- Prefix `/api/v1`; JSON; errors `{"error":{"code":"not_found","message":"…","fields":{…}}}` with HTTP status.
- Pagination: `?page=1&page_size=20` (max 100) → `{items,total,page,page_size}`.
- OpenAPI docs only when `APP_ENV != production`.
- Main groups: `/public` (health, site images), `/me`, `/inspector/dashboard`, `/inspections` (+ photos, extract,
  fields, analyze, findings, decision, report, notes, export), `/reference-images/{id}` (any active user),
  `/proposals`, `/assistant`, `/admin/*` (dashboard, reference, rules, proposals, users, analytics, audit, settings,
  storage). Full list in `FEATURE_MATRIX.md` and the generated OpenAPI schema.

## 5. Data model (summary — details in `DATABASE.md`)
| Collection | Owner field | Notes |
|------------|-------------|-------|
| users | `_id` = Firebase UID | role, status, profile, pre-authorised entries (`_id` = `pre:<email>`) |
| inspections | `owner_uid` | photos metadata, extraction (fields with `ai_value`/`value`/history), category, analysis (matching, licence, packaging, compliance — separate), findings decisions, classification, remarks, report ref, status |
| inspection_notes | `owner_uid` | follow-up notes |
| reference_records | admin-managed | combined product + manufacturer + licence + packaging versions + image refs |
| compliance_rules | admin-managed | code, category, check logic, severity, reference, status, version, history |
| product_proposals | `owner_uid` | proposal data, status, review history (embedded `reviews`, bounded) |
| chat_messages | `owner_uid` | one general history per inspector (paginated) |
| audit_logs | — | append-only; no update/delete API |
| usage_metrics | `uid` + `day` | AI call counters |
| settings | — | singleton `_id: "global"` |
| counters | — | inspection ID sequence |
| _migrations | — | applied migrations |
| GridFS buckets | metadata.owner_uid | `photos` (temporary originals), `reports` (PDFs), `refimages`, `siteimages` |

## 6. Frontend routes
`/` · `/signin` · `/pending` · `/inspector` · `/inspector/new?id=` · `/inspector/verify/[id]` · `/inspector/ai-review/[id]`
· `/inspector/findings/[id]` · `/inspector/report/[id]` · `/inspector/history` · `/inspector/proposals` · `/inspector/ask`
· `/inspector/profile` · `/admin` · `/admin/reference` · `/admin/reference/[id]` · `/admin/rules` · `/admin/proposals`
· `/admin/users` · `/admin/analytics` · `/admin/audit` · `/admin/settings`.
Role guard in the app shell redirects by `/me` result (pending → `/pending`; inspector ↔ admin areas). The backend
enforces everything independently.

## 7. Authentication & authorization
1. Client: `signInWithPopup(GoogleAuthProvider)` (redirect fallback when pop-ups are blocked).
2. Every API call sends `Authorization: Bearer <idToken>`; the client refreshes the token and retries once on 401.
3. Backend `current_user` dependency: verify token (Admin SDK) → load `users` doc → effective role = custom claim
   `role`; status must be `active` in **both** claim and DB (DB wins for disable). `require_active`, `require_admin`,
   `require_super_admin` guards; admin mutations also call `verify_id_token(check_revoked=True)`.
4. `/me` creates the profile on first call: `pending`, or `super_admin/active` when the email equals
   `SUPER_ADMIN_EMAIL` and is verified, or the pre-authorised role when an admin added the email earlier.
5. Approve/role change → set custom claims + DB; client forces `getIdToken(true)` when `/me` reports `claims_stale`.
6. Disable → claims `active:false`, `revoke_refresh_tokens`, DB status `disabled`.

## 8. Data-access layer
Routers import only `repositories.*`. Each user-owned repository function takes `Principal` and adds
`{"owner_uid": principal.uid}` to every find/update/delete. Missing or foreign documents → 404. Admin-only functions
take `Principal` and assert admin role (defence in depth). A test (`test_architecture.py`) fails if any router imports
`app.db` or calls collection methods.

## 9. AI pipeline
- `ProviderChain` tries providers in `AI_PROVIDER_ORDER` (default `gemini,nvidia,huggingface`), skipping those without
  keys. Each provider gets the **original** bytes (crop applied from original); resized only above the provider's limit
  (Gemini inline 20 MB total; NVIDIA/HF inline payload limits configurable).
- If every AI provider fails and `OCR_ENABLED`, PaddleOCR text + regex parser produce low-confidence fields.
- If all fail → inspection `extraction.status = "failed"`, inspection status `incomplete`; retry endpoint.
- `fake` provider (deterministic) only when `APP_ENV` is `development` or `test`.
- Packaging comparison and Ask AI use the same chain (vision / chat). Web research = Gemini Google Search grounding,
  only when the request has `web=true`.
- Quota: `usage_metrics` per user per day; 429 when exceeded.

## 10. Security controls
CORS allow-list (`CORS_ALLOWED_ORIGINS`), body size limit (default 12 MB for uploads, 1 MB JSON), slowapi rate limits
(global + stricter on AI and write routes), security headers, upload validation (Pillow decode, MIME/extension
allow-list, pixel cap), NoSQL injection prevention (Pydantic typed inputs only; no raw dict filters from clients),
structured logging without tokens/PII, secrets only in env.

## 11. Capacity and upgrade path
60 active users × ~10 inspections/week: documents are small (<50 KB). The binding limit is Atlas storage: report PDFs
≈ 0.5–1.5 MB each → roughly 300–700 reports on M0 (shown in Analytics). Upgrade: Atlas M10 (connection string only),
Render paid instance (no spin-down), enable OCR on an instance with ≥ 2 GB RAM. No code changes.

## 12. CI/CD
GitHub Actions `ci.yml`: quality → tests (Mongo service container + Firebase Auth emulator + Playwright) → security
(gitleaks, pip-audit, pnpm audit, Bandit, CodeQL, bundle secret check, DAL rule) → build → deploy (main only: Render
deploy hook → wait `/health` → Netlify CLI) → post-deploy smoke test. Weekly `security-scheduled.yml`; Dependabot.

## 13. Testing strategy
Backend pytest against a disposable Mongo (`crate_scan_test` DB, dropped per session) and the Auth emulator (real
token verification path). Frontend Vitest for components/utilities. Playwright end-to-end at 1440 and 390 widths
with the fake AI provider. Real AI providers verified manually by the owner with real keys.
