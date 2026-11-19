"""Create collections with $jsonSchema validators (strict level, error action)."""

from __future__ import annotations

from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

DATE = {"bsonType": "date"}
STR = {"bsonType": "string"}
NSTR = {"bsonType": ["string", "null"]}
CATS = ["beverages", "snacks", "dairy", "staples"]

SCHEMAS: dict[str, dict[str, Any]] = {
    "users": {
        "bsonType": "object",
        "required": ["_id", "email", "status", "created_at"],
        "properties": {
            "_id": STR,
            "email": {"bsonType": "string", "maxLength": 320},
            "name": STR,
            "role": {"enum": [None, "inspector", "admin", "super_admin"]},
            "status": {"enum": ["pending", "active", "disabled", "declined"]},
            "designation": STR,
            "office": STR,
            "phone": STR,
            "created_at": DATE,
        },
    },
    "user_invites": {
        "bsonType": "object",
        "required": ["_id", "email", "role", "created_at"],
        "properties": {
            "email": STR,
            "role": {"enum": ["inspector", "admin", "super_admin"]},
            "created_at": DATE,
        },
    },
    "inspections": {
        "bsonType": "object",
        "required": ["_id", "owner_uid", "status", "created_at", "photos", "fields", "findings"],
        "properties": {
            "_id": {"bsonType": "string", "pattern": "^CS-[0-9]{4}-[0-9]{4,6}$"},
            "owner_uid": STR,
            "status": {"enum": ["draft", "incomplete", "extracted", "analysed", "completed"]},
            "category": {"enum": [None, *CATS]},
            "photos": {"bsonType": "array", "maxItems": 5},
            "fields": {"bsonType": "object"},
            "findings": {"bsonType": "array", "maxItems": 200},
            "decision": {
                "bsonType": ["object", "null"],
                "properties": {
                    "classification": {"enum": ["verified", "not_verified", "suspicious"]}
                },
            },
            "created_at": DATE,
        },
    },
    "inspection_notes": {
        "bsonType": "object",
        "required": ["inspection_id", "owner_uid", "text", "created_at"],
        "properties": {
            "inspection_id": STR,
            "owner_uid": STR,
            "text": {"bsonType": "string", "maxLength": 8000},
            "created_at": DATE,
        },
    },
    "reference_records": {
        "bsonType": "object",
        "required": ["_id", "product_name", "brand", "category", "status", "demo"],
        "properties": {
            "_id": {"bsonType": "string", "pattern": "^REF-[0-9]{4,6}$"},
            "product_name": STR,
            "brand": STR,
            "category": {"enum": CATS},
            "status": {"enum": ["active", "archived"]},
            "demo": {"bsonType": "bool"},
            "gtin": STR,
            "manufacturer": {"bsonType": "object"},
            "licence": {
                "bsonType": "object",
                "properties": {
                    "number": STR,
                    "status": {"enum": ["active", "expired", "suspended"]},
                },
            },
            "packaging_versions": {"bsonType": "array", "maxItems": 20},
        },
    },
    "compliance_rules": {
        "bsonType": "object",
        "required": [
            "code",
            "title",
            "category",
            "check_type",
            "field",
            "severity",
            "status",
            "version",
        ],
        "properties": {
            "code": STR,
            "title": STR,
            "category": {"enum": [*CATS, "all"]},
            "check_type": {
                "enum": ["required_field", "pattern", "claim_keywords", "date_not_expired"]
            },
            "field": STR,
            "pattern": NSTR,
            "severity": {"enum": ["info", "warning", "high"]},
            "status": {"enum": ["active", "draft", "archived"]},
            "version": {"bsonType": "int", "minimum": 1},
        },
    },
    "product_proposals": {
        "bsonType": "object",
        "required": ["_id", "inspection_id", "owner_uid", "product", "status", "created_at"],
        "properties": {
            "_id": {"bsonType": "string", "pattern": "^PR-[0-9]{4}-[0-9]{4,6}$"},
            "owner_uid": STR,
            "product": {"bsonType": "object"},
            "status": {"enum": ["pending", "approved", "rejected", "info_requested"]},
            "reviews": {"bsonType": "array", "maxItems": 50},
            "created_at": DATE,
        },
    },
    "chat_messages": {
        "bsonType": "object",
        "required": ["owner_uid", "role", "text", "created_at"],
        "properties": {
            "owner_uid": STR,
            "role": {"enum": ["user", "assistant"]},
            "text": {"bsonType": "string", "maxLength": 20000},
            "created_at": DATE,
        },
    },
    "audit_logs": {
        "bsonType": "object",
        "required": ["actor_uid", "action", "target_type", "target_id", "at"],
        "properties": {
            "actor_uid": STR,
            "action": STR,
            "target_type": STR,
            "target_id": STR,
            "at": DATE,
        },
    },
    "usage_metrics": {
        "bsonType": "object",
        "required": ["uid", "day"],
        "properties": {
            "uid": STR,
            "day": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
            "ai_calls": {"bsonType": ["int", "long"], "minimum": 0},
        },
    },
    "settings": {"bsonType": "object", "required": ["_id"]},
    "counters": {"bsonType": "object", "required": ["_id", "seq"]},
}


async def up(db: AsyncDatabase) -> None:  # type: ignore[type-arg]
    existing = set(await db.list_collection_names())
    for name, schema in SCHEMAS.items():
        if name not in existing:
            await db.create_collection(
                name,
                validator={"$jsonSchema": schema},
                validationLevel="strict",
                validationAction="error",
            )
        else:
            await db.command(
                {
                    "collMod": name,
                    "validator": {"$jsonSchema": schema},
                    "validationLevel": "strict",
                    "validationAction": "error",
                }
            )
