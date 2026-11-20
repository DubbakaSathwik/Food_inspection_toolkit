"""Text content of the project report. Unknown personal details are [[placeholders]] (highlighted yellow in the document)."""

TITLE = "CRATE-SCAN – AI-Assisted Food Product Inspection Toolkit"
SHORT = "CRATE-SCAN"

TEAM = [("[[Student Name 1]]", "[[Roll No. 1]]"), ("[[Student Name 2]]", "[[Roll No. 2]]")]
GUIDE = ("[[Guide Name]]", "[[Designation]], Dept. of CSE, MVSREC")
YEAR = "[[2026-2027]]"
COORDINATORS = ["1. [[Coordinator 1]]", "2. [[Coordinator 2]]", "3. [[Coordinator 3]]"]
HOD = ("Dr Akhil Khare", ["Professor & Head of", "Department of CSE", "MVSREC."])
PRINCIPAL = "Dr. M. Kameswara Rao"

ABSTRACT = [
    "CRATE-SCAN is an AI-assisted food-product inspection toolkit built for Food Safety Inspectors working under the Food Safety and Standards Authority of India (FSSAI) framework. "
    "An inspector photographs a packaged product; a vision AI model reads 22 label fields (product name, brand, manufacturer, FSSAI licence number, dates, batch, net quantity, MRP, "
    "ingredients, nutrition, allergens, claims and more) together with a confidence value for each field. The inspector verifies or corrects every reading. The system then compares "
    "the approved values with a reference database of products, manufacturers and licences, applies a configurable set of labelling and claims rules, and presents findings with "
    "evidence. The inspector accepts, dismisses or corrects each finding, records a final decision, and the platform produces a 13-section PDF inspection report. The tool is strictly "
    "decision support: the AI only suggests, and the human inspector always decides.",
    "The platform uses Google sign-in only. New accounts wait for administrator approval, and roles (inspector, administrator, Super Administrator) are assigned by administrators. "
    "The administrator console manages users, the reference database, compliance rules, product proposals and site settings, and provides analytics, a read-only audit log and a "
    "system-diagnostics page that tests the database, sign-in and every AI provider with live calls. If every AI provider fails, photographs are saved and the inspection is marked "
    "incomplete so the work can be retried later; an optional offline OCR reader provides a last-resort draft.",
    "The system is implemented with Next.js 16 (React 19, TypeScript, Tailwind CSS) for the user interface and FastAPI (Python 3.12, Pydantic v2) for the API, with MongoDB Atlas "
    "(documents and GridFS file storage) for data and Firebase Authentication for identity. It is deployed on Render and released through a GitHub Actions pipeline that runs quality "
    "checks, automated tests, security scans and a production build before every deployment. Security was treated as a first-class requirement: every request passes rate limiting, "
    "token verification, role checks and owner-scoped data access, and an attacker-style test suite of 49 tests is part of the pipeline. The project is verified by 75 backend tests "
    "(89 % coverage), 9 front-end unit tests and 44 browser tests on desktop and mobile layouts.",
]

PROBLEM = [
    "Packaged food in India must carry a long list of mandatory declarations: the name of the food, ingredients, nutrition information, allergen declaration, vegetarian or non-vegetarian "
    "symbol, net quantity, date markings, batch number, the manufacturer's name and address, the FSSAI licence number and consumer-care details, among others. A Food Safety Inspector "
    "who examines a product in the field has to read all of these declarations, check their format, compare them with licence and product records, and relate them to the applicable "
    "regulations. Done by hand, this is slow, differs from inspector to inspector, and the evidence behind a decision is often poorly documented.",
    "Using artificial intelligence to read labels is attractive, but an AI model can misread small print and cannot be the final authority in a regulatory setting. A practical system must "
    "therefore keep the inspector in control, show how confident the AI is in every field, make correction easy, and keep a clear record of what the AI suggested and what the "
    "inspector decided. It must also protect inspectors' photographs and reports, work on a phone in the field, and keep working when an external AI service is slow or unavailable.",
    "CRATE-SCAN addresses these problems with a guided inspection workflow: photograph, read, verify, analyse, review findings, decide and report. Every step is saved, every AI value is "
    "kept next to the inspector's correction, and the final PDF report states clearly that the classification is the inspector's decision.",
]

