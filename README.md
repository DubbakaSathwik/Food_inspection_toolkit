# CRATE-SCAN — Food inspection toolkit

AI-assisted food-product inspection toolkit for FSSAI Food Safety Inspectors. Photograph a pack, extract and verify label
fields, compare them against reference records and rules, and generate an inspection report.
**Decision support only — the inspector decides.**

| Part | Stack | Folder |
|------|-------|--------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind 4, Firebase Web SDK (Google sign-in) | `frontend/` |
| Backend | Python 3.12, FastAPI, Pydantic v2, PyMongo async + GridFS, Firebase Admin, ReportLab | `backend/` |
| Database | MongoDB Atlas (documents + GridFS files) | — |
| AI | Gemini → NVIDIA → Hugging Face (→ optional PaddleOCR) for label extraction and "Ask AI" | `backend/app/services/ai/` |
| CI/CD | GitHub Actions → Render (API + website) | `.github/`, `render.yaml` |

## Run it locally (about 10 minutes)

Needs: Docker, Node 22 + pnpm 10, Python 3.12 + [uv](https://docs.astral.sh/uv/), Java 21 and
`npm i -g firebase-tools` (for the Auth emulator).

```bash
cp backend/.env.example backend/.env
```

```bash
cp frontend/.env.example frontend/.env.local
```

For a keyless demo, set `AI_PROVIDER_ORDER=fake` and `FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099` in `backend/.env`, and
`NEXT_PUBLIC_USE_AUTH_EMULATOR=true` in `frontend/.env.local`. Then install and start everything:

```bash
(cd backend && uv sync) && (cd frontend && pnpm install)
```

```bash
scripts/local-stack.sh --fresh
```

Open http://localhost:3000. Demo accounts (emulator): `admin@example.com` (Super Admin), `inspector@example.com`,
`pending.person@example.com`. With real keys instead, put your Atlas/Firebase/AI values in the two env files (see comments
inside them) and run the backend with `uv run python -m uvicorn app.main:app --reload --port 8000` and the frontend with `pnpm dev`.

## Tests

```bash
cd backend && uv run pytest --cov=app
```

```bash
cd frontend && pnpm test && pnpm exec playwright test
```

Playwright needs the local stack running. CI runs all of this plus security scans on every push (`.github/workflows/ci.yml`).

**Something not working?** Sign in as an admin and open **Admin → Diagnostics**: it tests the database, Firebase sign-in
and each AI provider with a live call and shows the real error.

## Documentation

| Document | What it covers |
|----------|----------------|
| `docs/DEPLOYMENT.md` | Atlas, Firebase, Render setup, rollback, pre-launch checklist |
| `SECURITY.md` | Security controls, Phase 4 review results, owner checklist |
| `docs/TEST_REPORT.md` | What was tested and verified, per phase, and what was not |
| `HANDOFF.md` | Final status and next steps for the owner |
| `docs/PROJECT_SPEC.md`, `docs/FEATURE_MATRIX.md` | Requirements and feature-by-feature status |
| `docs/ARCHITECTURE.md`, `docs/DATABASE.md` | Design, collections, migrations |
| `docs/DECISIONS.md` | Every technical and owner decision with reasons |
| `docs/handoffs/` | Phase-by-phase handoff notes |
| `docs/source-documents/` | Original ideation, features, MVP and PRD PDFs |

### Windows notes
- If Windows reports *"An Application Control policy has blocked this file (os error 4551)"*, Smart App Control is blocking an
  unsigned launcher in `backend\.venv\Scripts\`. Run tools through Python instead: `uv run python -m uvicorn …`,
  `uv run python -m pytest`.
- `scripts/local-stack.sh` needs Git Bash or WSL; in PowerShell start the emulator, API and frontend in separate terminals.
- Keep the Firebase emulator terminal open while you use the app; a "port taken" error means an earlier emulator is still running.
