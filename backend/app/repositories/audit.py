"""Append-only audit log. There is intentionally no update or delete function."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from app.principal import Principal
from app.repositories.base import col, ensure_admin, now, paginate, rx_escape


def _scrub(changes: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in changes.items():
        if isinstance(v, str) and len(v) > 300:
            v = v[:300] + "…"
        out[k] = v
    return out


async def log(
    actor: Principal,
    action: str,
    target_type: str,
    target_id: str,
    summary: str = "",
    changes: dict[str, Any] | None = None,
) -> None:
    await col("audit_logs").insert_one(
        {
            "actor_uid": actor.uid,
            "actor_name": actor.name or actor.email,
            "actor_role": actor.role,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "summary": summary[:300],
            "changes": _scrub(changes or {}),
            "at": now(),
        }
    )


def _filter(
    q: str | None, action: str | None, date_from: datetime | None, date_to: datetime | None
) -> dict[str, Any]:
    flt: dict[str, Any] = {}
    if q:
        rx = {"$regex": rx_escape(q), "$options": "i"}
        flt["$or"] = [{"actor_name": rx}, {"target_id": rx}, {"summary": rx}]
    if action:
        flt["action"] = {"$regex": "^" + rx_escape(action)}
    if date_from or date_to:
        rng: dict[str, Any] = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        flt["at"] = rng
    return flt


def to_out(d: dict[str, Any]) -> dict[str, Any]:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


async def list_logs(
    admin: Principal,
    q: str | None,
    action: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    ensure_admin(admin)
    items, total = await paginate(
        "audit_logs", _filter(q, action, date_from, date_to), page, page_size, [("at", -1)]
    )
    return [to_out(d) for d in items], total


async def export_logs(
    admin: Principal,
    q: str | None,
    action: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    ensure_admin(admin)
    cur = col("audit_logs").find(_filter(q, action, date_from, date_to)).sort("at", -1).limit(limit)
    return [to_out(d) async for d in cur]


async def recent(limit: int = 8) -> list[dict[str, Any]]:
    cur = col("audit_logs").find({}).sort("at", -1).limit(limit)
    return [to_out(d) async for d in cur]


async def actions_for_target(target_id: str, limit: int = 20) -> list[dict[str, Any]]:
    cur = col("audit_logs").find({"target_id": target_id}).sort("at", -1).limit(limit)
    return [to_out(d) async for d in cur]


def oid(s: str) -> ObjectId | None:
    return ObjectId(s) if ObjectId.is_valid(s) else None
