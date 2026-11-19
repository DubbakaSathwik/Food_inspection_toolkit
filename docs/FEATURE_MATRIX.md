# CRATE-SCAN — Feature Matrix

Roles: **I** inspector · **A** admin · **S** super admin · **P** public. Status: ☐ planned · ◐ partial · ☑ implemented + tested.
All `/api/v1` paths. Every user-owned query filters by `owner_uid` in the repository layer.

**Phase 1 status:** ◐ = backend implemented and tested (pytest, real Mongo + Auth emulator); frontend pending (Phase 2/3). ☑ only after end-to-end verification.

| F | Req | Role | Screen(s) | API | Collections / buckets | Authorization | Tests | Status |
|---|-----|------|-----------|-----|-----------------------|---------------|-------|--------|
| F01 Sign-in & profile | 001–005 | P/I/A | SignIn, Pending, Profile | `GET/PATCH /me` | users | valid token; profile created pending | test_auth.py | ◐ backend |
| F02 Inspector dashboard | 010 | I | InspectorDashboard | `GET /inspector/dashboard` | inspections, product_proposals | active inspector; own data | test_inspections.py | ◐ backend |
| F03 Create inspection + photos | 011–014 | I | NewInspection | `POST /inspections`, `POST /inspections/{id}/photos`, `PATCH/DELETE …/photos/{pid}`, `GET …/photos/{pid}` | inspections, `photos` bucket, counters | owner only | test_photos.py | ◐ backend |
| F04 AI extraction | 015–017 | I | VerifyFields | `POST /inspections/{id}/extract` | inspections, usage_metrics | owner; daily quota | test_extraction.py | ◐ backend |
| F05 Field review | 018–019 | I | VerifyFields | `PATCH /inspections/{id}/fields/{key}`, `POST …/fields/confirm`, `PUT …/category` | inspections | owner; not after report | test_extraction.py | ◐ backend |
| F06 Analysis | 020–026 | I | AIReview | `POST /inspections/{id}/analyze` | inspections, reference_records, compliance_rules | owner | test_analysis.py | ◐ backend |
| F07 Findings & decision | 027 | I | InspectionResults | `PATCH /inspections/{id}/findings/{fid}`, `PUT …/decision`, `GET /reference-images/{id}` | inspections | owner | test_analysis.py | ◐ backend |
| F08 Report | 028–030 | I | ReportPreview | `POST /inspections/{id}/report`, `GET …/report.pdf` | inspections, `reports` + `photos` buckets | owner | test_report.py | ◐ backend |
| F09 History, notes, export | 031–033 | I | InspectionHistory | `GET /inspections`, `POST /inspections/{id}/notes`, `GET /inspections/export` | inspections, inspection_notes | owner | test_inspections.py | ◐ backend |
| F10 Proposals (inspector) | 040–041 | I | ReportPreview, InspectorProposals | `POST/GET /proposals`, `GET /proposals/{id}`, `POST /proposals/{id}/reply` | product_proposals | owner | test_proposals.py | ◐ backend |
| F11 Proposals (admin) | 042 | A | AdminProposals | `GET /admin/proposals`, `GET /admin/proposals/{id}`, `POST /admin/proposals/{id}/decision` | product_proposals, reference_records, audit_logs | admin (+revocation) | test_proposals.py | ◐ backend |
| F12 Admin dashboard | 050 | A | AdminDashboard | `GET /admin/dashboard` | all (counts) | admin | test_admin.py | ◐ backend |
| F13 Reference DB | 051–055 | A/S | ReferenceDatabase, ProductDetail | `GET/POST /admin/reference`, `GET/PATCH/DELETE /admin/reference/{id}`, `POST …/archive`, `POST …/restore`, `POST/DELETE …/images`, `POST /admin/reference/ai-extract`, `POST /admin/reference/import/preview`, `POST /admin/reference/import/commit` | reference_records, `refimages`, audit_logs | admin; delete = super admin | test_reference.py | ◐ backend |
| F14 Compliance rules | 056 | A | ComplianceRules | `GET/POST /admin/rules`, `PATCH /admin/rules/{id}`, `POST …/archive` | compliance_rules, audit_logs | admin | test_rules.py | ◐ backend |
| F15 Users | 057 | A/S | UserManagement | `GET/POST /admin/users`, `GET /admin/users/{uid}`, `POST …/approve`, `POST …/decline`, `PATCH /admin/users/{uid}` | users, user_invites, audit_logs | admin; admin/super roles only by S | test_users.py | ◐ backend |
| F16 Analytics | 058 | A | Analytics | `GET /admin/analytics` | all (aggregates), GridFS stats | admin | test_admin.py | ◐ backend |
| F17 Audit | 059 | A | AuditLogs | `GET /admin/audit`, `GET /admin/audit/export` | audit_logs | admin; read-only | test_admin.py | ◐ backend |
| F18 Settings & site images | 060 | A / P | Settings, Main, SignIn, Dashboard | `GET/PATCH /admin/settings`, `PUT/DELETE /admin/settings/images/{key}`, `GET /public/site-images[/{key}]`, `GET/POST /admin/storage[/cleanup]` | settings, `siteimages` | admin; image GET public | test_settings.py | ◐ backend |
| F19 Ask AI | 070–071 | I | AskAI | `GET/POST/DELETE /assistant/messages` | chat_messages, usage_metrics | owner; quota | test_assistant.py | ◐ backend |
| F20 Health / cold start | NFR-05 | P | all | `GET /health` | — | public | test_health.py | ◐ backend |

### Test files (Phase 1)
`test_health.py` (5) · `test_auth.py` (13) · `test_inspections.py` (11) · `test_admin.py` (10) · `test_assistant.py` (2) ·
`test_providers.py` (8, mocked HTTP) · `test_units.py` (9) · `test_architecture.py` (2) — 59 tests, all passing.