DOMAIN = [
    "The project belongs to the domains of Food Safety Regulation and Compliance Technology, Applied Artificial Intelligence (vision-language models for document and label "
    "understanding), and Secure Web Application Engineering. It combines label reading with a rule engine, a reference-data matcher and report generation, and wraps them in a "
    "role-based web application.",
    "The regulatory background is the Food Safety and Standards Act, 2006 and its regulations, in particular the Food Safety and Standards (Labelling and Display) Regulations, 2020 "
    "and the Food Safety and Standards (Advertising and Claims) Regulations, 2018, which the demonstration rules of the project are derived from. All reference records and rules shipped "
    "with the project are clearly labelled as demonstration data; the owner must replace them with official data before real use.",
]

APPLICATIONS = [
    ("Field inspection of packaged foods", "Inspectors can check a product on the shelf from a phone: photographs, AI reading, verification and a documented decision in a single guided flow."),
    ("Evidence-backed reporting", "Each report contains the original photograph evidence, every extracted value with its confidence, the rules applied, the findings with the inspector's decisions and notes, and the final classification."),
    ("Reference data and rule management", "Administrators maintain product, manufacturer and licence records, upload packaging reference images, and write versioned compliance rules, with every change recorded in an audit log."),
    ("Inspector training and quality review", "The side-by-side display of AI values and inspector corrections, together with analytics on classifications and activity, helps supervisors review consistency and coach inspectors."),
    ("Complaint and suspicious-product follow-up", "Products that look suspicious can be flagged, documented with photographs and a report, and submitted as proposals for new reference records after administrator review."),
]

SOFTWARE = [
    ("Front-end", "Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4", "Responsive user interface for phone and desktop; client-side Google sign-in with the Firebase Web SDK"),
    ("Back-end", "Python 3.12, FastAPI, Pydantic v2, Uvicorn", "REST API with typed request/response models, authentication, workflow and report services"),
    ("Database", "MongoDB Atlas (PyMongo async driver), GridFS", "Documents, validators, indexes; photographs and reports stored as files"),
    ("Identity", "Firebase Authentication (Google provider), firebase-admin", "Sign-in, ID-token verification and role claims"),
    ("AI / OCR", "Google Gemini, NVIDIA vision models, optional PaddleOCR", "Label reading and the Ask-AI assistant, with ordered fallback"),
    ("Reports and images", "ReportLab, Pillow, NumPy", "13-section PDF reports; photo validation, quality checks and compression"),
    ("Hosting", "Render (two web services)", "Runs the API and the website; automatic deploys from the protected main branch"),
    ("CI/CD and security", "GitHub Actions, CodeQL, gitleaks, pip-audit, Bandit, Dependabot", "Quality, tests, security scans, build and release check on every change"),
    ("Testing", "pytest, Vitest, Playwright, httpx, Firebase Auth emulator", "Unit, integration, browser and attack-style tests"),
    ("Tools", "Visual Studio Code, Git and GitHub, uv, pnpm, Docker", "Development, version control and dependency management"),
]

HARDWARE = [
    ("Developer laptop / PC", "Intel Core i3 or better, 8 GB RAM recommended, 10 GB free storage"),
    ("User device", "Smartphone or tablet with a rear camera, or a laptop with a modern browser (Chrome, Edge, Firefox, Safari)"),
    ("Network", "Stable Wi-Fi or mobile data; the app shows a start-up banner when the hosted server is waking up"),
    ("Server (hosted)", "Render web service instances (free plan: 512 MB RAM each) and a MongoDB Atlas free-tier cluster"),
]

