# CRATE-SCAN backend (FastAPI)

Python 3.12 · FastAPI · PyMongo async + GridFS · Firebase Admin · ReportLab. Managed with [uv](https://docs.astral.sh/uv/).

## Run locally
```bash
cd backend
cp .env.example .env            # then edit values (keys stay on the server only)
uv sync                         # add --extra ocr to install PaddleOCR (needs ~1 GB RAM)
docker run -d --name cs-mongo -p 27017:27017 mongo:7
uv run python -m scripts.migrate
uv run python -m uvicorn app.main:app --reload --port 8000
```
Without real Firebase credentials, use the Auth emulator: `firebase emulators:start --only auth --project demo-cratescan`
(from the repo root) and set `FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099`, `FIREBASE_PROJECT_ID=demo-cratescan`.
Without AI keys, set `AI_PROVIDER_ORDER=fake` (development only).

API docs (non-production): http://localhost:8000/docs

## Checks
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy app migrations scripts
uv run bandit -c pyproject.toml -r app migrations scripts
uv run pytest --cov=app          # needs MongoDB on :27017 and the Auth emulator on :9099
```

## Scripts
| Command | Purpose |
|---------|---------|
| `uv run python -m scripts.migrate [--dry-run]` | Apply pending migrations (validators, indexes, demo seed) |
| `uv run python -m scripts.grant_role EMAIL ROLE` | Backup bootstrap: grant `inspector` / `admin` / `super_admin` |
| `uv run python -m scripts.cleanup` | Delete expired temporary photos and orphan GridFS chunks |
| `uv run python -m scripts.export_openapi` | Write `openapi.json` (frontend type generation) |

Layout and rules: see `docs/ARCHITECTURE.md` and `docs/DATABASE.md`.
