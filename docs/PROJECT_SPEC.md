# CRATE-SCAN — Project Specification

Sources: MVP document V1 (primary scope), PRD v1.0, Project Details, Ideation document, final design handoff ZIP
(44 screens), owner answers (see `DECISIONS.md`). All people, products, licence numbers and records used as seed or
sample data are **fictional** and labelled as such.

## 1. Overview
CRATE-SCAN is an AI-assisted food-product inspection toolkit for FSSAI Food Safety Inspectors. An inspector photographs a
packaged food product (up to 5 photos), the AI reads the label, the inspector checks and corrects the fields, the product
is compared against a **demo** reference database and category-specific **demo** labelling rules, the inspector picks a
classification, and an evidence-backed PDF report is produced. Admins maintain the reference data, rules, proposals and
users. It is **decision support only**.

## 2. Users and roles
| Role | Who | Can |
|------|-----|-----|
| Inspector | Food Safety Inspector (Google account approved by an admin) | Own inspections, reports, history, proposals, Ask AI |
| Admin | Reference-data administrator | Reference DB, rules, proposals, inspector accounts, analytics, audit, settings |
| Super Admin | One bootstrap account (`SUPER_ADMIN_EMAIL`) + any it promotes | Everything an admin can + create/promote/demote admins |
| Pending user | Any new Google sign-in | Only the Pending screen |

Expected active users at launch: up to **60**.

## 3. Non-negotiable product rules (BR)
- BR-01 The inspector makes the final decision; AI output is a suggestion.
- BR-02 Original AI values and confidence are kept beside every correction (with timestamps).
- BR-03 A demo licence match is not government verification. A missing reference record is not "fake". A packaging difference is not proof of counterfeiting. Admin approval of a proposal is not FSSAI certification.
- BR-04 AI confidence is not measured accuracy.
- BR-05 Typed signature is not a certified digital signature.
- BR-06 Verified / Not verified / Suspicious are suggestions; the criteria are provisional until the owner finalises them.
- BR-07 Internet research happens only when the inspector switches it on; results never become findings automatically.
- BR-08 Photos are temporary: originals deleted after the report (or after the retention period if abandoned). The PDF is the evidence.
- BR-09 New Google sign-ins stay pending until an admin activates them. Admin rights are never self-assigned.
- BR-10 Extraction status, reference matching, packaging analysis and compliance findings are stored separately.

## 4. Requirements
Priority: **M** mandatory · **I** important · **O** optional · **X** out of scope.

### Authentication & accounts
| ID | Requirement | P |
|----|-------------|---|
| REQ-001 | Google sign-in via Firebase; backend verifies the ID token on every protected request | M |
| REQ-002 | First sign-in creates a pending profile; Pending screen until approved; declined/disabled users are blocked | M |
| REQ-003 | Roles inspector / admin / super_admin as server-set custom claims; route + API protection | M |
| REQ-004 | Super Admin bootstrap via `SUPER_ADMIN_EMAIL` and a CLI script | M |
| REQ-005 | Profile page: view account, edit display name / designation / office; log out | I |

### Inspection workflow
| ID | Requirement | P |
|----|-------------|---|
| REQ-010 | Inspector dashboard: totals, completed, pending reviews, proposals, continue-where-you-left-off, recent inspections, banner image | M |
| REQ-011 | Create inspection with unique ID, date/time, owner | M |
| REQ-012 | Upload 1–5 photos (camera / gallery / file), preview, remove, replace, label (front/back/side/close-up) | M |
| REQ-013 | Automatic image-quality check (blur, darkness, resolution) → warning (orange) that never blocks | M |
| REQ-014 | Manual crop: crop rectangle stored; crop cut from the original at analysis; original preserved | I |
| REQ-015 | AI extraction of all label fields as structured JSON with per-field confidence and source photo | M |
| REQ-016 | Provider chain Gemini → backup AI → OCR → incomplete + retry; no data loss on failure | M |
| REQ-017 | Validation of dates, quantities, licence format, numeric fields | M |
| REQ-018 | Verify Fields: high-confidence fields auto-confirmed, others ask the user; every field editable; original AI value preserved; "Replay AI reading" | M |
| REQ-019 | Product category (4 supported) detected and editable | M |
| REQ-020 | Reference matching: exact / partial / mismatch / no record / insufficient information, with evidence | M |
| REQ-021 | Manufacturer comparison tolerant to case, spacing, spelling; address comparison | M |
| REQ-022 | Demo licence check: found / not found / invalid format / expired / suspended / needs review | M |
| REQ-023 | Packaging anomaly analysis vs reference photos and known packaging versions (observations only) | M |
| REQ-024 | Category-specific compliance engine running admin-maintained demo rules; findings show extracted value, expected requirement, rule, reference, reason, evidence photo, status | M |
| REQ-025 | Claim analysis (natural/organic, health, nutrition, exaggerated) as review findings | I |
| REQ-026 | AI Review step with progress animation while analysis runs | M |
| REQ-027 | Findings: per-finding inspector decision, corrections kept beside original AI value, photo switcher, suggested classification, final classification + remarks | M |
| REQ-028 | PDF report in the fixed 13-section order, original photos embedded (compressed copies), typed-name signature, disclaimers | M |
| REQ-029 | Report preview (print view ⇄ mobile view), download, print, share | M |
| REQ-030 | Originals deleted after report generation; abandoned originals deleted after retention days | M |
| REQ-031 | Inspection history: search by product/brand, filters by date, category, classification, status; view and re-download reports | M |
| REQ-032 | Follow-up notes on past inspections without changing original findings | I |
| REQ-033 | Export own history (CSV / Excel) | O |

