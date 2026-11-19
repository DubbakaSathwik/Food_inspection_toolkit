# Deployment — CRATE-SCAN

Target (owner decisions, `docs/DECISIONS.md`): **Render** web service for the FastAPI backend (A1), **Netlify** for the
Next.js frontend (B1), **MongoDB Atlas Free** (C1) with GridFS for files (D3), **Firebase Authentication, Google only** (E2),
about 60 users, and **auto-deploy from `main` after CI passes** (F1).

Nothing has been deployed by the build agent. Follow these steps in order. Allow about 1–2 hours the first time.

```
GitHub push to main ──► CI (quality → tests → security/CodeQL → build) ──► deploy job
                                                                            ├─ Render deploy hook → wait for /health
                                                                            └─ Netlify CLI build + deploy → smoke test
```

## 1. MongoDB Atlas (C1)
1. Create an Atlas project and a **free (M0)** cluster in the region closest to your users and to Render (e.g. Mumbai / Singapore).
2. *Database Access* → add user `crate-scan-app`, password auth (auto-generate), role **readWrite** on database `crate_scan` only
   (*Specific privileges*), not Atlas admin.
3. *Network Access* → add `0.0.0.0/0` (Render free has no fixed outbound IP; see `SECURITY.md`).
4. *Connect → Drivers* → copy the `mongodb+srv://…` string, insert the password. This is `MONGODB_URI`.
5. Free tier limit is 512 MB. Admin → Analytics shows database and GridFS usage; photos are deleted after reports, so usage
   stays low with 60 users. Turn on Atlas email alerts for storage.

## 2. Firebase Authentication (E2)
1. Create a Firebase project (Spark plan is enough). *Authentication → Sign-in method* → enable **Google** only.
2. *Project settings → General → Your apps* → add a **Web app**. Copy `apiKey`, `authDomain`, `projectId`, `appId`
   (these are public `NEXT_PUBLIC_*` values).
3. *Project settings → Service accounts* → **Generate new private key**. The JSON file is a secret: paste it on one line into
   Render as `FIREBASE_SERVICE_ACCOUNT_JSON`, then delete the downloaded file.
4. *Authentication → Settings → Authorized domains* → add your Netlify domain (e.g. `crate-scan.netlify.app`) and any custom domain.
5. Restrict the browser API key (Google Cloud Console → Credentials) to your site's referrers.

## 3. Render backend (A1)
1. Render dashboard → **New → Blueprint** → connect this GitHub repo → it reads `render.yaml` (service `crate-scan-api`,
   root `backend`, free plan, `autoDeploy: false`, health check `/health`).
   If you prefer a manual web service, use the same values:
   - Build: `pip install "uv==0.11.32" && uv sync --frozen --no-dev && .venv/bin/python -m scripts.migrate`
   - Start: `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "*"`
   - Health check path `/health`; env `PYTHON_VERSION=3.12.12`.
   - Auto-Deploy: **Off** (GitHub Actions deploys after CI).
2. Enter the secret env vars (`sync: false` in the blueprint):

   | Variable | Value |
   |----------|-------|
   | `MONGODB_URI` | Atlas connection string (step 1) |
   | `FIREBASE_PROJECT_ID` | Firebase project ID |
   | `FIREBASE_SERVICE_ACCOUNT_JSON` | service-account JSON on one line |
   | `SUPER_ADMIN_EMAIL` | your Google email — becomes Super Admin on first sign-in |
   | `CORS_ALLOWED_ORIGINS` | `https://<your-site>.netlify.app` (exact, comma-separated if several) |
   | `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `HF_API_KEY` | AI keys (any you have; missing ones are skipped) |

   Do **not** set `FIREBASE_AUTH_EMULATOR_HOST` (startup refuses it in production) or `AI_PROVIDER_ORDER=fake`.
3. *Settings → Deploy Hook* → copy the URL (secret) for GitHub (`RENDER_DEPLOY_HOOK_URL`).
4. Deploy once manually, then open `https://<service>.onrender.com/health` → `{"status":"ok","database":"ok"}`.