FUNCTIONAL = [
    ("FR-01", "Google sign-in only; new accounts stay pending until an administrator approves them and assigns a role."),
    ("FR-02", "Role-based access: inspector, administrator and Super Administrator; the first Super Administrator is set by a server variable."),
    ("FR-03", "Capture or upload up to five photographs of a product with automatic quality checks (resolution, blur)."),
    ("FR-04", "AI reading of 22 label fields with a confidence value per field; ordered provider fallback and an incomplete-inspection state when all fail."),
    ("FR-05", "Field verification: confirm, correct or clear each value, with format validation (FSSAI licence, dates, EAN-13, quantity)."),
    ("FR-06", "Matching against the reference database and evaluation of compliance rules and packaging comparison."),
    ("FR-07", "Findings review (accept, dismiss, correct with a note), final classification and a 13-section PDF report."),
    ("FR-08", "Inspection history with filters and CSV/Excel export; follow-up notes."),
    ("FR-09", "Ask-AI assistant with saved history and optional internet research when the inspector switches it on."),
    ("FR-10", "Product proposals from inspectors, reviewed by administrators."),
    ("FR-11", "Administrator console: users, reference database (manual, CSV import, AI-assisted draft), compliance rules with versioning, settings."),
    ("FR-12", "Analytics, read-only audit log with export, and a diagnostics page that tests every dependency."),
]

NONFUNCTIONAL = [
    ("Security", "Verified tokens, role checks, owner-scoped queries, strict input validation, rate limits, security headers and content-security policy."),
    ("Privacy", "Original photographs are kept only until the report is generated, then deleted; abandoned inspections expire after a retention period."),
    ("Reliability", "Temporary AI-provider errors are retried; photographs are never lost when AI fails; start-up banner for sleeping hosts."),
    ("Usability", "Mobile-first responsive layout, guided step-by-step workflow, plain-language errors and empty states."),
    ("Maintainability", "Layered code (routers, services, repositories), migrations, strict typing, automated tests and a CI pipeline."),
    ("Accountability", "AI value and inspector correction are both stored; administrator actions are written to an append-only audit log."),
]

ARCH_COMPONENTS = [
    ("Users", "Inspectors and administrators use the website from a phone or a computer. Photographs are captured with the device camera."),
    ("Front-end (Next.js on Render)", "Renders the landing page, sign-in, the six-step inspection workflow, Ask AI, history, and the administrator console. It signs the user in with Firebase and sends the ID token with every API call."),
    ("Back-end (FastAPI on Render)", "Verifies the token, checks the account and role, applies rate limits, runs the workflow services (reading, matching, rules, reports) and talks to the database and the AI providers."),
    ("MongoDB Atlas", "Stores users, inspections, reference records, rules, proposals, chat history, audit logs and usage counters; GridFS stores photographs and PDF reports."),
    ("Firebase Authentication", "Provides Google sign-in in the browser and custom claims (role) that the API checks against its own user records."),
    ("AI providers", "Gemini is tried first, then NVIDIA (and optionally Hugging Face); an optional PaddleOCR reader is the last resort. Providers receive only the photographs needed for a reading."),
    ("GitHub Actions and Render", "Every change is tested and scanned; after the checks pass on the protected main branch, Render builds and deploys both services."),
]

DATAFLOW = [
    "The inspector signs in with Google in the browser; Firebase returns an ID token.",
    "The front-end calls the API with the token; the API verifies it, loads the user record and checks that the account is active and has the required role.",
    "Photographs are uploaded to the API, validated (type, size, pixel count, quality) and stored in GridFS.",
    "The API sends the photographs to the AI provider chain; the structured answer (22 fields with confidence) is stored with the inspection.",
    "The inspector verifies the fields; the API then matches the product against the reference database and evaluates the compliance rules, storing findings.",
    "The inspector decides each finding and the final classification; the API generates the PDF report, stores it, and deletes the original photographs.",
    "Administrators manage reference data, rules and users; every administrative change is written to the audit log.",
]

MODULES = [
    ("User and access management", "Google sign-in, pending/active/disabled/declined states, role assignment, invitations and the Super Administrator bootstrap."),
    ("Inspection workflow", "Six guided steps with automatic saving: photographs, AI reading, verification, analysis, findings, decision and report."),
    ("AI extraction engine", "Prompting, provider chain (Gemini, NVIDIA, optional Hugging Face), retry on temporary errors, OCR fallback and field normalisation."),
    ("Field validation", "Format checks for FSSAI licence numbers, dates, EAN-13 barcodes and quantities; confidence handling."),
    ("Reference matching", "Fuzzy matching of brand, product and manufacturer against reference records, with licence validity and packaging comparison."),
    ("Compliance rules engine", "Versioned rules by category (required fields, claims keywords, date markings) producing findings with severity and regulatory reference."),
    ("Report generator", "13-section PDF with photographs, values, findings, decisions and disclaimers; compressed copies only."),
    ("Ask-AI assistant", "Context-aware assistant (current inspection, matched record, rules) with saved history and optional web research with sources."),
    ("Product proposals", "Inspectors submit unknown products; administrators request information, approve into the reference database or reject."),
    ("Administrator console", "Users, reference database with CSV import and AI-assisted drafts, rules with history, site images, limits and settings."),
    ("Analytics and audit", "Activity charts with table view, classifications, storage usage, and an append-only audit log with filters and export."),
    ("Diagnostics", "Live checks of configuration, database, file storage, Firebase credentials, each AI provider and the client address seen by the rate limiter."),
    ("Security layer", "Rate limiting, CORS, body-size limits, token verification, role checks, owner-scoped repositories and strict models."),
]

