"""Combined demo reference records (product + manufacturer + licence + packaging versions)."""

from __future__ import annotations

import re
import secrets
from typing import Any

from pymongo import ReturnDocument

from app.errors import AppError, forbidden, not_found
from app.principal import Principal
from app.repositories import audit
from app.repositories.base import col, ensure_admin, next_sequence, now, paginate


async def _new_id() -> str:
    seq = await next_sequence("reference", 0)
    return f"REF-{seq:04d}"


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def _dates_to_str(data: dict[str, Any]) -> dict[str, Any]:
    lic = data.get("licence")
    if isinstance(lic, dict):
        for k in ("valid_from", "valid_until"):
            if lic.get(k) is not None and not isinstance(lic[k], str):
                lic[k] = lic[k].isoformat()
    return data


async def create(
    admin: Principal, data: dict[str, Any], source: str | None = None
) -> dict[str, Any]:
    ensure_admin(admin)
    data = _dates_to_str(dict(data))
    doc = {
        "_id": await _new_id(),
        **data,
        "source": source or data.get("source", "manual"),
        "status": "active",
        "demo": True,
        "packaging_versions": [],
        "created_by": admin.uid,
        "created_at": now(),
        "updated_at": now(),
    }
    await col("reference_records").insert_one(doc)
    await audit.log(
        admin,
        "reference.create",
        "reference",
        doc["_id"],
        f"Added {doc['brand']} {doc['product_name']}",
        {"source": [None, doc["source"]]},
    )
    return doc


async def create_many(admin: Principal, rows: list[dict[str, Any]]) -> list[str]:
    ensure_admin(admin)
    ids: list[str] = []
    for r in rows:
        r = _dates_to_str(dict(r))
        doc = {
            "_id": await _new_id(),
            **r,
            "source": "import",
            "status": "active",
            "demo": True,
            "packaging_versions": [],
            "created_by": admin.uid,
            "created_at": now(),
            "updated_at": now(),
        }
        await col("reference_records").insert_one(doc)
        ids.append(doc["_id"])
    await audit.log(
        admin,
        "reference.import",
        "reference",
        ids[0] if ids else "-",
        f"Imported {len(ids)} reference records",
        {"count": [0, len(ids)]},
    )
    return ids


async def get(ref_id: str) -> dict[str, Any]:
    """Readable by any active user (inspectors see reference data in findings)."""
    doc = await col("reference_records").find_one({"_id": ref_id})
    if not doc:
        raise not_found("Reference record")
    return doc