**Migrations in production** run in the build command (`scripts.migrate`); they are idempotent (CI applies them twice) and
recorded in the `migrations` collection. To preview: `uv run python -m scripts.migrate --dry-run` with the production
`MONGODB_URI` in your shell (never commit it).

**Cold starts:** free instances sleep after ~15 idle minutes; the first request then takes up to about a minute. The app shows
"Starting the server…" and retries automatically. No keep-alive pinging is configured (it would work against the free plan's
intent); upgrade the instance if cold starts are a problem.

## 4. Netlify frontend (B1)
1. Netlify → **Add new site → Import from Git** → this repo. `netlify.toml` sets base `frontend`, `pnpm build`, the Next.js
   runtime plugin and security headers.
2. *Site configuration → Build & deploy → Continuous deployment* → **Stop builds** (GitHub Actions deploys after CI; F1).
3. *Environment variables* (also add them as GitHub variables, step 5):
   `NEXT_PUBLIC_API_BASE_URL=https://<service>.onrender.com`, `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`,
   `NEXT_PUBLIC_FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_APP_ID`, `NEXT_PUBLIC_USE_AUTH_EMULATOR=false`.
4. *User settings → Applications → Personal access tokens* → new token (`NETLIFY_AUTH_TOKEN`). *Site configuration → Site
   details* → Site ID (`NETLIFY_SITE_ID`).
5. If the site's CSP in `netlify.toml` needs your exact Render URL, set `connect-src` accordingly (currently allows
   `https://*.onrender.com` and Firebase/Google endpoints).

## 5. GitHub
1. *Settings → Environments* → create **production** (optionally add yourself as required reviewer → manual approval per deploy).
2. Environment **secrets**: `RENDER_DEPLOY_HOOK_URL`, `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`.
3. Repository **variables**: `API_BASE_URL` (Render URL, no trailing slash), `SITE_URL` (Netlify URL), and the four
   `NEXT_PUBLIC_FIREBASE_*` values.
4. *Settings → Branches* → protect `main`: require a pull request, require status checks **Quality**, **Tests**, **Security**,
   **CodeQL (python)**, **CodeQL (javascript-typescript)**, **Build**; block force pushes.
5. *Settings → Code security*: enable Dependabot alerts + security updates, secret scanning + push protection, code scanning
   (CodeQL results upload from CI). Dependabot PRs (`.github/dependabot.yml`) arrive weekly; merge them only when CI is green.
6. Merge `feature/initial-build` into `main` via a pull request → CI runs → deploy → smoke test.

## 6. First sign-in
Open the Netlify URL, sign in with the `SUPER_ADMIN_EMAIL` Google account → you are Super Admin. Other people sign in, appear as
**pending** in Admin → Users; approve them and assign *Inspector* or *Admin*. Then in Admin → Settings set the AI daily limit
and photo retention days, and upload any site images.

## 7. Rollback
- **Frontend:** Netlify → *Deploys* → pick the previous deploy → **Publish deploy** (instant).
- **Backend:** Render → service → *Events/Deploys* → previous deploy → **Rollback**.
- **Code:** `git revert <commit>` on `main` (via PR) → CI redeploys. Never force-push `main`.
- **Database:** migrations only add validators/indexes/seed data and are safe to leave in place on rollback. Atlas Free has no
  point-in-time restore — export important collections before risky changes (`mongodump` with the app user).

## 8. Pre-launch checklist
- [ ] Atlas user is readWrite-only on `crate_scan`; storage alert on
- [ ] Firebase: Google only; authorized domains set; API key restricted
- [ ] Render env complete; `APP_ENV=production`; `/health` ok; `/docs` returns 404
- [ ] `CORS_ALLOWED_ORIGINS` = exact Netlify URL
- [ ] At least one real AI key set and an extraction tested end to end (not verified during the build)
- [ ] GitHub environment secrets/variables set; `main` protected; Dependabot + secret scanning on
- [ ] Netlify and Render auto-builds off (deploys come only from CI)
- [ ] First CI deploy + smoke job green; Super Admin sign-in works; a pending user approved
- [ ] One full inspection on a phone: photos → extraction → findings → decision → PDF downloaded; originals removed afterwards
