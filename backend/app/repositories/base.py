"""Shared helpers for the data-access layer. Routers never import `app.db`; they call repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from app.db import get_db
from app.errors import forbidden
from app.principal import Principal


def now() -> datetime:
    return datetime.now(UTC)


def col(name: str) -> AsyncCollection[dict[str, Any]]:
    return get_db()[name]


async def paginate(
    collection: str,
    flt: dict[str, Any],
    page: int,
    page_size: int,
    sort: list[tuple[str, int]],
    projection: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    c = col(collection)
    total = await c.count_documents(flt)
    # Tiebreaker: equal timestamps must not reorder or repeat items across pages.
    if all(k != "_id" for k, _ in sort):
        sort = [*sort, ("_id", sort[-1][1] if sort else -1)]
    cur = c.find(flt, projection).sort(sort).skip((page - 1) * page_size).limit(page_size)
    return [d async for d in cur], total


async def next_sequence(name: str, year: int) -> int:
    doc = await col("counters").find_one_and_update(
        {"_id": f"{name}-{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    assert doc is not None
    return int(doc["seq"])


def ensure_admin(p: Principal) -> None:
    """Defence in depth: repository admin paths re-check the role (not an assert; survives -O)."""
    if not p.is_admin:
        raise forbidden("Administrator access required.")