COLLECTIONS = [
    ("users", "Profile, role and status; created on first sign-in; linked to the Firebase user id."),
    ("user_invites", "Pre-approved e-mail addresses with a role, consumed at the first verified sign-in."),
    ("inspections", "One document per inspection: owner, status, category, photographs, 22 fields (value, AI value, confidence, status), findings, analysis, decision and report."),
    ("inspection_notes", "Follow-up notes written after a report is saved."),
    ("reference_records", "Product, brand, variant, manufacturer, licence and packaging data used for matching (demonstration data)."),
    ("compliance_rules", "Versioned labelling and claims rules with category, check type, severity and regulatory reference."),
    ("product_proposals", "Proposals for new reference records with reviews and messages."),
    ("chat_messages", "Ask-AI history per inspector."),
    ("audit_logs", "Append-only record of administrative actions."),
    ("usage_metrics, counters, settings", "Daily AI usage per user, number sequences (CS-year, REF), and the global settings document."),
    ("GridFS buckets", "photos, reports, refimages and siteimages."),
]

SECURITY_CONTROLS = [
    ("Sign-in", "Google only; the API verifies every Firebase ID token (signature, audience, expiry) and requires the Google provider."),
    ("Accounts", "New accounts start pending; only administrators approve and assign roles; privileged roles need a Super Administrator; the last Super Administrator is protected."),
    ("Authorization", "Role comes from the server-side user record cross-checked with token claims; stale claims are refreshed; administrator writes re-check token revocation."),
    ("Data isolation", "Every inspector query carries the owner id inside the database filter; documents of other users answer 'not found'. An automated test fails if a router touches MongoDB directly."),
    ("Input validation", "Strict Pydantic models reject unknown fields; search text is matched literally; uploads are decoded and size/pixel limited."),
    ("Abuse control", "Per-client rate limits (default, write, AI) plus an atomic per-user daily AI quota; the client address is read from a trusted proxy chain only."),
    ("Transport and browser", "HTTPS with HSTS, content-security policy, frame blocking, no sniffing, exact CORS origins, no-store caching for API data."),
    ("Secrets", "Keys live only in the hosting environment; the repository is scanned for secrets (gitleaks, GitHub push protection)."),
    ("Accountability", "Administrator actions and decisions are recorded; audit logs cannot be edited or deleted through the application."),
]

STRUCTURE = """food_inspection_toolkit/
  backend/
    app/
      main.py, auth.py, config.py, ratelimit.py      application factory, auth, settings, rate limiter
      routers/        inspections, proposals, assistant, admin, admin_reference, public, me
      services/       workflow, fields, matching, compliance, classification, images, report_pdf, ai/
      repositories/   owner-scoped data-access layer (the only code that touches MongoDB)
      models/         Pydantic request and response models
    migrations/       m0001 validators, m0002 indexes, m0003 demo data (explicit-only in production)
    scripts/          migrate, dev_seed, grant_role, reset_data
    tests/            75 backend tests
  frontend/
    src/app/          pages: landing, sign-in, inspector/*, admin/*
    src/components/   shell, UI kit, inspection, report, charts
    src/lib/          typed API client, Firebase wrapper, auth context
    e2e/              Playwright journeys (desktop + mobile)
  security-tests/     attacker-style regression suite (49 tests)
  .github/workflows/  CI pipeline, weekly security scan, Dependabot
  render.yaml         Render blueprint (API + website)
  docs/               specification, architecture, decisions, test report, deployment guide"""

