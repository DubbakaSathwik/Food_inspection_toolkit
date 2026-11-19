"""MongoDB client lifecycle. Only `app.repositories` and migrations may import this module."""

from __future__ import annotations

from typing import Any

from gridfs import AsyncGridFSBucket
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.config import get_settings

BUCKETS = ("photos", "reports", "refimages", "siteimages")

_client: AsyncMongoClient[dict[str, Any]] | None = None


def get_client() -> AsyncMongoClient[dict[str, Any]]:
    global _client
    if _client is None:
        s = get_settings()
        _client = AsyncMongoClient(
            s.mongodb_uri,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            tz_aware=True,
            appname="crate-scan",
        )
    return _client


def get_db() -> AsyncDatabase[dict[str, Any]]:
    return get_client()[get_settings().mongodb_db_name]


def bucket(name: str) -> AsyncGridFSBucket:
    if name not in BUCKETS:
        raise ValueError(f"unknown bucket {name}")
    return AsyncGridFSBucket(get_db(), bucket_name=name)


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
