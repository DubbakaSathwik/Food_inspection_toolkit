"""Indexes for frequent queries, uniqueness rules and GridFS retention lookups."""

from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

INDEXES: dict[str, list[tuple[list[tuple[str, int]], dict[str, Any]]]] = {
    "users": [
        ([("email", ASCENDING)], {"unique": True, "name": "email_unique"}),
        ([("status", ASCENDING), ("created_at", DESCENDING)], {"name": "status_created"}),
        ([("role", ASCENDING)], {"name": "role"}),
    ],
    "inspections": [
        ([("owner_uid", ASCENDING), ("created_at", DESCENDING)], {"name": "owner_created"}),
        (
            [("owner_uid", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)],
            {"name": "owner_status"},
        ),
        (
            [("owner_uid", ASCENDING), ("decision.classification", ASCENDING)],
            {"name": "owner_class"},
        ),
        ([("created_at", DESCENDING)], {"name": "created"}),
        ([("photos.id", ASCENDING)], {"name": "photo_ids"}),
    ],
    "inspection_notes": [
        (
            [("owner_uid", ASCENDING), ("inspection_id", ASCENDING), ("created_at", ASCENDING)],
            {"name": "owner_insp"},
        )
    ],
    "reference_records": [
        ([("status", ASCENDING), ("updated_at", DESCENDING)], {"name": "status_updated"}),
        ([("licence.number", ASCENDING)], {"name": "licence"}),
        ([("gtin", ASCENDING)], {"name": "gtin"}),
        ([("brand", ASCENDING), ("product_name", ASCENDING)], {"name": "brand_product"}),
        ([("packaging_versions.images.file_id", ASCENDING)], {"name": "image_ids"}),
    ],
    "compliance_rules": [
        ([("code", ASCENDING)], {"unique": True, "name": "code_unique"}),
        ([("status", ASCENDING), ("category", ASCENDING)], {"name": "status_category"}),
    ],
    "product_proposals": [
        ([("owner_uid", ASCENDING), ("created_at", DESCENDING)], {"name": "owner_created"}),
        ([("status", ASCENDING), ("created_at", ASCENDING)], {"name": "status_created"}),
        (
            [("owner_uid", ASCENDING), ("inspection_id", ASCENDING)],
            {"unique": True, "name": "one_per_inspection"},
        ),
    ],
    "chat_messages": [
        ([("owner_uid", ASCENDING), ("created_at", DESCENDING)], {"name": "owner_created"})
    ],
    "audit_logs": [
        ([("at", DESCENDING)], {"name": "at"}),
        ([("action", ASCENDING), ("at", DESCENDING)], {"name": "action_at"}),
        ([("target_id", ASCENDING), ("at", DESCENDING)], {"name": "target_at"}),
    ],
    "usage_metrics": [
        ([("uid", ASCENDING), ("day", ASCENDING)], {"unique": True, "name": "uid_day"}),
        ([("day", ASCENDING)], {"name": "day"}),
    ],
    "photos.files": [
        ([("metadata.expires_at", ASCENDING)], {"name": "expires_at"}),
        ([("metadata.owner_uid", ASCENDING)], {"name": "owner"}),
    ],
}


async def up(db: AsyncDatabase) -> None:  # type: ignore[type-arg]
    for coll, specs in INDEXES.items():
        for keys, opts in specs:
            await db[coll].create_index(keys, **opts)  # idempotent for identical definitions