ISSUES = [
    ("Memory exhaustion by a very large image", "An inspector could upload a small file that expands to over 100 million pixels, which could crash a 512 MB server.", "Hard 50-megapixel limit checked before the image is decoded; regression test added."),
    ("Rate limit bypass", "Spoofing the X-Forwarded-For header gave every request its own limit bucket.", "The header is ignored unless the number of trusted proxies is configured; the real client is read from the right; verified with a spoofing test."),
    ("Database error from a NUL byte in search text", "A search term containing a NUL character made MongoDB reject the query and returned a misleading 503.", "A literal-match helper strips NUL bytes; regression tests for all search boxes."),
    ("Crash without Firebase credentials", "With missing server credentials every token check failed with an unhandled error.", "Production refuses to start without credentials; other environments answer with a clean 503."),
    ("Reasoning AI model used all its tokens", "A 'reasoning' vision model returned no answer because it spent its token budget thinking.", "Reasoning is switched off for label reading; think-blocks are stripped; clear error text."),
    ("Temporary provider overload (HTTP 503)", "Gemini sometimes answered 'high demand'.", "Retry after 2 s and 5 s, then fall back to the next provider; real provider reasons shown in errors and in Diagnostics."),
    ("Flaky browser test", "A test attached photographs before the page had finished loading, so the event was lost.", "The test waits until React is attached to the input; 16 of 16 repeats pass."),
    ("Content-security policy blocked the emulator frame", "Firebase loads a helper frame that the first policy did not allow in tests.", "The frame source now includes the emulator and the configured auth domain."),
]

TEST_LEVELS = [
    ("Backend unit and integration", "pytest, httpx, MongoDB, Firebase Auth emulator", "75 tests: authentication, roles, inspections, matching, compliance, reports, providers (mocked HTTP), admin, rate limiting", "75 passed; 89 % line coverage (gate 85 %)"),
    ("Front-end unit", "Vitest, Testing Library", "API client, formatting and UI helpers", "9 passed"),
    ("Browser end-to-end", "Playwright (desktop 1440 px and iPhone 14)", "Accounts, full inspection journey, provider outage and retry, proposals, admin screens, Ask AI, security, analytics/audit, diagnostics, every screen without console errors or sideways scrolling", "44 passed, 2 skipped by design"),
    ("Attack-style security suite", "pytest, raw HTTP requests", "Forged and replayed tokens, role escalation, cross-user access, NoSQL injection, malicious uploads, races, rate-limit spoofing, CORS and headers", "49 passed"),
    ("Static analysis and scans", "ruff, mypy (strict), ESLint, TypeScript, Bandit, CodeQL, gitleaks, pip-audit, pnpm audit", "Style, types, code security, secrets, dependency vulnerabilities", "All clean on the final code"),
    ("Continuous integration", "GitHub Actions", "All of the above on every push and pull request", "Green on the protected main branch"),
]

