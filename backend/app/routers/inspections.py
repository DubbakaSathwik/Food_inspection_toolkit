"""Inspector workflow API (F02–F09)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Path, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.auth import current_principal, require_inspector
from app.config import get_settings
from app.errors import not_found
from app.http import (
    AI_LIMIT,
    WRITE_LIMIT,
    csv_response,
    file_response,
    limiter,
    read_upload,
    xlsx_response,
)
from app.models.common import Category, Classification, OkOut, Page
from app.models.inspections import (
    CategoryIn,
    ConfirmFieldsIn,
    DashboardOut,
    DecisionIn,
    FieldUpdate,
    FindingDecisionIn,
    InspectionOut,
    InspectionStatus,
    InspectionSummary,
    NoteIn,
    NoteOut,
    PhotoLabel,
    PhotoUpdate,
    ReportIn,
)
from app.principal import Principal
from app.repositories import files, reference
from app.repositories import inspections as repo
from app.repositories import settings as settings_repo
from app.services import images, maintenance, workflow
from app.services.fields import CATEGORIES

router = APIRouter(prefix="/api/v1", tags=["inspections"])
Insp = Annotated[Principal, Depends(require_inspector)]
ID = r"^CS-\d{4}-\d{4,6}$"


async def _full(p: Principal, doc: dict[str, Any]) -> dict[str, Any]:
    notes = await repo.list_notes(p, doc["_id"])
    return workflow.to_out(doc, notes)


@router.get("/inspector/dashboard", response_model=DashboardOut)
async def dashboard(p: Insp) -> dict[str, Any]:
    d = await repo.dashboard(p)
    d["continue_items"] = [workflow.to_summary(x) for x in d["continue_items"]]
    d["recent"] = [workflow.to_summary(x) for x in d["recent"]]
    return d


@router.post("/inspections", response_model=InspectionOut, status_code=201)
@limiter.limit(WRITE_LIMIT)
async def create(request: Request, p: Insp) -> dict[str, Any]:
    await maintenance.maybe_cleanup()
    cfg = await settings_repo.load()
    doc = await repo.create(p, cfg["limits"]["photo_retention_days"])
    return workflow.to_out(doc)


@router.get("/inspections", response_model=Page[InspectionSummary])
async def list_inspections(
    p: Insp,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Category | None = None,
    classification: Classification | None = None,
    status: InspectionStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    query = {
        "q": q,
        "category": category,
        "classification": classification,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
        "page": page,
        "page_size": page_size,
    }
    items, total = await repo.list_owned(p, query)
    return {
        "items": [workflow.to_summary(d) for d in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/inspections/export")
async def export(
    p: Insp,
    format: Literal["csv", "xlsx"] = "csv",
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Category | None = None,
    classification: Classification | None = None,
    status: InspectionStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    docs = await repo.export_owned(
        p,
        {
            "q": q,
            "category": category,
            "classification": classification,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
        },
    )
    header = [
        "Inspection ID",
        "Date",
        "Product",
        "Brand",
        "Category",
        "Status",
        "Classification",
        "Remarks",
    ]
    rows = [
        [
            d["_id"],
            d["created_at"].strftime("%Y-%m-%d %H:%M"),
            (d.get("summary") or {}).get("product_name") or "",
            (d.get("summary") or {}).get("brand") or "",
            CATEGORIES.get(d.get("category") or "", ""),
            d["status"],
            (d.get("decision") or {}).get("classification") or "",
            (d.get("decision") or {}).get("remarks") or "",
        ]
        for d in docs
    ]
    if format == "xlsx":
        return xlsx_response(rows, header, "inspection-history.xlsx")
    return csv_response(rows, header, "inspection-history.csv")


@router.get("/inspections/{inspection_id}", response_model=InspectionOut)
async def get_one(p: Insp, inspection_id: Annotated[str, Path(pattern=ID)]) -> dict[str, Any]:
    return await _full(p, await repo.get(p, inspection_id))


@router.delete("/inspections/{inspection_id}", response_model=OkOut)
async def delete(p: Insp, inspection_id: str) -> dict[str, Any]:
    doc = await repo.delete_draft(p, inspection_id)
    for ph in doc.get("photos", []):
        await files.delete("photos", ph["id"])
    return {"ok": True}


# ---------------------------------------------------------------- photos


@router.post("/inspections/{inspection_id}/photos", response_model=InspectionOut, status_code=201)
@limiter.limit(WRITE_LIMIT)
async def upload_photo(
    request: Request,
    p: Insp,
    inspection_id: str,
    file: Annotated[UploadFile, File()],
    label: Annotated[PhotoLabel, Form()] = "other",
) -> dict[str, Any]:
    data = await read_upload(file, get_settings().max_upload_mb * 1_048_576)
    doc = await workflow.upload_photo(p, inspection_id, data, file.filename or "", label)
    return await _full(p, doc)


@router.get("/inspections/{inspection_id}/photos/{photo_id}")
async def get_photo(p: Insp, inspection_id: str, photo_id: str, thumb: bool = False) -> Response:
    insp = await repo.get(p, inspection_id)
    if not any(ph["id"] == photo_id for ph in insp.get("photos", [])) or insp.get("photos_deleted"):
        raise not_found("Photo")
    if thumb:
        data, info = await files.read_bytes("photos", photo_id, owner_uid=p.uid)
        return Response(
            images.thumbnail(data),
            media_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=600"},
        )
    it, info = await files.stream("photos", photo_id, owner_uid=p.uid)
    return file_response(it, info, cache="private, max-age=600")


@router.patch("/inspections/{inspection_id}/photos/{photo_id}", response_model=InspectionOut)
async def update_photo(
    p: Insp, inspection_id: str, photo_id: str, body: PhotoUpdate
) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if body.label:
        changes["label"] = body.label
    if body.clear_crop:
        changes["crop"] = None
    elif body.crop:
        changes["crop"] = body.crop.model_dump()
    doc = (
        await repo.update_photo(p, inspection_id, photo_id, changes)
        if changes
        else await repo.get(p, inspection_id)
    )
    return await _full(p, doc)


@router.delete("/inspections/{inspection_id}/photos/{photo_id}", response_model=InspectionOut)
async def delete_photo(p: Insp, inspection_id: str, photo_id: str) -> dict[str, Any]:
    return await _full(p, await workflow.delete_photo(p, inspection_id, photo_id))


# ---------------------------------------------------------------- extraction and review


@router.post("/inspections/{inspection_id}/extract", response_model=InspectionOut)
@limiter.limit(AI_LIMIT)
async def extract(request: Request, p: Insp, inspection_id: str) -> dict[str, Any]:
    return await _full(p, await workflow.extract(p, inspection_id))


@router.patch("/inspections/{inspection_id}/fields/{key}", response_model=InspectionOut)
async def update_field(p: Insp, inspection_id: str, key: str, body: FieldUpdate) -> dict[str, Any]:
    return await _full(
        p, await workflow.update_field(p, inspection_id, key, body.value, body.confirm)
    )


@router.post("/inspections/{inspection_id}/fields/confirm", response_model=InspectionOut)
async def confirm_fields(p: Insp, inspection_id: str, body: ConfirmFieldsIn) -> dict[str, Any]:
    return await _full(p, await workflow.confirm_fields(p, inspection_id, body.keys))


@router.put("/inspections/{inspection_id}/category", response_model=InspectionOut)
async def set_category(p: Insp, inspection_id: str, body: CategoryIn) -> dict[str, Any]:
    return await _full(p, await workflow.set_category(p, inspection_id, body.category))


@router.post("/inspections/{inspection_id}/analyze", response_model=InspectionOut)
@limiter.limit(AI_LIMIT)
async def analyze(request: Request, p: Insp, inspection_id: str) -> dict[str, Any]:
    return await _full(p, await workflow.analyse(p, inspection_id))


@router.patch("/inspections/{inspection_id}/findings/{finding_id}", response_model=InspectionOut)
async def decide_finding(
    p: Insp, inspection_id: str, finding_id: str, body: FindingDecisionIn
) -> dict[str, Any]:
    return await _full(
        p, await workflow.decide_finding(p, inspection_id, finding_id, body.model_dump())
    )


@router.put("/inspections/{inspection_id}/decision", response_model=InspectionOut)
async def set_decision(p: Insp, inspection_id: str, body: DecisionIn) -> dict[str, Any]:
    return await _full(
        p, await workflow.set_decision(p, inspection_id, body.classification, body.remarks)
    )


@router.post("/inspections/{inspection_id}/report", response_model=InspectionOut)
@limiter.limit(WRITE_LIMIT)
async def generate_report(
    request: Request, p: Insp, inspection_id: str, body: ReportIn
) -> dict[str, Any]:
    return await _full(p, await workflow.generate_report(p, inspection_id, body.signature_name))


@router.get("/inspections/{inspection_id}/report.pdf")
async def report_pdf(p: Insp, inspection_id: str, download: bool = False) -> StreamingResponse:
    insp = await repo.get(p, inspection_id)
    rep = insp.get("report")
    if not rep:
        raise not_found("Report")
    it, info = await files.stream("reports", rep["file_id"], owner_uid=p.uid)
    return file_response(
        it, info, filename=f"{inspection_id}.pdf", inline=not download, cache="private, no-store"
    )


@router.post("/inspections/{inspection_id}/notes", response_model=NoteOut, status_code=201)
async def add_note(p: Insp, inspection_id: str, body: NoteIn) -> dict[str, Any]:
    n = await repo.add_note(p, inspection_id, body.text)
    return {"id": str(n["_id"]), "text": n["text"], "created_at": n["created_at"]}


# ---------------------------------------------------------------- reference data visible to inspectors


@router.get("/reference-images/{file_id}")
async def reference_image(
    file_id: str, p: Principal = Depends(current_principal)
) -> StreamingResponse:
    if not await reference.is_reference_image(file_id):
        raise not_found("Image")
    it, info = await files.stream("refimages", file_id)
    return file_response(it, info, cache="private, max-age=3600")
