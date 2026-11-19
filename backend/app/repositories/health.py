from __future__ import annotations

import asyncio

from app.db import get_client


async def ping() -> bool:
    try:
        await asyncio.wait_for(get_client().admin.command("ping"), timeout=4)
        return True
    except Exception:
        return False
