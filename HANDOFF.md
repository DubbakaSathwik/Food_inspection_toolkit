# HANDOFF — CRATE-SCAN

**Overall status: IMPLEMENTED WITH DOCUMENTED LIMITATIONS**

All features in `docs/FEATURE_MATRIX.md` (F01–F20) are built and tested locally against MongoDB 7, the Firebase Auth emulator and
a fake AI provider: backend pytest (coverage gate 85 %), frontend Vitest, and Playwright journeys on desktop and mobile. CI/CD,
security scans and deployment configuration are in place. What could **not** be verified during the build, because no real
accounts or keys were available to the agent:

| Not verified | Why | How the owner verifies |
|--------------|-----|------------------------|
| Real Google sign-in (popup/redirect) and a real Firebase project | emulator used | `docs/DEPLOYMENT.md` §2, §6 |
| Real AI extraction (Gemini, NVIDIA, Hugging Face) and PaddleOCR | no keys; fake provider used | set keys, run one inspection with a real pack photo |
| MongoDB Atlas | local MongoDB 7 used | §1 |
| Render + Netlify deployment, deploy and smoke jobs | the agent must never deploy; no secrets | §3–§5, merge to `main` |
| Pixel-level visual match | screens compared by eye against `design/screenshots` (Phase 2) | review the live site |

## Where things are
- Code: `backend/` (FastAPI), `frontend/` (Next.js). Start locally: `README.md`.
- CI/CD: `.github/workflows/ci.yml` (quality → tests → security + CodeQL → build → deploy on `main` → smoke),
  `.github/workflows/security-scheduled.yml` (weekly), `.github/dependabot.yml`, `render.yaml`, `netlify.toml`.
- Deployment steps, rollback and pre-launch checklist: `docs/DEPLOYMENT.md`. Security: `SECURITY.md`.
- Test evidence per phase: `docs/TEST_REPORT.md`. Decisions: `docs/DECISIONS.md`. Phase notes: `docs/handoffs/`.

## Next steps for the owner
1. Create Atlas, Firebase, Render and Netlify resources and the GitHub secrets/variables (`docs/DEPLOYMENT.md`).
2. Open a pull request `feature/initial-build` → `main`; let CI pass; protect `main`; merge → automatic deploy.
3. Sign in as Super Admin, approve inspectors, run one real inspection on a phone, download the PDF.
4. Replace the DEMO reference records and rules with official data before relying on findings (all seeded data is marked DEMO).