### Proposals
| ID | Requirement | P |
|----|-------------|---|
| REQ-040 | Inspector submits an unknown product as a proposal (extracted data, manufacturer/licence, remarks, linked report PDF) | M |
| REQ-041 | Inspector sees proposal status and detail ("Your proposals", View expands) and can reply to an info request | M |
| REQ-042 | Admin reviews proposals: approve (creates demo reference record), reject with reason, request info, keep pending; edit before approval; review history kept | M |

### Admin
| ID | Requirement | P |
|----|-------------|---|
| REQ-050 | Admin dashboard metrics: users, active users (DAU/WAU/MAU), inspections, reference products, proposals by status, pending approvals | M |
| REQ-051 | Reference database: list, search, filter, add (manual), edit, archive/restore, delete (super admin) | M |
| REQ-052 | Combined record: product, variant, category, size, GTIN, manufacturer, addresses, state/district, licence no., validity, status, FBO category, contact | M |
| REQ-053 | Reference packaging photos with known packaging versions | M |
| REQ-054 | AI-assisted product entry (photos → extracted draft → admin reviews → save) | M |
| REQ-055 | Excel/CSV bulk import with validation preview and confirm | M |
| REQ-056 | Compliance rules: create, edit, archive, category assignment, references, check logic, version history | M |
| REQ-057 | User management: approvals (role + approve/decline), search, role/status filters, view, edit role, disable/enable, pre-authorise a user, admin roles only by super admin | M |
| REQ-058 | Analytics: inspections by category, classification stats, frequently scanned products, proposal stats, storage use | I |
| REQ-059 | Audit log of admin actions (actor, action, target, timestamp, changed fields); read-only; CSV export | I |
| REQ-060 | Settings: Website Images (hero, sign-in, banner upload/replace/remove), General, AI & OCR, Limits & Usage | I |

### Assistant
| ID | Requirement | P |
|----|-------------|---|
| REQ-070 | Ask AI chat with one saved history per inspector; can use own inspection context, demo references, demo rules | I |
| REQ-071 | Internet research toggle (off by default), official FSSAI/FoSCoS sources prioritised, clickable sources | I |

### Non-functional
| ID | Requirement | P |
|----|-------------|---|
| NFR-01 | Desktop (1440) and mobile (390) layouts per design; breakpoint 760 px; no horizontal page scroll | M |
| NFR-02 | Data isolation: inspectors only see their own inspections, reports, notes, chats, proposals | M |
| NFR-03 | AI failure never destroys an inspection (retry / incomplete) | M |
| NFR-04 | Free-tier usage only; per-user daily AI quota; no silent paid usage | M |
| NFR-05 | Cold-start handling for Render (starting-server state + retry) | M |
| NFR-06 | Accessibility basics: semantic HTML, labels, focus, contrast, reduced motion | M |
| NFR-07 | Storage use visible to admins; Atlas 512 MB budget respected via compression and cleanup | M |

## 5. Out of scope (X)
Official government verification, automatic legal verdicts, enforcement actions, guaranteed counterfeit detection, live
regulatory sync, multi-language, GPS tagging, advanced/predictive analytics, manufacturer contact, barcode/QR external
verification, unlimited AI, offline AI processing, notifications for proposals.

## 6. Assumptions
- A-01 Supported categories: Packaged beverages & water · Packaged snacks · Dairy products · Packaged groceries & food staples.
- A-02 FSSAI licence number format check = 14 digits (registration numbers also 14 digits). Rule is editable data.
- A-03 Auto-confirm threshold for extracted fields = confidence ≥ 0.85 (admin setting).
- A-04 Provisional classification heuristic (D-09): any open *high*-severity finding → Suspicious; exact reference match and no open warnings → Verified; otherwise Not verified.
- A-05 Report share = Web Share API with the PDF file where the browser supports it, otherwise download.
- A-06 Seed data: a handful of fictional reference records and demo rules, all labelled "Demo".

## 7. Unresolved (owner to decide later — do not block build)
- U-01 Final classification criteria. U-02 Final primary/backup AI providers after benchmarking. U-03 Exact regulatory
  rule wording per category. U-04 Certified digital signature (not in V1).

## 8. Acceptance criteria
Per requirement in `FEATURE_MATRIX.md`; overall: the MVP completion criteria (MVP §6) and the demonstration scenarios
(inspector and admin) must run end to end against the real backend and database.

## 9. Design references
`/design` in this repository: `tokens.css`, shared CSS rules, icons (47), logo, screenshots (desktop + mobile) and
`specs/screens.json`. Routes and per-screen behaviour follow handoff §2 and §6.
