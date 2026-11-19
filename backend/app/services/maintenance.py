"""Retention cleanup of temporary photo originals (D-04) and storage statistics (NFR-07)."""

from __future__ import annotations

import logging
from typing import Any

from app.repositories import files
from app.repositories import inspections as insp_repo
from app.repositories.base import now

log = logging.getLogger("crate_scan.maintenance")
STORAGE_LIMIT_MB = 512.0
_last_run: dict[str, float] = {}


async def cleanup_expired_photos() -> dict[str, int]:
    ids = await files.expired_photo_ids(now())
    deleted = await files.delete_ids("photos", ids)
    await insp_repo.mark_expired_photos_deleted(ids)
    orphans = 0
    for b in ("photos", "reports", "refimages", "siteimages"):
        orphans += await files.orphan_chunk_cleanup(b)
    if deleted or orphans:
        log.info("cleanup: %d expired photos, %d orphan chunks", deleted, orphans)
    return {"expired_photos_deleted": deleted, "orphan_chunks_deleted": orphans}


async def maybe_cleanup() -> None:
    """Opportunistic cleanup (Render free has no cron): at most once per hour per process."""
    import time

    t = time.monotonic()
    if t - _last_run.get("cleanup", -1e9) < 3600:
        return
    _last_run["cleanup"] = t
    try:
        await cleanup_expired_photos()
    except Exception:  # never break a user request because of cleanup
        log.exception("cleanup failed")


async def storage() -> dict[str, Any]:
    stats = await files.db_stats()
    buckets = {
        b: await files.bucket_stats(b) for b in ("photos", "reports", "refimages", "siteimages")
    }
    expired = len(await files.expired_photo_ids(now(), limit=10_000))
    return {
        **stats,
        "limit_mb": STORAGE_LIMIT_MB,
        "buckets": buckets,
        "temporary_photos_expired": expired,
    }
