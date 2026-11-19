"""Demo compliance rules with version history (REQ-056)."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from app.errors import AppError, not_found
from app.principal import Principal
from app.repositories import audit
from app.repositories.base import col, ensure_admin, now, paginate, rx_escape

_TRACKED = (
    "title",
    "category",
    "check_type",
    "field",
    "pattern",
    "keywords",
    "severity",
    "requirement",
    "reference",
    "status",
    "notes",
)


def _oid(rule_id: str) -> ObjectId:
    if not ObjectId.is_valid(rule_id):
        raise not_found("Rule")
    return ObjectId(rule_id)


def to_out(d: dict[str, Any]) -> dict[str, Any]:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


async def active_for_category(category: str | None) -> list[dict[str, Any]]:
    cats = ["all"] + ([category] if category else [])
    cur = (
        col("compliance_rules")
        .find({"status": "active", "category": {"$in": cats}})
        .sort("code", 1)
    )
    return [d async for d in cur]


async def list_rules(
    admin: Principal,
    q: str | None,
    category: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    ensure_admin(admin)
    flt: dict[str, Any] = {}
    if q:
        rx = {"$regex": rx_escape(q), "$options": "i"}
        flt["$or"] = [{"code": rx}, {"title": rx}, {"reference": rx}]
    if category:
        flt["category"] = category
    flt["status"] = status if status else {"$ne": "archived"}
    items, total = await paginate(
        "compliance_rules", flt, page, page_size, [("code", 1)], {"history": {"$slice": -10}}
    )
    return [to_out(d) for d in items], total


async def get(admin: Principal, rule_id: str) -> dict[str, Any]:
    ensure_admin(admin)
    d = await col("compliance_rules").find_one({"_id": _oid(rule_id)})
    if not d:
        raise not_found("Rule")
    return to_out(d)


async def create(admin: Principal, data: dict[str, Any]) -> dict[str, Any]:
    ensure_admin(admin)
    if await col("compliance_rules").find_one({"code": data["code"]}):
        raise AppError(409, "conflict", f"Rule code {data['code']} already exists.")
    doc = {
        **data,
        "version": 1,
        "demo": True,
        "created_at": now(),
        "updated_at": now(),
        "history": [
            {"version": 1, "at": now(), "by": admin.name, "note": "Created", "changes": {}}
        ],
    }
    res = await col("compliance_rules").insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit.log(admin, "rule.create", "rule", data["code"], f"Created rule {data['code']}")
    return to_out(doc)


async def update(
    admin: Principal, rule_id: str, changes: dict[str, Any], note: str
) -> dict[str, Any]:
    ensure_admin(admin)
    before = await col("compliance_rules").find_one({"_id": _oid(rule_id)})
    if not before:
        raise not_found("Rule")
    upd = {k: v for k, v in changes.items() if v is not None and k in _TRACKED}
    diff = {k: [before.get(k), v] for k, v in upd.items() if before.get(k) != v}
    if not diff:
        return to_out(before)
    version = int(before.get("version", 1)) + 1
    entry = {
        "version": version,
        "at": now(),
        "by": admin.name,
        "note": note or "Edited",
        "changes": diff,
    }
    doc = await col("compliance_rules").find_one_and_update(
        {"_id": before["_id"], "version": before.get("version", 1)},
        {
            "$set": {**upd, "version": version, "updated_at": now()},
            "$push": {"history": {"$each": [entry], "$slice": -50}},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise AppError(
            409, "conflict", "The rule was changed by someone else. Reload and try again."
        )
    action = "rule.archive" if upd.get("status") == "archived" else "rule.update"
    await audit.log(
        admin, action, "rule", before["code"], f"Rule {before['code']} v{version}", diff
    )
    return to_out(doc)


async def stats() -> dict[str, Any]:
    c = col("compliance_rules")
    last = await c.find_one({}, sort=[("updated_at", -1)])
    cats = await c.distinct("category", {"status": "active"})
    return {
        "active": await c.count_documents({"status": "active"}),
        "draft": await c.count_documents({"status": "draft"}),
        "archived": await c.count_documents({"status": "archived"}),
        "categories": len([x for x in cats if x != "all"]) if "all" not in cats else 4,
        "last_update": last.get("updated_at") if last else None,
    }
