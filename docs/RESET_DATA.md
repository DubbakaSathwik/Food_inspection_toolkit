# Fresh-start data reset (DANGEROUS — run by hand, once)

Empties the app's data and creates exactly one Super Admin. Tool: `backend/scripts/reset_data.py`. It is never called from startup,
CI or deployment, prints no e-mails/secrets/contents, and refuses to run without a matching typed confirmation.

## What it clears / keeps
| Cleared | Kept |
|---------|------|
| users, invites, inspections, notes, proposals, chat, audit logs, usage, counters; all uploaded photos and reports (GridFS); **every Firebase Auth user** | the collections themselves, validators, indexes, `_migrations`, `settings`; Firebase project settings; all code and hosting config |
| `reference_records` and `compliance_rules` (the DEMO reference data) **only with `--include-reference-data`** | those two by default |

The app signs in with Google only, so **no password is created** (`SUPER_ADMIN_PASSWORD` is ignored). The tool creates the Super Admin in
Firebase (verified e-mail, no password) with the claims the API checks, plus its profile. You then sign in with that Google account.

## Steps (PowerShell, in `backend/`)
Point the shell at the **target** (production values — they override `backend/.env` for this window only):
```powershell
$env:MONGODB_URI="<Atlas connection string>"
$env:MONGODB_DB_NAME="crate_scan"
$env:FIREBASE_PROJECT_ID="<firebase project id>"
$env:FIREBASE_SERVICE_ACCOUNT_JSON='<one-line service account json>'
$env:FIREBASE_AUTH_EMULATOR_HOST=""
$env:SUPER_ADMIN_EMAIL="<your google email>"
```
1. Read-only inventory (counts only, writes `RESET_INVENTORY.md`):
```powershell
uv run python -m scripts.reset_data inventory
```
2. Backup to a folder **outside** the repository (it holds personal data — delete it later):
```powershell
uv run python -m scripts.reset_data backup --dir "$HOME\crate-backup"
```
3. Reset (add `--include-reference-data` to also clear the demo reference data and rules):
```powershell
uv run python -m scripts.reset_data reset --confirm-db crate_scan --confirm-project <firebase project id> --backup-dir "$HOME\crate-backup" --create-admin --admin-email-verified
```
It asks you to type the database name. 4. Check:
```powershell
uv run python -m scripts.reset_data verify
```
Expect: Firebase users 1, `users` 1 (`super_admin`), every other data collection 0. Then close the shell (clears the variables) and sign in on the site.

## Seeding
Nothing seeds on startup. The `m0003_seed_demo` migration (fictional demo reference data) now runs in production **only with
`ALLOW_DEMO_SEED=true`**; `scripts/dev_seed.py` refuses any non-local API. Atlas free has no backups: keep the backup folder until you are sure.
