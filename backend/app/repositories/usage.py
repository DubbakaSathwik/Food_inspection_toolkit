"""Per-user daily AI quota (NFR-04) stored in `usage_metrics`."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.errors import AppError
from app.repositories.base import col, now


def _today() -> str:
    return now().strftime("%Y-%m-%d")


async def consume_ai(uid: str, limit: int, n: int = 1) -> int:
    """Atomically count an AI call; raises 429 when the daily limit is reached."""
    day = _today()
    await col("usage_metrics").update_one(
        {"uid": uid, "day": day}, {"$setOnInsert": {"ai_calls": 0, "active": True}}, upsert=True
    )
    doc = await col("usage_metrics").find_one_and_update(
        {"uid": uid, "day": day, "ai_calls": {"$lte": limit - n}},
        {"$inc": {"ai_calls": n}},
        return_document=True,
    )
    if doc is None:
        raise AppError(
            429,
            "ai_quota_exceeded",
            f"You have reached today's AI limit ({limit} requests). Try again tomorrow.",
        )
    return int(doc["ai_calls"])


async def calls_today() -> int:
    total = 0
    async for row in await col("usage_metrics").aggregate(
        [{"$match": {"day": _today()}}, {"$group": {"_id": None, "n": {"$sum": "$ai_calls"}}}]
    ):
        total = int(row["n"])
    return total


async def calls_summary() -> dict[str, int]:
    since = (now() - timedelta(days=7)).strftime("%Y-%m-%d")
    week = 0
    async for row in await col("usage_metrics").aggregate(
        [{"$match": {"day": {"$gt": since}}}, {"$group": {"_id": None, "n": {"$sum": "$ai_calls"}}}]
    ):
        week = int(row["n"])
    return {"today": await calls_today(), "last_7_days": week}


async def user_today(uid: str) -> dict[str, Any] | None:
    return await col("usage_metrics").find_one({"uid": uid, "day": _today()})
