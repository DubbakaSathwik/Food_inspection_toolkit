"""One general Ask-AI history per inspector (owner-scoped)."""

from __future__ import annotations

from typing import Any

from app.principal import Principal
from app.repositories.base import col, now, paginate


def to_out(d: dict[str, Any]) -> dict[str, Any]:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


async def add(
    p: Principal,
    role: str,
    text: str,
    web: bool,
    inspection_id: str | None,
    sources: list[dict[str, str]] | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    doc = {
        "owner_uid": p.uid,
        "role": role,
        "text": text,
        "web": web,
        "inspection_id": inspection_id,
        "sources": sources or [],
        "provider": provider,
        "created_at": now(),
    }
    res = await col("chat_messages").insert_one(doc)
    doc["_id"] = res.inserted_id
    return to_out(doc)


async def history(p: Principal, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    items, total = await paginate(
        "chat_messages", {"owner_uid": p.uid}, page, page_size, [("created_at", -1)]
    )
    return [to_out(d) for d in reversed(items)], total


async def recent(p: Principal, limit: int = 10) -> list[dict[str, Any]]:
    cur = col("chat_messages").find({"owner_uid": p.uid}).sort("created_at", -1).limit(limit)
    return list(reversed([d async for d in cur]))


async def clear(p: Principal) -> int:
    res = await col("chat_messages").delete_many({"owner_uid": p.uid})
    return int(res.deleted_count)
