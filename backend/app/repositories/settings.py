"""Singleton platform settings (`settings` collection, _id = "global")."""

from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from app.config import get_settings
from app.models.admin import SettingsAi, SettingsGeneral, SettingsLimits
from app.principal import Principal
from app.repositories import audit
from app.repositories.base import col, ensure_admin, now

IMAGE_KEYS = ("hero", "signin", "banner")


def defaults() -> dict[str, Any]:
    env = get_settings()
    return {
        "_id": "global",
        "general": SettingsGeneral().model_dump(),
        "ai": SettingsAi().model_dump(),
        "limits": SettingsLimits(
            ai_daily_limit_per_user=env.ai_daily_limit_per_user,
            photo_retention_days=env.photo_retention_days,
        ).model_dump(),
        "images": dict.fromkeys(IMAGE_KEYS),
        "updated_at": None,
        "updated_by_name": None,
    }


async def load() -> dict[str, Any]:
    doc = await col("settings").find_one({"_id": "global"})
    base = defaults()
    if not doc:
        return base
    for k in ("general", "ai", "limits", "images"):
        base[k] = {**base[k], **(doc.get(k) or {})}
    base["updated_at"] = doc.get("updated_at")
    base["updated_by_name"] = doc.get("updated_by_name")
    return base


async def patch(admin: Principal, changes: dict[str, Any]) -> dict[str, Any]:
    ensure_admin(admin)
    before = await load()
    sets: dict[str, Any] = {"updated_at": now(), "updated_by_name": admin.name}
    diff: dict[str, Any] = {}
    for section, values in changes.items():
        if values is None:
            continue
        for k, v in values.items():
            if before[section].get(k) != v:
                diff[f"{section}.{k}"] = [before[section].get(k), v]
            sets[f"{section}.{k}"] = v
    await col("settings").update_one({"_id": "global"}, {"$set": sets}, upsert=True)
    if diff:
        await audit.log(
            admin, "settings.update", "settings", "global", "Updated platform settings", diff
        )
    return await load()


async def set_image(
    admin: Principal, key: str, info: dict[str, Any] | None
) -> tuple[dict[str, Any], str | None]:
    """Returns (settings, previous file id) so the caller can delete the old file."""
    ensure_admin(admin)
    before = await load()
    prev = (before["images"].get(key) or {}).get("file_id")
    doc = await col("settings").find_one_and_update(
        {"_id": "global"},
        {"$set": {f"images.{key}": info, "updated_at": now(), "updated_by_name": admin.name}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    assert doc is not None
    await audit.log(
        admin,
        "settings.image_" + ("upload" if info else "reset"),
        "settings",
        key,
        f"{'Uploaded' if info else 'Reset'} website image '{key}'",
    )
    return await load(), prev
