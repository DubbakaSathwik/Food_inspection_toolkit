"""Delete expired temporary photo originals and orphan GridFS chunks: `uv run python -m scripts.cleanup`."""

from __future__ import annotations

import asyncio

from app.db import close_client
from app.services.maintenance import cleanup_expired_photos


async def main() -> None:
    print(await cleanup_expired_photos())
    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
