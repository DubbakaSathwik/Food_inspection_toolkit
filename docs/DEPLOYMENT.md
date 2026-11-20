# Deployment — CRATE-SCAN (everything on Render)

Two Render web services from one `render.yaml`: **crate-scan-api** (FastAPI) and **crate-scan-web** (Next.js).
Database is **MongoDB Atlas** (free), sign-in is **Firebase Authentication (Google only)**. About 60 users.
Render deploys both services from `main` by itself **after the GitHub Actions checks pass**; no deploy tokens or hooks are needed.

Nothing here has been deployed by the build agent. Allow about 1 hour.

```
merge to main ─► GitHub Actions (quality, tests, security, build) ─► checks pass ─► Render builds + deploys API and website
                                                                                      └─► release-check job confirms the new version is live
```

## Before you start
- Rotate any key that was ever pasted into a chat or committed: Firebase service-account key, Atlas password, AI keys.
- Run the app locally once (sign-in, one inspection, **Admin → Diagnostics** all green).
- Free Render instances have 512 MB RAM. If the website build is killed for memory, upgrade `crate-scan-web` to Starter or build elsewhere.

## 1. MongoDB Atlas (10 min)
1. Create a free (M0) cluster near your users (e.g. Mumbai or Singapore).
2. *Database Access* → new user `crate-scan-app`, strong generated password, role **readWrite** on database `crate_scan` only.
3. *Network Access* → add `0.0.0.0/0` (Render free has no fixed IP; the password and TLS protect it).
4. *Connect → Drivers* → copy the `mongodb+srv://…` string and put the password in it (no `< >`). This is `MONGODB_URI`.

## 2. Firebase (10 min)
1. Authentication → Sign-in method → **Google** enabled (only provider).
2. Project settings → General → your **web app** → note `apiKey`, `authDomain`, `projectId`, `appId`.
3. Project settings → Service accounts → **Generate new private key**. Convert it to one line (PowerShell):
   `Get-Content key.json -Raw | ConvertFrom-Json | ConvertTo-Json -Compress -Depth 5`, then delete the downloaded file.
4. (After step 4 below) Authentication → Settings → **Authorised domains** → add `crate-scan-web.onrender.com`
   (or the real address Render gives your site).

## 3. Put the code on `main` (5 min)
Open a pull request `feature/initial-build` → `main`, wait for the green checks, merge.
(Render deploys the `main` branch. In GitHub → Settings → Branches you can protect `main` and require the checks.)

## 4. Create the services on Render (20 min)
1. Render dashboard → **New → Blueprint** → connect the GitHub repo → it reads `render.yaml` and proposes both services.
2. Render asks for the values marked secret. Enter:

   | Service | Variable | Value |
   |---------|----------|-------|
   | crate-scan-api | `MONGODB_URI` | Atlas string (step 1) |
   | | `FIREBASE_PROJECT_ID` | Firebase project id |
   | | `FIREBASE_SERVICE_ACCOUNT_JSON` | the key as ONE line of JSON (paste it raw, no extra quotes) |
   | | `SUPER_ADMIN_EMAIL` | your real Google account |
   | | `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `NVIDIA_MODEL`, `HF_API_KEY` | AI keys / vision model names (leave blank what you do not have) |
   | crate-scan-web | `NEXT_PUBLIC_FIREBASE_API_KEY`, `…_AUTH_DOMAIN`, `…_PROJECT_ID`, `…_APP_ID` | the four web-app values (step 2) |

3. Apply. The first build takes several minutes (API: installs packages and runs the database migrations; website: `pnpm build`).
4. **Check the real addresses.** If Render named a service differently (e.g. `crate-scan-api-x7k2`), fix these two and redeploy:
   - on **crate-scan-web**: `NEXT_PUBLIC_API_BASE_URL` = the API's real `https://….onrender.com` address (it is baked in at build → *Manual Deploy*)
   - on **crate-scan-api**: `CORS_ALLOWED_ORIGINS` = the website's real `https://….onrender.com` address
5. Open `https://<api>.onrender.com/health` → `{"status":"ok","database":"ok",…}`. Then open the website.

   The blueprint also sets `TRUSTED_PROXY_HOPS=3` and starts the API without proxy-header trust (so callers cannot spoof their address
   for rate limits). After the first deploy, open **Admin → Diagnostics → Client address** and check it shows your own public IP.

## 5. First sign-in (5 min)
Sign in with the `SUPER_ADMIN_EMAIL` Google account → you are Super Admin. Open **Admin → Diagnostics → Run all checks** on the live site:
database, storage, Firebase and the AI providers should show *Working*. Approve other users in Admin → Users.

If Google sign-in is blocked, open the browser console (F12). A "Content Security Policy" message means the website's
security rules block it; set `CSP_REPORT_ONLY=true` on crate-scan-web, redeploy, and send me the message.

## 6. Optional: automatic release check in GitHub
GitHub → Settings → Secrets and variables → Actions → **Variables**: `API_BASE_URL` and `SITE_URL` (the two Render addresses,
no trailing slash). After each merge to `main` the `release-check` job waits until the API reports the new commit and then tests
both services (health, CORS, security headers, docs hidden, `/me` needs sign-in). Without the variables the job is skipped.

## Free-plan behaviour
- Services **sleep after 15 idle minutes**; the next visit takes up to about a minute ("Starting the server…" is shown).
- Two free services = two sleepers. A paid plan (about $7 each) removes sleeping.
- Reference records and rules are **DEMO** data; replace them with official data before real use.

## Rollback
Render → the service → **Deploys** → previous deploy → **Rollback**. For code, `git revert` the commit on `main` via a pull request.
Migrations only add validators, indexes and seed data; they are safe to leave in place. Atlas free has no point-in-time restore.

## Pre-launch checklist
- [ ] Atlas user is readWrite on `crate_scan` only; storage alert on
- [ ] Firebase: Google only; the website address is an authorised domain; browser API key restricted to the site
- [ ] API env complete, `APP_ENV=production`, `/health` ok, `/docs` returns 404
- [ ] `CORS_ALLOWED_ORIGINS` is exactly the website address
- [ ] Diagnostics all *Working* (at least one AI provider)
- [ ] One full inspection on a phone: photos → AI reading → findings → decision → PDF
- [ ] `main` protected; Dependabot and secret scanning on
