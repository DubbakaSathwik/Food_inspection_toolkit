"""GridFS buckets (D-03): photos (temporary originals), reports (PDFs), refimages, siteimages.
Ownership is stored in metadata.owner_uid and checked here for user-owned buckets."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from bson import ObjectId
from gridfs.errors import NoFile

from app.db import bucket
from app.errors import not_found
from app.repositories.base import col


def _oid(file_id: str) -> ObjectId:
    if not ObjectId.is_valid(file_id):
        raise not_found("File")
    return ObjectId(file_id)


async def put(
    bucket_name: str, data: bytes, filename: str, content_type: str, metadata: dict[str, Any]
) -> str:
    meta = dict(metadata, content_type=content_type)
    fid = await bucket(bucket_name).upload_from_stream(filename, data, metadata=meta)
    return str(fid)


async def file_info(bucket_name: str, file_id: str) -> dict[str, Any] | None:
    return await col(f"{bucket_name}.files").find_one({"_id": _oid(file_id)})


async def read_bytes(
    bucket_name: str, file_id: str, owner_uid: str | None = None
) -> tuple[bytes, dict[str, Any]]:
    """Read a whole file (used for images and PDFs; sizes are capped at upload)."""
    info = await file_info(bucket_name, file_id)
    if not info:
        raise not_found("File")
    if owner_uid is not None and (info.get("metadata") or {}).get("owner_uid") != owner_uid:
        raise not_found("File")
    try:
        stream = await bucket(bucket_name).open_download_stream(info["_id"])
        data = await stream.read()
    except NoFile as e:
        raise not_found("File") from e
    return data, info


async def stream(
    bucket_name: str, file_id: str, owner_uid: str | None = None
) -> tuple[AsyncIterator[bytes], dict[str, Any]]:
    info = await file_info(bucket_name, file_id)
    if not info:
        raise not_found("File")
    if owner_uid is not None and (info.get("metadata") or {}).get("owner_uid") != owner_uid:
        raise not_found("File")
    gout = await bucket(bucket_name).open_download_stream(info["_id"])

    async def _iter() -> AsyncIterator[bytes]:
        while True:
            chunk = await gout.readchunk()
            if not chunk:
                break
            yield chunk

    return _iter(), info


async def delete(bucket_name: str, file_id: str) -> bool:
    try:
        await bucket(bucket_name).delete(_oid(file_id))
        return True
    except NoFile:
        return False


async def expired_photo_ids(before: datetime, limit: int = 500) -> list[ObjectId]:
    cur = (
        col("photos.files").find({"metadata.expires_at": {"$lt": before}}, {"_id": 1}).limit(limit)
    )
    return [d["_id"] async for d in cur]


async def delete_ids(bucket_name: str, ids: list[ObjectId]) -> int:
    n = 0
    for fid in ids:
        try:
            await bucket(bucket_name).delete(fid)
            n += 1
        except NoFile:
            continue
    return n


async def orphan_chunk_cleanup(bucket_name: str) -> int:
    """Remove chunks whose files document no longer exists (safety net)."""
    files = col(f"{bucket_name}.files")
    chunks = col(f"{bucket_name}.chunks")
    file_ids = set(await chunks.distinct("files_id"))
    if not file_ids:
        return 0
    existing = {d["_id"] async for d in files.find({"_id": {"$in": list(file_ids)}}, {"_id": 1})}
    orphans = list(file_ids - existing)
    if not orphans:
        return 0
    res = await chunks.delete_many({"files_id": {"$in": orphans}})
    return int(res.deleted_count)


async def bucket_stats(bucket_name: str) -> dict[str, float]:
    total, count = 0, 0
    async for row in await col(f"{bucket_name}.files").aggregate(
        [{"$group": {"_id": None, "bytes": {"$sum": "$length"}, "n": {"$sum": 1}}}]
    ):
        total, count = int(row["bytes"]), int(row["n"])
    return {"files": float(count), "mb": round(total / 1_048_576, 2)}


async def db_stats() -> dict[str, float]:
    from app.db import get_db

    s = await get_db().command("dbStats")
    return {
        "data_mb": round(float(s.get("dataSize", 0)) / 1_048_576, 2),
        "storage_mb": round(float(s.get("storageSize", 0)) / 1_048_576, 2),
    }