async def update(admin: Principal, ref_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    ensure_admin(admin)
    before = await get(ref_id)
    changes = _dates_to_str({k: v for k, v in changes.items() if v is not None})
    if not changes:
        return before
    sets = dict(changes, updated_at=now())
    doc = await col("reference_records").find_one_and_update(
        {"_id": ref_id}, {"$set": sets}, return_document=ReturnDocument.AFTER
    )
    assert doc is not None
    flat_b, flat_a = _flatten(before), _flatten(doc)
    diff = {
        k: [flat_b.get(k), v]
        for k, v in flat_a.items()
        if k not in ("updated_at",)
        and not k.startswith("packaging_versions")
        and flat_b.get(k) != v
    }
    action = (
        "reference.licence_change"
        if any(k.startswith("licence.") for k in diff)
        else (
            "reference.manufacturer_change"
            if any(k.startswith("manufacturer.") for k in diff)
            else "reference.update"
        )
    )
    await audit.log(
        admin, action, "reference", ref_id, f"Edited {doc['brand']} {doc['product_name']}", diff
    )
    return doc


async def set_status(admin: Principal, ref_id: str, status: str) -> dict[str, Any]:
    ensure_admin(admin)
    before = await get(ref_id)
    doc = await col("reference_records").find_one_and_update(
        {"_id": ref_id},
        {"$set": {"status": status, "updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    assert doc is not None
    await audit.log(
        admin,
        f"reference.{'archive' if status == 'archived' else 'restore'}",
        "reference",
        ref_id,
        f"{status.title()} {doc['brand']} {doc['product_name']}",
        {"status": [before.get("status"), status]},
    )
    return doc


async def delete(admin: Principal, ref_id: str) -> dict[str, Any]:
    if not admin.is_super_admin:
        raise forbidden(
            "Only a Super Admin can permanently delete reference records. Archive it instead."
        )
    doc = await col("reference_records").find_one_and_delete({"_id": ref_id})
    if not doc:
        raise not_found("Reference record")
    await audit.log(
        admin,
        "reference.delete",
        "reference",
        ref_id,
        f"Deleted {doc['brand']} {doc['product_name']}",
    )
    return doc


def _filter(q: str | None, category: str | None, status: str) -> dict[str, Any]:
    flt: dict[str, Any] = {}
    if status != "all":
        flt["status"] = status
    if category:
        flt["category"] = category
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        flt["$or"] = [
            {"product_name": rx},
            {"brand": rx},
            {"_id": rx},
            {"manufacturer.name": rx},
            {"licence.number": rx},
            {"gtin": rx},
        ]
    return flt


async def list_records(
    q: str | None, category: str | None, status: str, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    return await paginate(
        "reference_records", _filter(q, category, status), page, page_size, [("updated_at", -1)]
    )


async def counts() -> dict[str, int]:
    c = col("reference_records")
    return {
        "active": await c.count_documents({"status": "active"}),
        "archived": await c.count_documents({"status": "archived"}),
        "with_images": await c.count_documents(
            {"status": "active", "packaging_versions.images.0": {"$exists": True}}
        ),
    }


async def candidates(
    brand: str | None, name: str | None, licence: str | None, gtin: str | None, limit: int = 30
) -> list[dict[str, Any]]:
    """Active records that might match a scanned product (scored later by the matcher)."""
    ors: list[dict[str, Any]] = []
    if licence:
        ors.append({"licence.number": licence})
    if gtin:
        ors.append({"gtin": gtin})
    for text in (brand, name):
        if text:
            words = [w for w in re.findall(r"[A-Za-z0-9]{3,}", text)][:4]
            for w in words:
                ors.append({"brand": {"$regex": re.escape(w), "$options": "i"}})
                ors.append({"product_name": {"$regex": re.escape(w), "$options": "i"}})
    if not ors:
        return []
    cur = col("reference_records").find({"status": "active", "$or": ors}).limit(limit)
    return [d async for d in cur]


async def by_licence(number: str) -> list[dict[str, Any]]:
    cur = col("reference_records").find({"licence.number": number}).limit(10)
    return [d async for d in cur]


# ---------------------------------------------------------------- packaging versions / images


async def add_version(admin: Principal, ref_id: str, label: str, notes: str) -> dict[str, Any]:
    ensure_admin(admin)
    version = {
        "id": secrets.token_hex(6),
        "label": label,
        "notes": notes,
        "images": [],
        "created_at": now(),
    }
    doc = await col("reference_records").find_one_and_update(
        {"_id": ref_id, "packaging_versions.19": {"$exists": False}},
        {"$push": {"packaging_versions": version}, "$set": {"updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        await get(ref_id)
        raise AppError(409, "conflict", "A record can have up to 20 packaging versions.")
    await audit.log(
        admin, "reference.version_add", "reference", ref_id, f"Added packaging version '{label}'"
    )
    return doc


async def add_image(
    admin: Principal, ref_id: str, version_id: str, image: dict[str, Any]
) -> dict[str, Any]:
    ensure_admin(admin)
    image = {**image, "uploaded_at": now()}
    doc = await col("reference_records").find_one_and_update(
        {
            "_id": ref_id,
            "packaging_versions": {
                "$elemMatch": {"id": version_id, "images.7": {"$exists": False}}
            },
        },
        {"$push": {"packaging_versions.$.images": image}, "$set": {"updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        await get(ref_id)
        raise AppError(409, "conflict", "Version not found or it already has 8 photographs.")
    await audit.log(
        admin, "reference.image_add", "reference", ref_id, "Uploaded reference packaging photo"
    )
    return doc


async def remove_image(admin: Principal, ref_id: str, file_id: str) -> dict[str, Any]:
    ensure_admin(admin)
    doc = await col("reference_records").find_one_and_update(
        {"_id": ref_id, "packaging_versions.images.file_id": file_id},
        {
            "$pull": {"packaging_versions.$[].images": {"file_id": file_id}},
            "$set": {"updated_at": now()},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise not_found("Image")
    await audit.log(
        admin, "reference.image_remove", "reference", ref_id, "Removed reference packaging photo"
    )
    return doc


async def is_reference_image(file_id: str) -> bool:
    return (
        await col("reference_records").count_documents(
            {"packaging_versions.images.file_id": file_id}, limit=1
        )
        > 0
    )