# (number, title, focus bullets, result, image file, caption)
SCREENS = [
    ("Home Page", ["Landing page loads without errors on desktop and mobile", "Call-to-action buttons and feature summary are visible", "No horizontal scrolling or console errors"],
     "The public landing page presents the product, its three main capabilities (scan products, check compliance, generate reports) and the Get Started button.", "01-landing", "Landing page of CRATE-SCAN"),
    ("Sign In", ["Google-only sign-in with a clear explanation", "Notice that new accounts need administrator approval"],
     "The sign-in page offers a single 'Continue with Google' action. New users land on a waiting page until an administrator approves them; the tests confirm this flow.", "02-signin", "Google sign-in page"),
    ("Inspector Dashboard", ["Summary counters (total, completed, pending, proposals)", "Start-a-new-inspection call to action and continue-where-you-left-off list"],
     "Inspectors see their own inspections and can resume drafts. Counters and lists are scoped to the signed-in inspector only.", "03-inspector-dashboard", "Inspector dashboard"),
    ("New Inspection (Photographs)", ["Product category selection", "Upload or capture up to five photographs with guidance on which sides to include", "Quality checks and removal or replacement of a photo"],
     "A new inspection is created as soon as the category is chosen and saved automatically, so work is never lost. Photographs are validated for type, size, pixel count and quality.", "04-new-inspection", "Step 1 – product photographs"),
    ("Verify Extracted Information", ["22 label fields with AI confidence", "Confirm, edit or clear any value; automatic confirmation only for high-confidence fields", "Format validation notes"],
     "Every AI reading is shown with its confidence. The inspector confirms or corrects each value; the AI value is preserved next to the correction for accountability.", "05-verify-fields", "Step 2 – verification of extracted fields"),
    ("AI Review", ["Progress of the analysis steps", "Reference matching, licence check, packaging comparison and rule evaluation"],
     "The analysis runs against the reference database and the compliance rules while showing clear progress, and explains what happens if the analysis cannot be completed.", "06-ai-review", "Step 3 – AI review of the approved values"),
    ("Findings", ["Findings listed with severity, expected value, value found and rule reference", "Accept, dismiss or correct a finding with a note", "Photograph evidence side by side"],
     "Each finding shows what the rule expects, what was found on the pack, the evidence photograph and the regulatory reference; the inspector decides every one.", "07-findings", "Step 4 – findings and evidence"),
    ("Inspection Report", ["13-section report preview", "Download PDF, print and share actions", "Locked findings with follow-up notes"],
     "The report is generated as a PDF and previewed in the page. Original photographs are deleted once the report is saved; only compressed copies remain inside the PDF.", "08-report", "Step 5 – inspection report"),
    ("Inspection History", ["Search and filters by date, category and classification", "Export to CSV or Excel"],
     "Inspectors can find any past inspection and export their list; exports protect against spreadsheet formula injection.", "09-history", "Inspection history"),
    ("Ask AI Assistant", ["Questions about labelling requirements or the current inspection", "History is saved; internet research only when switched on"],
     "The assistant answers using the inspector's own inspection context and the demonstration rules. The screenshot was taken with the offline test provider, which labels its answers as test output.", "10-ask-ai", "Ask AI assistant"),
    ("Administrator Dashboard", ["Pending proposals and accounts awaiting approval", "Counts of reference products and rules", "Recent administrator activity"],
     "Administrators get a single overview of what needs attention: proposals to review, users to approve and recent changes.", "11-admin-dashboard", "Administrator dashboard"),
    ("Reference Database", ["Search and filters by category and status", "Add product, import CSV, archive and restore"],
     "Administrators maintain product, manufacturer and licence records. Records approved from proposals appear here, and all changes are audited.", "12-reference-database", "Reference database"),
    ("Compliance Rules", ["Rules by category with regulatory reference", "Active/draft status and last update", "Versioned edits with change notes"],
     "Rules are data, not code: an administrator can add or edit a rule and every edit creates a new version with history.", "13-compliance-rules", "Compliance rules"),
    ("Product Proposals", ["Proposals awaiting review", "Request information, approve or reject"],
     "Inspectors' proposals for unknown products are reviewed here; approval creates a new reference record.", "14-proposals", "Product proposals (administrator)"),
    ("User Management", ["Accounts awaiting approval with role selection", "Role and status changes", "Protected Super Administrator"],
     "New Google accounts wait here. The administrator approves with a role or declines. Only a Super Administrator can manage administrators.", "15-users", "User management"),
    ("Analytics", ["Period filter", "Charts for inspections per week and per category", "Chart/table toggle for accessibility"],
     "Activity charts have a table view so every figure can also be read as text; storage usage of the free database tier is shown.", "16-analytics", "Analytics"),
    ("Audit Logs", ["Filters by action, date and text", "Change details and CSV export", "Read-only"],
     "Every administrative action is listed with actor, record and the fields that changed. The application offers no way to edit or delete entries.", "17-audit-logs", "Audit logs"),
    ("System Diagnostics", ["Run all checks or one check", "Database, file storage, Firebase, each AI provider, client address", "Real reason and fix hints on failure"],
     "The page tests every dependency with a live call and shows working, needs attention, failing or not tested, with the provider's own error text when something fails.", "18-diagnostics", "System diagnostics"),
    ("Settings", ["Website images, general, AI and OCR, limits and usage", "Replaceable placeholders"],
     "Administrators control the images shown on public pages, AI options, daily AI limits and photograph retention.", "19-settings", "Settings"),
]

