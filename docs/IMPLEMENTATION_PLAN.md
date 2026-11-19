# CRATE-SCAN — Implementation Plan

Status: ☐ not started · ◐ in progress · ☑ done (verified) · ⚠ blocked

| Task | Phase | Reqs | Depends | Scope | Verification | Status |
|------|-------|------|---------|-------|--------------|--------|
| T00 | 0 | all | — | Spec, matrix, architecture, decisions, state | Docs exist and reviewed | ☑ |
| T01 | 1 | — | T00 | Backend skeleton: config, db, errors, app factory, health | `pytest tests/test_health.py` | ☑ |
| T02 | 1 | — | T01 | Migrations framework + validators + indexes + seed demo data | migrate twice on empty DB; validator test | ☑ |
| T03 | 1 | REQ-001..005 | T02 | Firebase auth dependency, `/me`, bootstrap, grant script | emulator token tests, pending/active/disabled | ☑ |
| T04 | 1 | NFR-02 | T03 | Repositories with ownership filters + architecture test | isolation tests user A/B | ☑ |
| T05 | 1 | REQ-011..014,030 | T04 | Inspections + photos (GridFS, quality check, crop, retention cleanup) | upload/quality/crop/cleanup tests | ☑ |
| T06 | 1 | REQ-015..019,016 | T05 | AI providers + chain + OCR fallback + extraction + field corrections | fake/failing provider tests | ☑ |
| T07 | 1 | REQ-020..027 | T06 | Matching, licence, packaging, compliance engine, classification, findings decisions | unit + API tests | ☑ |
| T08 | 1 | REQ-028..033 | T07 | PDF report (13 sections), report storage, originals deletion, history, notes, export | PDF section order test | ☑ |
| T09 | 1 | REQ-040..042 | T08 | Proposals (inspector + admin review) | API tests | ☑ |
| T10 | 1 | REQ-050..060 | T04 | Admin: dashboard, reference CRUD/images/AI entry/import, rules, users, analytics, audit, settings, storage | API + permission tests | ☑ |
| T11 | 1 | REQ-070..071 | T06 | Assistant chat + web toggle | API tests with fake provider | ☑ |
| T12 | 2 | NFR-01 | T00 | Next.js foundation, tokens, fonts, icons, components, shells, loader | build + lint | ☑ |
| T13 | 2 | public/auth | T12 | Landing, SignIn, Pending | Playwright | ☑ |
| T14 | 2 | inspector | T12 | Dashboard, New, Verify, AI Review, Findings, Report, History, Proposals, Ask AI, Profile | Playwright | ☑ |
| T15 | 2 | admin | T12 | Admin dashboard, Reference DB, Product detail, Rules, Proposals, Users, Analytics, Audit, Settings | Playwright | ☑ |
| T16 | 3 | all | T11,T15 | Integration, cold-start, auth flow with emulator, e2e journeys | Playwright e2e desktop + mobile | ☐ |
| T17 | 4 | — | T16 | CI workflows, Dependabot, scheduled security, actionlint | actionlint + local runs | ☐ |
| T18 | 4 | — | T17 | Security review, bundle check, visual comparison vs screenshots | reports | ☐ |
| T19 | 4 | — | T18 | Docs: README, DATABASE, SECURITY, TEST_REPORT, DEPLOYMENT, HANDOFF | review | ☐ |

## Phase exit gates
- **Phase 1:** migrations idempotent on disposable DB; auth + isolation + role-escalation tests pass; all routers via repositories (architecture test); pytest green.
- **Phase 2:** every route renders at 1440 and 390 without horizontal overflow; `tsc`, ESLint, build pass.
- **Phase 3:** inspector demo journey (sign in → report → history) and admin journey (reference, rules, proposal decision, users) pass in Playwright against real API + Mongo + emulator.
- **Phase 4:** all CI jobs pass locally; workflows lint clean; truthful TEST_REPORT.
