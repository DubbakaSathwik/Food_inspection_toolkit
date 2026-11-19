"""Product proposals: inspectors see only their own; admins review all (REQ-040..042)."""

from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from app.errors import AppError, not_found
from app.principal import Principal
from app.repositories import audit
from app.repositories.base import col, ensure_admin, next_sequence, now, paginate


async def create(
    p: Principal,
    inspection_id: str,
    product: dict[str, Any],
    remarks: str,
    report_file_id: str | None,
    photo_count: int,
) -> dict[str, Any]:
    if await col("product_proposals").find_one(
        {"inspection_id": inspection_id, "owner_uid": p.uid}
    ):
        raise AppError(409, "conflict", "A proposal for this inspection already exists.")
    ts = now()
    seq = await next_sequence("proposal", ts.year)
    doc: dict[str, Any] = {
        "_id": f"PR-{ts.year}-{seq:04d}",
        "inspection_id": inspection_id,
        "owner_uid": p.uid,
        "owner_name": p.name,
        "product": product,
        "remarks": remarks,
        "status": "pending",
        "reviews": [],
        "messages": [],
        "reference_id": None,
        "report_file_id": report_file_id,
        "photo_count": photo_count,
        "created_at": ts,
        "updated_at": ts,
    }
    await col("product_proposals").insert_one(doc)
    return doc


async def list_own(p: Principal, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    return await paginate(
        "product_proposals", {"owner_uid": p.uid}, page, page_size, [("created_at", -1)]
    )


async def get_own(p: Principal, proposal_id: str) -> dict[str, Any]:
    d = await col("product_proposals").find_one({"_id": proposal_id, "owner_uid": p.uid})
    if not d:
        raise not_found("Proposal")
    return d


async def reply(p: Principal, proposal_id: str, message: str) -> dict[str, Any]:
    d = await col("product_proposals").find_one_and_update(
        {"_id": proposal_id, "owner_uid": p.uid, "status": "info_requested"},
        {
            "$push": {
                "messages": {"from": "inspector", "by": p.name, "text": message, "at": now()}
            },
            "$set": {"status": "pending", "updated_at": now()},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not d:
        await get_own(p, proposal_id)
        raise AppError(
            409, "invalid_state", "Replies are only possible when more information was requested."
        )
    return d


async def list_all(
    admin: Principal, status: str | None, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    ensure_admin(admin)
    flt: dict[str, Any] = {"status": status} if status else {}
    return await paginate("product_proposals", flt, page, page_size, [("created_at", -1)])


async def get_any(admin: Principal, proposal_id: str) -> dict[str, Any]:
    ensure_admin(admin)
    d = await col("product_proposals").find_one({"_id": proposal_id})
    if not d:
        raise not_found("Proposal")
    return d


async def decide(
    admin: Principal,
    proposal_id: str,
    outcome: str,
    note: str,
    reference_id: str | None,
    product: dict[str, Any] | None,
) -> dict[str, Any]:
    ensure_admin(admin)
    before = await get_any(admin, proposal_id)
    if before["status"] in ("approved", "rejected"):
        raise AppError(409, "invalid_state", "This proposal has already been decided.")
    review = {
        "by_uid": admin.uid,
        "by_name": admin.name,
        "outcome": outcome,
        "note": note,
        "at": now(),
    }
    sets: dict[str, Any] = {"status": outcome, "updated_at": now()}
    if reference_id:
        sets["reference_id"] = reference_id
    if product:
        sets["product"] = product
    push: dict[str, Any] = {"reviews": {"$each": [review], "$slice": -50}}
    if outcome == "info_requested" and note:
        push["messages"] = {"from": "admin", "by": admin.name, "text": note, "at": now()}
    d = await col("product_proposals").find_one_and_update(
        {"_id": proposal_id, "status": before["status"]},
        {"$set": sets, "$push": push},
        return_document=ReturnDocument.AFTER,
    )
    if not d:
        raise AppError(409, "conflict", "The proposal changed meanwhile. Reload and try again.")
    await audit.log(
        admin,
        f"proposal.{outcome}",
        "proposal",
        proposal_id,
        f"{outcome.replace('_', ' ').title()}: {before['product'].get('brand', '')} "
        f"{before['product'].get('product_name', '')}",
        {"status": [before["status"], outcome], **({"note": [None, note]} if note else {})},
    )
    return d


async def counts(owner_uid: str | None = None) -> dict[str, int]:
    match: dict[str, Any] = {"owner_uid": owner_uid} if owner_uid else {}
    out = {"pending": 0, "approved": 0, "rejected": 0, "info_requested": 0}
    async for row in await col("product_proposals").aggregate(
        [{"$match": match}, {"$group": {"_id": "$status", "n": {"$sum": 1}}}]
    ):
        out[row["_id"]] = row["n"]
    return out


async def pending_list(limit: int = 6) -> list[dict[str, Any]]:
    cur = (
        col("product_proposals")
        .find({"status": {"$in": ["pending", "info_requested"]}})
        .sort("created_at", 1)
        .limit(limit)
    )
    return [
        {
            "id": d["_id"],
            "product": d["product"].get("product_name"),
            "brand": d["product"].get("brand"),
            "owner_name": d.get("owner_name"),
            "status": d["status"],
            "created_at": d["created_at"],
        }
        async for d in cur
    ]
