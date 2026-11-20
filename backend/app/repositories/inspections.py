"""Inspections, follow-up notes. Every function takes the Principal and filters by owner_uid
(NFR-02). A document owned by someone else is reported as 404."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from app.errors import AppError, not_found
from app.principal import Principal
from app.repositories.base import col, ensure_admin, next_sequence, now, paginate, rx_escape


def _own(p: Principal, inspection_id: str) -> dict[str, Any]:
    return {"_id": inspection_id, "owner_uid": p.uid}


async def create(p: Principal, retention_days: int) -> dict[str, Any]:
    ts = now()
    seq = await next_sequence("inspection", ts.year)
    doc: dict[str, Any] = {
        "_id": f"CS-{ts.year}-{seq:04d}",
        "owner_uid": p.uid,
        "owner_name": p.name,
        "owner_email": p.email,
        "status": "draft",
        "created_at": ts,
        "updated_at": ts,
        "photos": [],
        "photos_deleted": False,
        "photo_expires_at": ts + timedelta(days=retention_days),
        "category": None,
        "category_source": None,
        "extraction": {"status": "not_started", "attempts": []},
        "fields": {},
        "summary": {"product_name": None, "brand": None},
        "analysis": None,
        "findings": [],
        "suggestion": None,
        "decision": None,
        "report": None,
        "proposal_id": None,
    }
    await col("inspections").insert_one(doc)
    return doc


async def get(p: Principal, inspection_id: str) -> dict[str, Any]:
    doc = await col("inspections").find_one(_own(p, inspection_id))
    if not doc:
        raise not_found("Inspection")
    return doc


async def update(
    p: Principal,
    inspection_id: str,
    set_fields: dict[str, Any],
    expect_status: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flt = _own(p, inspection_id)
    if expect_status:
        flt["status"] = {"$in": expect_status}
    upd: dict[str, Any] = {"$set": dict(set_fields, updated_at=now())}
    if extra:
        for k, v in extra.items():
            upd.setdefault(k, {}).update(v)
    doc = await col("inspections").find_one_and_update(
        flt, upd, return_document=ReturnDocument.AFTER
    )
    if doc is None:
        await get(p, inspection_id)  # raises 404 when not owned
        raise AppError(409, "invalid_state", "This step is not available for the inspection now.")
    return doc


async def add_photo(
    p: Principal, inspection_id: str, photo: dict[str, Any], max_photos: int
) -> dict[str, Any]:
    doc = await col("inspections").find_one_and_update(
        {
            **_own(p, inspection_id),
            "status": {"$in": ["draft", "incomplete", "extracted", "analysed"]},
            f"photos.{max_photos - 1}": {"$exists": False},
        },
        {
            "$push": {"photos": photo},
            "$set": {"updated_at": now(), "status": "draft", "extraction.status": "not_started"},
        },
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        existing = await get(p, inspection_id)
        if len(existing.get("photos", [])) >= max_photos:
            raise AppError(
                409, "too_many_photos", f"An inspection can have up to {max_photos} photographs."
            )
        raise AppError(
            409, "invalid_state", "Photographs can no longer be changed for this inspection."
        )
    return doc


async def remove_photo(p: Principal, inspection_id: str, photo_id: str) -> dict[str, Any]:
    doc = await col("inspections").find_one_and_update(
        {**_own(p, inspection_id), "status": {"$ne": "completed"}, "photos.id": photo_id},
        {
            "$pull": {"photos": {"id": photo_id}},
            "$set": {"updated_at": now(), "status": "draft", "extraction.status": "not_started"},
        },
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise not_found("Photo")
    return doc


async def update_photo(
    p: Principal, inspection_id: str, photo_id: str, changes: dict[str, Any]
) -> dict[str, Any]:
    sets = {f"photos.$.{k}": v for k, v in changes.items()}
    sets["updated_at"] = now()
    doc = await col("inspections").find_one_and_update(
        {**_own(p, inspection_id), "status": {"$ne": "completed"}, "photos.id": photo_id},
        {"$set": sets},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise not_found("Photo")
    return doc


async def delete_draft(p: Principal, inspection_id: str) -> dict[str, Any]:
    doc = await col("inspections").find_one_and_delete(
        {**_own(p, inspection_id), "status": {"$in": ["draft", "incomplete", "extracted"]}}
    )
    if doc is None:
        await get(p, inspection_id)
        raise AppError(409, "invalid_state", "Only unfinished inspections can be deleted.")
    return doc


def _history_filter(p: Principal, q: dict[str, Any]) -> dict[str, Any]:
    flt: dict[str, Any] = {"owner_uid": p.uid}
    if q.get("q"):
        rx = {"$regex": rx_escape(q["q"]), "$options": "i"}
        flt["$or"] = [{"summary.product_name": rx}, {"summary.brand": rx}, {"_id": rx}]
    if q.get("category"):
        flt["category"] = q["category"]
    if q.get("classification"):
        flt["decision.classification"] = q["classification"]
    if q.get("status"):
        flt["status"] = q["status"]
    if q.get("date_from") or q.get("date_to"):
        rng: dict[str, Any] = {}
        if q.get("date_from"):
            rng["$gte"] = q["date_from"]
        if q.get("date_to"):
            rng["$lte"] = q["date_to"]
        flt["created_at"] = rng
    return flt


_LIST_PROJ = {"fields": 0, "analysis": 0}


async def list_owned(p: Principal, q: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    return await paginate(
        "inspections",
        _history_filter(p, q),
        q.get("page", 1),
        q.get("page_size", 20),
        [("created_at", -1)],
        _LIST_PROJ,
    )


async def export_owned(p: Principal, q: dict[str, Any], limit: int = 5000) -> list[dict[str, Any]]:
    cur = (
        col("inspections")
        .find(_history_filter(p, q), _LIST_PROJ)
        .sort("created_at", -1)
        .limit(limit)
    )
    return [d async for d in cur]


async def dashboard(p: Principal) -> dict[str, Any]:
    c = col("inspections")
    total = await c.count_documents({"owner_uid": p.uid})
    completed = await c.count_documents({"owner_uid": p.uid, "status": "completed"})
    pending = await c.count_documents({"owner_uid": p.uid, "status": {"$ne": "completed"}})
    proposals = await col("product_proposals").count_documents({"owner_uid": p.uid})
    cont = [
        d
        async for d in c.find({"owner_uid": p.uid, "status": {"$ne": "completed"}}, _LIST_PROJ)
        .sort("updated_at", -1)
        .limit(3)
    ]
    recent = [
        d async for d in c.find({"owner_uid": p.uid}, _LIST_PROJ).sort("created_at", -1).limit(5)
    ]
    by_cls: dict[str, int] = {"verified": 0, "not_verified": 0, "suspicious": 0}
    async for row in await c.aggregate(
        [
            {"$match": {"owner_uid": p.uid, "decision.classification": {"$ne": None}}},
            {"$group": {"_id": "$decision.classification", "n": {"$sum": 1}}},
        ]
    ):
        by_cls[row["_id"]] = row["n"]
    return {
        "total": total,
        "completed": completed,
        "pending_reviews": pending,
        "proposals": proposals,
        "continue_items": cont,
        "recent": recent,
        "by_classification": by_cls,
    }


async def add_note(p: Principal, inspection_id: str, text: str) -> dict[str, Any]:
    await get(p, inspection_id)
    doc = {"inspection_id": inspection_id, "owner_uid": p.uid, "text": text, "created_at": now()}
    res = await col("inspection_notes").insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def list_notes(p: Principal, inspection_id: str) -> list[dict[str, Any]]:
    cur = (
        col("inspection_notes")
        .find({"inspection_id": inspection_id, "owner_uid": p.uid})
        .sort("created_at", 1)
        .limit(200)
    )
    return [d async for d in cur]


async def mark_photos_deleted(p: Principal, inspection_id: str) -> None:
    await col("inspections").update_one(
        _own(p, inspection_id), {"$set": {"photos_deleted": True, "updated_at": now()}}
    )


# ---------------------------------------------------------------- system / admin (no user data leaks)


async def mark_expired_photos_deleted(file_ids: list[ObjectId]) -> None:
    ids = [str(f) for f in file_ids]
    if ids:
        await col("inspections").update_many(
            {"photos.id": {"$in": ids}}, {"$set": {"photos_deleted": True}}
        )


async def stats(admin: Principal, since: datetime) -> dict[str, Any]:
    ensure_admin(admin)
    c = col("inspections")

    async def group(field: str, match: dict[str, Any] | None = None) -> dict[str, int]:
        out: dict[str, int] = {}
        pipe: list[dict[str, Any]] = [
            {"$match": match or {}},
            {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
        ]
        async for row in await c.aggregate(pipe):
            out[str(row["_id"]) if row["_id"] is not None else "unknown"] = row["n"]
        return out

    by_day: list[dict[str, Any]] = []
    async for row in await c.aggregate(
        [
            {"$match": {"created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "n": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
    ):
        by_day.append({"day": row["_id"], "count": row["n"]})
    top: list[dict[str, Any]] = []
    async for row in await c.aggregate(
        [
            {"$match": {"summary.product_name": {"$nin": [None, ""]}}},
            {
                "$group": {
                    "_id": {"p": "$summary.product_name", "b": "$summary.brand"},
                    "n": {"$sum": 1},
                }
            },
            {"$sort": {"n": -1}},
            {"$limit": 8},
        ]
    ):
        top.append(
            {"product": row["_id"].get("p"), "brand": row["_id"].get("b"), "count": row["n"]}
        )
    return {
        "total": await c.count_documents({}),
        "since": await c.count_documents({"created_at": {"$gte": since}}),
        "by_category": await group("category"),
        "by_classification": await group("decision.classification", {"decision": {"$ne": None}}),
        "by_status": await group("status"),
        "by_day": by_day,
        "top": top,
    }
