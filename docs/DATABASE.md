# CRATE-SCAN — Database

MongoDB Atlas (C1 free cluster), database per environment: `crate_scan_dev`, `crate_scan_test` (CI / pytest,
dropped every run), `crate_scan_prod`. Driver: PyMongo native async (`AsyncMongoClient`, `AsyncGridFSBucket`).

## Collections

| Collection | `_id` | Owner field | Purpose / key fields |
|------------|-------|-------------|----------------------|
| `users` | Firebase UID | `_id` | email (unique), name, photo_url, role (`inspector`/`admin`/`super_admin`/null), status (`pending`/`active`/`disabled`/`declined`), designation, office, phone, approved_at/by, last_active_at |
| `user_invites` | lower-case email | — | Admin pre-authorisation: role applied on that email's first verified Google sign-in, then deleted |
| `inspections` | `CS-YYYY-NNNN` | `owner_uid` | status (`draft`→`extracted`/`incomplete`→`analysed`→`completed`), photos[] (GridFS id, label, quality, crop), photos_deleted, photo_expires_at, category (+source), extraction {status, provider, attempts[], ocr_used}, fields{key: ai_value, ai_confidence, confidence_level, source_photo, flag, note, value, status, history[]}, summary {product_name, brand, fields_extracted}, analysis {reference, licence, packaging, compliance} (kept separate, BR-10), findings[] (+inspector decision), suggestion (provisional), decision {classification, remarks}, report {file_id, size, pages, signature_name}, analysis_stale, proposal_id |
| `inspection_notes` | ObjectId | `owner_uid` | Follow-up notes; never modify the original inspection |
| `reference_records` | `REF-NNNN` | admin-managed | Combined product + manufacturer + demo licence + `packaging_versions[]{id,label,notes,images[]{file_id,side}}`, status (`active`/`archived`), demo=true, source |
| `compliance_rules` | ObjectId | admin-managed | code (unique), title, category (4 + `all`), check_type (`required_field`/`pattern`/`claim_keywords`/`date_not_expired`), field, pattern, keywords, severity, requirement, reference, status (`active`/`draft`/`archived`), version, history[≤50] |
| `product_proposals` | `PR-YYYY-NNNN` | `owner_uid` | inspection_id (unique per owner), product{}, remarks, status (`pending`/`approved`/`rejected`/`info_requested`), reviews[≤50], messages[], reference_id, report_file_id |
| `chat_messages` | ObjectId | `owner_uid` | One general Ask-AI history per inspector; role, text, web, sources[], provider |
| `audit_logs` | ObjectId | — | Append-only: actor, action, target_type, target_id, summary, changes, at. No update/delete API |
| `usage_metrics` | ObjectId | `uid` | One doc per user per day: ai_calls (atomic quota), active flag (DAU/WAU/MAU) |
| `settings` | `"global"` | — | general, ai, limits, images{hero,signin,banner} |
| `counters` | `inspection-YYYY`, `proposal-YYYY`, `reference-0` | — | Atomic ID sequences |
| `_migrations` | migration name | — | Applied migrations |

### GridFS buckets (D-03)
| Bucket | Content | Metadata | Lifetime |
|--------|---------|----------|----------|
| `photos` | Inspection originals (full quality) | owner_uid, inspection_id, expires_at | **Temporary**: deleted right after the report is generated, or after `photo_retention_days` (default 7) by cleanup |
| `reports` | Generated PDFs (compressed photos embedded) | owner_uid, inspection_id | Permanent |
| `refimages` | Reference packaging photos | reference_id, uploaded_by | Until removed by an admin |
| `siteimages` | Landing / sign-in / banner images | key | Until replaced or reset |

## Relationships and consistency
- `inspections.photos[].id` → `photos.files._id`; `report.file_id` → `reports.files._id`. Upload: file first, then
  document; if the document update fails the file is deleted. Delete photo: document first, then file.
- `product_proposals.inspection_id` → `inspections._id` (same owner); approval creates a `reference_records` doc and
  stores `reference_id`.
- Orphan GridFS chunks are swept by `maintenance.cleanup_expired_photos()` (runs at most hourly when inspections are
  created, via Admin → Storage cleanup, or `python -m scripts.cleanup`).

## Validators and indexes
`migrations/m0001_validators.py` — `$jsonSchema`, `validationLevel: strict`, `validationAction: error` on every
collection above (enums for status/role/category/classification, ID patterns, array caps).
`migrations/m0002_indexes.py` — owner+date compound indexes for every user-owned list, unique email / rule code /
usage day / one-proposal-per-inspection, licence + GTIN lookups, `photos.files.metadata.expires_at`.

## Migrations
```
cd backend
uv run python -m scripts.migrate --dry-run   # list pending
uv run python -m scripts.migrate             # apply (idempotent, recorded in _migrations)
```
Never run on application start. Production: run from your machine with the production `MONGODB_URI` after the deploy
that needs it (see DEPLOYMENT.md, Phase 4). `m0003_seed_demo` only inserts missing fictional demo records/rules
(`$setOnInsert`), never overwrites admin edits.

## Data-access layer and authorization
Only `app/repositories/*` touch collections (enforced by `tests/test_architecture.py`). User-owned functions take the
verified `Principal` and add `owner_uid` to every query, update and delete; foreign IDs return 404. Admin functions
call `ensure_admin()` (defence in depth behind the router guard). Client input reaches queries only through typed
Pydantic values; free-text search is `re.escape`d, so operator objects like `{"$gt": ""}` are treated as text.

## Backup and restore (C1 has no automated backups)
```
mongodump --uri "$MONGODB_URI" --db crate_scan_prod --archive=crate-scan-$(date +%F).gz --gzip
mongorestore --uri "$MONGODB_URI" --archive=crate-scan-YYYY-MM-DD.gz --gzip --nsInclude 'crate_scan_prod.*'
```
Upgrade to Atlas M10+ (C2) for automated backups; no code change.
