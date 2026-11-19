from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from app.errors import not_found
from app.http import file_response
from app.repositories import files, health
from app.repositories import settings as settings_repo
from app.repositories.settings import IMAGE_KEYS

router = APIRouter(tags=["public"])


@router.get("/health")
@router.head("/health", include_in_schema=False)
async def health_check() -> JSONResponse:
    ok = await health.ping()
    return JSONResponse(
        {"status": "ok" if ok else "degraded", "database": "ok" if ok else "unavailable"},
        status_code=200 if ok else 503,
    )


@router.get("/api/v1/public/site-images")
async def site_images() -> dict[str, Any]:
    cfg = await settings_repo.load()
    return {
        k: (
            {"url": f"/api/v1/public/site-images/{k}?v={v['file_id']}", "alt": v.get("alt", "")}
            if v
            else None
        )
        for k, v in cfg["images"].items()
    }


@router.get("/api/v1/public/site-images/{key}")
async def site_image(key: str) -> StreamingResponse:
    if key not in IMAGE_KEYS:
        raise not_found("Image")
    cfg = await settings_repo.load()
    info = cfg["images"].get(key)
    if not info:
        raise not_found("Image")
    it, meta = await files.stream("siteimages", info["file_id"])
    return file_response(it, meta, cache="public, max-age=86400")
