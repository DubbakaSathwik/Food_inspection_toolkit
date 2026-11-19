# Phase 0 Handoff — Project Understanding, Discovery & Architecture

**Project:** CRATE-SCAN (repo `DubbakaSathwik/Food_inspection_toolkit`, branch `feature/initial-build`)
**Phase status:** ✅ Phase 0 complete (documents only; no application code yet)
**Date:** 2026-11-19

---

## 1. What Phase 0 delivered

| File | Purpose |
|------|---------|
| `docs/DECISIONS.md` | Deployment gate answers, owner conflict resolutions (D-01…D-10), technical decisions (T-01…T-11) |
| `docs/PROJECT_SPEC.md` | Scope, roles, product rules BR-01…BR-10, requirements REQ-001…REQ-071 + NFR-01…07, assumptions, open items |
| `docs/FEATURE_MATRIX.md` | Features F01–F20 → screens, API endpoints, collections, authorization, tests |
| `docs/ARCHITECTURE.md` | Request flow, hosts, repo layout, API design, data model, auth, data-access layer, AI pipeline, security, capacity |
| `docs/IMPLEMENTATION_PLAN.md` | Tasks T00–T19 with dependencies and phase exit gates |
| `PROJECT_STATE.md` | Resumable progress checkpoint |
| `design/` | Design handoff copied into the repo (tokens, CSS, 47 icons, logo, screenshots, original screen source, `specs/screens.json`) |
| `backend/pyproject.toml` | Backend dependency list only (Phase 1 starting point; no app code yet) |

## 2. Locked decisions (summary)

- **Stack:** Next.js 16 (App Router) + TypeScript strict + Tailwind v4 (design tokens as CSS variables) · FastAPI (Python 3.12, uv) · MongoDB Atlas via **PyMongo native async** · Firebase Auth.
- **Hosting:** Backend **Render** free · Frontend **Netlify** · DB **Atlas Free (512 MB)** · deploy **automatically from `main`** after all CI checks pass.
- **Sign-in:** **Google only**. New users stay **pending** until an admin approves them and chooses the role. First Super Admin is set by the env var `SUPER_ADMIN_EMAIL`; `scripts/grant_role.py` is the backup.
- **Files:** **MongoDB GridFS only** (`photos`, `reports`, `refimages`, `siteimages` buckets). No Cloudinary, no Firebase Storage.
- **Images:** AI (Gemini → backup AI) and the OCR fallback always get the **full-quality original**, resized only when a provider's limit requires it. Crops are cut from the original. Originals are deleted after the report is generated, and after 7 days for abandoned inspections. Only the PDF copies are compressed.
- **Extraction chain:** Gemini → NVIDIA / Hugging Face → PaddleOCR (optional, **off on Render**) → saved as *incomplete* with retry.
- **Rules / classification:** seeded **demo** rules that admins can edit. Verified / Not verified / Suspicious is a **provisional suggestion**; the inspector decides.
- **Keys:** the owner adds the real keys to `.env` later. A `fake` AI provider (blocked in production) is used for tests.

## 3. Verified environment facts

- MongoDB 7 runs locally in Docker (`mirror.gcr.io/library/mongo:7`; Docker Hub rate-limited).
- The Firebase Auth emulator works (firebase-tools 14; Java available).
- Python deps install with uv. PyMongo 4.20 provides `AsyncMongoClient` + `gridfs.AsyncGridFSBucket` (checked).
- Node 22 / pnpm 10 available. Playwright 1.63.0 browsers are pre-installed.
- **Push to GitHub is currently refused** for this session. The Claude GitHub App must be installed on the repo, or GitHub reconnected in claude.ai settings. Work is committed locally on `feature/initial-build`.

## 4. Open items (non-blocking)

U-01 final classification criteria · U-02 final AI providers after benchmarking · U-03 exact regulatory rule wording · U-04 certified digital signature (not V1).

---

## 5. ▶ PROMPT TO START PHASE 1 (copy into the next session)

```
You are continuing the CRATE-SCAN build in repo DubbakaSathwik/Food_inspection_toolkit,
branch feature/initial-build. Follow the MASTER BUILD PROMPT rules, but work PHASE BY PHASE:
complete only Phase 1, then stop and write docs/handoffs/PHASE_1_HANDOFF.md
(same structure as PHASE_0_HANDOFF.md, ending with the prompt to start Phase 2).

Before coding, read: PROJECT_STATE.md, docs/DECISIONS.md, docs/PROJECT_SPEC.md,
docs/FEATURE_MATRIX.md, docs/ARCHITECTURE.md, docs/IMPLEMENTATION_PLAN.md. Do not re-ask
the deployment gate; selections are recorded.

PHASE 1 — BACKEND (tasks T01–T11):
- FastAPI app in /backend (uv, Python 3.12): config (pydantic-settings), PyMongo async
  client + GridFS buckets, uniform error format, CORS allow-list, body-size limit,
  security headers, slowapi rate limits, /health.
- Ordered, idempotent migrations in /backend/migrations ($jsonSchema validators, indexes,
  fictional demo seed data labelled "Demo"), `python -m scripts.migrate`.
- Firebase auth dependency (Admin SDK, custom claims {role, active} + DB status check,
  revocation check on admin actions), GET/PATCH /api/v1/me with pending flow and
  SUPER_ADMIN_EMAIL bootstrap, scripts/grant_role.py.
- Repositories = only code touching collections; owner_uid filter on all user data;
  404 for foreign docs; architecture test forbidding db access in routers.
- Inspections + photos in GridFS (quality check, crop rect, retention cleanup), AI provider
  chain (gemini → nvidia/huggingface → optional PaddleOCR → incomplete+retry, fake provider
  for dev/test only, per-user daily quota), 24 extraction fields in 7 groups matching
  design/source/VerifyFields.dc.html, field corrections preserving ai_value + history,
  reference matching, demo licence check, packaging comparison, compliance engine,
  provisional classification, findings decisions, ReportLab PDF (13 sections, compressed
  embedded photos, typed signature), delete originals after report, history/filters/notes/
  export, proposals (inspector + admin review), admin endpoints (dashboard, reference CRUD +
  images + AI-assisted entry + CSV/Excel import, rules with history, users/approvals/roles,
  analytics incl. storage use, audit logs read-only + CSV, settings + site images),
  Ask AI chat with web-research toggle.
- backend/.env.example with every variable (no real secrets).
- pytest against Docker Mongo (start with: docker run -d -p 27017:27017
  mirror.gcr.io/library/mongo:7 --replSet rs0) and the Firebase Auth emulator
  (firebase emulators:start --only auth --project demo-cratescan): auth, isolation
  (user A vs B), role escalation, validation, migrations idempotency, PDF section order.
- Run ruff, mypy, bandit, pytest; record real results. Update FEATURE_MATRIX status,
  IMPLEMENTATION_PLAN, PROJECT_STATE. Commit on feature/initial-build.
Stop after Phase 1 and deliver the Phase 1 handoff doc.
```
