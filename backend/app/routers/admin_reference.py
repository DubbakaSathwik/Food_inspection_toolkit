"""Admin reference database (F13): CRUD, archive, packaging versions/images, AI-assisted entry, import."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from app.auth import require_admin
from app.config import get_settings
from app.errors import AppError
from app.http import read_upload
from app.models.common import Category, OkOut, Page
from app.models.reference import (
    AiDraftOut,
    ImportCommitIn,
    ImportPreviewOut,
    ReferenceIn,
    ReferenceOut,
    ReferencePatch,
)
from app.principal import Principal
from app.repositories import files, reference, usage
from app.repositories import settings as settings_repo
from app.services import images, importer
from app.services.ai import chain
from app.services.ai.prompts import EXTRACTION_PROMPT
from app.services.fields import confidence_level

router = APIRouter(prefix="/api/v1/admin/reference", tags=["admin-reference"])
Admin = Annotated[Principal, Depends(require_admin)]


def to_out(d: dict[str, Any]) -> dict[str, Any]:
    out = dict(d)
    out["id"] = out.pop("_id")
    return out


@router.get("", response_model=Page[ReferenceOut])
async def list_records(
    p: Admin,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Category | None = None,
    status: Literal["active", "archived", "all"] = "active",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    items, total = await reference.list_records(q, category, status, page, page_size)
    return {
        "items": [to_out(d) for d in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stats")
async def stats(p: Admin) -> dict[str, int]:
    return await reference.counts()


@router.post("", response_model=ReferenceOut, status_code=201)
async def create(request: Request, p: Admin, body: ReferenceIn) -> dict[str, Any]:
    return to_out(await reference.create(p, body.model_dump(mode="json")))


@router.get("/{ref_id}", response_model=ReferenceOut)
async def get_one(p: Admin, ref_id: str) -> dict[str, Any]:
    return to_out(await reference.get(ref_id))


@router.patch("/{ref_id}", response_model=ReferenceOut)
async def update(p: Admin, ref_id: str, body: ReferencePatch) -> dict[str, Any]:
    return to_out(
        await reference.update(p, ref_id, body.model_dump(mode="json", exclude_none=True))
    )


@router.post("/{ref_id}/archive", response_model=ReferenceOut)
async def archive(p: Admin, ref_id: str) -> dict[str, Any]:
    return to_out(await reference.set_status(p, ref_id, "archived"))


@router.post("/{ref_id}/restore", response_model=ReferenceOut)
async def restore(p: Admin, ref_id: str) -> dict[str, Any]:
    return to_out(await reference.set_status(p, ref_id, "active"))


@router.delete("/{ref_id}", response_model=OkOut)
async def delete(p: Admin, ref_id: str) -> dict[str, Any]:
    doc = await reference.delete(p, ref_id)
    for v in doc.get("packaging_versions", []):
        for im in v.get("images", []):
            await files.delete("refimages", im["file_id"])
    return {"ok": True}


@router.post("/{ref_id}/versions", response_model=ReferenceOut, status_code=201)
async def add_version(
    p: Admin,
    ref_id: str,
    label: Annotated[str, Form(min_length=1, max_length=80)],
    notes: Annotated[str, Form(max_length=500)] = "",
) -> dict[str, Any]:
    return to_out(await reference.add_version(p, ref_id, label.strip(), notes.strip()))


@router.post("/{ref_id}/versions/{version_id}/images", response_model=ReferenceOut, status_code=201)
async def add_image(
    request: Request,
    p: Admin,
    ref_id: str,
    version_id: str,
    file: Annotated[UploadFile, File()],
    side: Annotated[Literal["front", "back", "side", "closeup", "other"], Form()] = "front",
) -> dict[str, Any]:
    await reference.get(ref_id)
    max_b = get_settings().max_upload_mb * 1_048_576
    data = await read_upload(file, max_b)
    meta = images.inspect_upload(data, max_b)
    fid = await files.put(
        "refimages",
        data,
        f"{ref_id}-{side}.{meta['format'].lower()}",
        meta["content_type"],
        {"reference_id": ref_id, "uploaded_by": p.uid},
    )
    try:
        doc = await reference.add_image(
            p, ref_id, version_id, {"file_id": fid, "side": side, "uploaded_at": None}
        )
    except AppError:
        await files.delete("refimages", fid)
        raise
    return to_out(doc)


@router.delete("/{ref_id}/images/{file_id}", response_model=ReferenceOut)
async def remove_image(p: Admin, ref_id: str, file_id: str) -> dict[str, Any]:
    doc = await reference.remove_image(p, ref_id, file_id)
    await files.delete("refimages", file_id)
    return to_out(doc)


@router.post("/ai-extract", response_model=AiDraftOut)
async def ai_extract(
    request: Request, p: Admin, files_in: Annotated[list[UploadFile], File(alias="files")]
) -> dict[str, Any]:
    """AI-assisted entry: returns a draft only. The admin reviews it and saves explicitly (MVP §2.2-5)."""
    if not 1 <= len(files_in) <= 5:
        raise AppError(400, "bad_request", "Upload 1 to 5 photographs.")
    max_b = get_settings().max_upload_mb * 1_048_576
    imgs = []
    for i, upload in enumerate(files_in, start=1):
        data = await read_upload(upload, max_b)
        meta = images.inspect_upload(data, max_b)
        imgs.append(images.ImageInput(data, meta["content_type"], "", i))
    cfg = await settings_repo.load()
    await usage.consume_ai(p.uid, cfg["limits"]["ai_daily_limit_per_user"])
    res = await chain.run_extract(
        imgs, EXTRACTION_PROMPT, allow_ocr=bool(cfg["ai"].get("ocr_fallback_enabled"))
    )
    if res.data is None:
        raise AppError(
            502,
            "ai_unavailable",
            "AI extraction is unavailable right now. Enter the details manually.",
        )
    f = res.data.get("fields") or {}

    def val(k: str) -> str:
        v = (f.get(k) or {}).get("value")
        return str(v).strip() if v else ""

    draft = {
        "product_name": val("product_name"),
        "brand": val("brand"),
        "variant": val("variant"),
        "category": res.data.get("category") or "",
        "net_quantity": val("net_quantity"),
        "gtin": "".join(ch for ch in val("barcode") if ch.isdigit())[:14],
        "manufacturer": {
            "name": val("manufacturer_name"),
            "registered_address": "",
            "facility_address": val("manufacturer_address"),
            "state": "",
            "district": "",
            "contact": val("customer_care"),
        },
        "licence": {
            "number": "".join(ch for ch in val("fssai_licence") if ch.isdigit()),
            "status": "active",
        },
        "source": "ai_assisted",
    }
    conf = {
        k: confidence_level((v or {}).get("confidence"))
        for k, v in f.items()
        if isinstance(v, dict)
    }
    return {"draft": draft, "confidence": conf, "provider": res.provider or ""}


@router.post("/import/preview", response_model=ImportPreviewOut)
async def import_preview(p: Admin, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    data = await read_upload(file, 5 * 1_048_576)
    return importer.preview(file.filename or "", data)


@router.post("/import/commit")
async def import_commit(request: Request, p: Admin, body: ImportCommitIn) -> dict[str, Any]:
    ids = await reference.create_many(p, [r.model_dump(mode="json") for r in body.rows])
    return {"created": len(ids), "ids": ids}
