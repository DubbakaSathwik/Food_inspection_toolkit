"""Apply pending migrations: `uv run python -m scripts.migrate [--dry-run]`."""

from __future__ import annotations

import argparse
import asyncio

from app.config import get_settings
from app.db import close_client, get_db
from migrations.runner import run


async def main(dry_run: bool) -> None:
    s = get_settings()
    print(f"Database: {s.mongodb_db_name} (env: {s.app_env})")
    done = await run(get_db(), dry_run=dry_run)
    print(("Pending: " if dry_run else "Applied: ") + (", ".join(done) if done else "nothing"))
    await close_client()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    asyncio.run(main(ap.parse_args().dry_run))