MOBILE_NOTE = ("The same screens were captured on an iPhone 14 viewport (390 px). The mobile layout uses a bottom tab bar and a 'More' list; the automated tests confirm "
               "that every page renders without horizontal scrolling or console errors on both layouts.")

CONCLUSION = ("CRATE-SCAN achieves its objective of giving food-safety inspectors a guided, evidence-based and secure way to inspect packaged products. The platform reads labels with AI "
              "while keeping the inspector in charge, compares the verified values with reference data and configurable rules, and produces a complete PDF report. The system is built with a "
              "layered architecture, role-based access with administrator approval, owner-scoped data access, privacy-conscious file handling and a full automated test and security pipeline. "
              "Testing at five levels (75 backend tests, 9 unit tests, 44 browser tests, 49 attack-style tests and static scans) gives confidence in correctness and security. "
              "Limitations remain: the reference records and rules are demonstration data, live AI providers can be slow or unavailable (handled by retry, fallback and the incomplete state), "
              "and the free hosting tiers sleep when idle.")

FUTURE = [
    ("Official reference data", "Replace the demonstration records and rules with official, regularly updated data and connect to licence-verification services where available."),
    ("Mobile application", "Offline-capable progressive web app or native app with background upload and on-device barcode scanning."),
    ("Multilingual labels", "Read and compare labels printed in Hindi, Telugu and other regional languages."),
    ("Model quality", "Evaluate and fine-tune extraction models on real label images; add per-field accuracy dashboards."),
    ("Workflow and teams", "Inspection assignment, supervisor review, batch-level trend alerts and sample-collection records."),
    ("Operations", "Paid hosting tiers without sleeping, shared rate-limit store for several instances, scheduled backups and uptime monitoring."),
]

BIBLIOGRAPHY = [
    ("FastAPI Documentation", "https://fastapi.tiangolo.com/"),
    ("Next.js Documentation", "https://nextjs.org/docs"),
    ("React Documentation", "https://react.dev/"),
    ("MongoDB Documentation", "https://www.mongodb.com/docs/"),
    ("Firebase Authentication Documentation", "https://firebase.google.com/docs/auth"),
    ("Pydantic Documentation", "https://docs.pydantic.dev/"),
    ("Google Gemini API Documentation", "https://ai.google.dev/gemini-api/docs"),
    ("Render Documentation", "https://render.com/docs"),
    ("GitHub Actions Documentation", "https://docs.github.com/actions"),
    ("Playwright Documentation", "https://playwright.dev/docs/intro"),
    ("OWASP Application Security Verification Standard", "https://owasp.org/www-project-application-security-verification-standard/"),
    ("Food Safety and Standards Authority of India", "https://www.fssai.gov.in/"),
    ("ReportLab User Guide", "https://docs.reportlab.com/"),
    ("uv – Python package manager", "https://docs.astral.sh/uv/"),
]

CODE_SNIPPETS = [
    ("Authentication dependency (verified user, active account, role check)", "backend/app/auth.py", r"async def current_principal", 34,
     "Every protected route depends on this function: it verifies the Firebase token, loads the user record and refuses pending, declined or disabled accounts."),
    ("Owner-scoped data access", "backend/app/repositories/inspections.py", r"def _own", 14,
     "All inspector queries include the owner id inside the database filter, so another inspector's document simply does not exist from the caller's point of view."),
    ("Rate limiter with trusted-proxy client address", "backend/app/ratelimit.py", r"    def _client", 20,
     "The client address is read from the forwarded header only when the number of trusted proxies is configured, and then from the right-hand side."),
    ("Ordered AI provider chain with OCR fallback", "backend/app/services/ai/chain.py", r"async def run_extract", 34,
     "Each configured provider is tried in order; failures are recorded as attempts, and the optional OCR reader is the last resort."),
    ("Field validation helper (EAN-13 check digit)", "backend/app/services/fields.py", r"def ean13_valid", 6,
     "Format checks give the inspector early warnings, such as an invalid barcode check digit."),
    ("Front-end API client with token refresh", "frontend/src/lib/api.ts", r"claims_stale", 14,
     "When the server says the role changed or the token expired, the client refreshes the Firebase token once and retries the call."),
]
