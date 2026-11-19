"""Ordered, idempotent migrations. Applied migrations are recorded in `_migrations`.

Run: `uv run python -m scripts.migrate` (add `--dry-run` to list pending migrations only).
Never run automatically on application start (Render rule)."""

from __future__ import annotations

import importlib
import pkgutil
from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

import migrations


def discover() -> list[Any]:
    mods = []
    for info in sorted(pkgutil.iter_modules(migrations.__path__), key=lambda m: m.name):
        if info.name.startswith("m") and info.name[1:5].isdigit():
            mods.append(importlib.import_module(f"migrations.{info.name}"))
    return mods


async def run(db: AsyncDatabase, dry_run: bool = False) -> list[str]:  # type: ignore[type-arg]
    applied = {d["_id"] async for d in db["_migrations"].find({}, {"_id": 1})}
    done: list[str] = []
    for mod in discover():
        name = mod.__name__.rsplit(".", 1)[-1]
        if name in applied and not getattr(mod, "ALWAYS_RERUN", False):
            continue
        done.append(name)
        if dry_run:
            continue
        await mod.up(db)
        await db["_migrations"].update_one(
            {"_id": name},
            {
                "$set": {
                    "applied_at": datetime.now(UTC),
                    "description": (mod.__doc__ or "").strip()[:200],
                }
            },
            upsert=True,
        )
    return done
