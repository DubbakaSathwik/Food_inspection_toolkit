# ATTACK_SURFACE — CRATE-SCAN (Phase A map, 2026-11-20)

Sources: the repository at the audit commit, the live route table (introspected from the running app), the production-mode
and real-verification test instances, `render.yaml`, the workflows, and read-only GitHub settings. Items that need a dashboard
I cannot reach (Atlas, Firebase, Render) are marked **NOT VERIFIED**.

## 1. Deployment shape
Browser → **Render web service `crate-scan-web`** (Next.js 16.4.6, `next start`) → **Render web service `crate-scan-api`**
(FastAPI) → **MongoDB Atlas** (documents + GridFS). Sign-in: **Firebase Authentication (Google only)**; the API verifies ID tokens
with firebase-admin. Both services auto-deploy from `main` after GitHub Actions pass (`autoDeployTrigger: checksPass`).
The GitHub repository is **public**.

## 2. Frontend (Next.js)
| Item | Finding |
|------|---------|
| Router / rendering | App Router, client-rendered app pages (auth is a Firebase ID token in the browser); no route handlers, server actions or middleware; no secrets or database access in Next.js |
| Protection | Pages redirect in the client; **all authorization is enforced by the API** (the UI is not a control) |
| `NEXT_PUBLIC_*` | `API_BASE_URL`, `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, `FIREBASE_APP_ID`, `USE_AUTH_EMULATOR`, `AUTH_EMULATOR_URL`. All public by design; none is a server secret |
| HTML sinks | `dangerouslySetInnerHTML` only in `components/icon.tsx` for fixed icon constants. No user data rendered as HTML |
| User-controlled links | Ask-AI source links (`href={s.url}`) — now limited to `http(s)` (SEC-009). Report PDFs open from `blob:` URLs with `noopener` |
| Redirects | `/signin?next=` is only followed when it starts with the user's own area (`/inspector`, `/admin`) |
| Token storage | Application code never writes tokens to `localStorage`/cookies; Firebase SDK manages its own persistence |
| Headers / CSP | Set in `frontend/next.config.ts` (production only): CSP (`default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, connect/img limited to the API origin and Firebase), HSTS, `X-Frame-Options: DENY`, nosniff, referrer and permissions policy |
| Source maps | None generated (0 `.map` files in `.next/static`) |

## 3. Backend (FastAPI)
Versions (lockfile): FastAPI 0.165.0, Starlette 1.10.0, Pydantic 2.14.3, PyMongo 4.20.0, firebase-admin 7.8.0,
python-multipart 0.0.34, Python 3.12.

**Routes: 78 (77 OpenAPI operations, 74 protected).** Public: `GET/HEAD /health`, `GET /api/v1/public/site-images`, `GET /api/v1/public/site-images/{key}`.
`GET/PATCH /api/v1/me` need a verified Google token only (they create/read the caller's own profile). Everything else uses
`require_inspector` (active inspector or admin) or `require_admin` (admin; writes also re-check token revocation).
Full route × identity statuses are in `SECURITY_AUDIT_REPORT.md` §5.

| Control | How it works |
|---------|--------------|
| Token read | `Authorization: Bearer` only (query-string tokens are ignored) |
| Verification | `firebase_admin.auth.verify_id_token` (signature, audience, expiry); `sign_in_provider` must be `google.com`; email required |
| Revocation | `check_revoked=True` on every non-GET admin request |
| Roles | From the MongoDB `users` document (authoritative) cross-checked with the token's custom claims; stale claims → 401 `claims_stale` |
| Role changes | Only via admin API; privileged roles (admin/super_admin) need a Super Admin; last Super Admin protected; no HTTP route sets claims without an admin check |
| Bootstrap | Verified Google email equal to `SUPER_ADMIN_EMAIL` becomes Super Admin on first sign-in (unverified emails never do) |
| Data access | Routers never touch MongoDB (architecture test, proven to fail on violation); every inspector query is filtered by `owner_uid` inside the repository query |
| Input | Pydantic v2 `extra="forbid"` on request models; string length limits; enum categories; `re.escape` (+ NUL stripping) for all search regexes; no `$where`/`$function`; no user text in aggregation stages |
| Uploads | Decoded with Pillow (content-based type check), JPG/PNG/WebP only, 12 MB limit, **50 MP pixel cap before decoding** (SEC-001), stored in GridFS by id (file name never used as a path) |
| Outbound HTTP | Only to AI provider base URLs from server configuration; no user-supplied URLs (no SSRF surface) |
| CORS | Exact origin list from `CORS_ALLOWED_ORIGINS`; no wildcard; no credentials |
| Rate limits | Own middleware: 240/min default, 60/min writes, 12/min AI per client; client address from `X-Forwarded-For` only when `TRUSTED_PROXY_HOPS` says how many proxies are ours (SEC-003); plus an atomic per-user daily AI quota |
| Errors / logs | Uniform JSON errors, no stack traces; logs contain exception class names, never tokens or bodies |
| Docs | `/docs`, `/redoc`, `/openapi.json` are off when `APP_ENV=production` |
| Body limits | 12 MB uploads, small JSON limit (413) |
| Process | `uvicorn … --no-proxy-headers` (no forwarded-allow-ips), no `--reload` in production |

## 4. MongoDB Atlas — NOT VERIFIED
No Atlas credentials or MCP session were available. From the repository: collections with `$jsonSchema` validators and indexes are
created by migrations `m0001`–`m0003` (applied in the Render build). **Unknown:** live network access list (expected `0.0.0.0/0`
because Render free has no fixed IP), database user roles (must be `readWrite` on `crate_scan` only), separate users per
environment, backups (Atlas free tier has none), any App Services / Data API.

## 5. Firebase — NOT VERIFIED
**Unknown:** enabled providers (should be Google only), anonymous/email sign-up state, authorised domains, API-key restrictions,
whether Firestore / Realtime Database / Cloud Storage are enabled and their rules (the app uses none of them — any in test mode
would be critical), number and age of service-account keys. The app code uses Firebase **only** for ID-token verification and
custom claims.

## 6. Hosting (Render) — partly verified
From `render.yaml`: no secret values in the file (all `sync: false`); API and web auto-deploy only from `main` after checks;
production start refuses emulator hosts, fake AI and (new) a missing service account. **NOT VERIFIED:** actual dashboard env vars,
preview environments (not enabled in the blueprint), who can see the service, the real proxy chain in front of the API
(use **Admin → Diagnostics → Client address** to check).

## 7. GitHub and CI/CD (read-only API)
| Check | Result |
|-------|--------|
| Visibility | **Public** repository |
| Branch protection on `main` | **None** (`Branch not protected`) → SEC-005 |
| Secret scanning + push protection | Enabled |
| Dependabot security updates | **Disabled** → SEC-012 (version updates are configured in `dependabot.yml`) |
| Workflows | No `pull_request_target`/`workflow_run`; no untrusted `${{ }}` inside `run:`; all actions pinned to commit SHAs; default `contents: read`; no `continue-on-error`; deploy is done by Render after checks, no deploy secrets exist |
| Secrets / environments | **NOT VERIFIED** (the API path is blocked in this environment) |
