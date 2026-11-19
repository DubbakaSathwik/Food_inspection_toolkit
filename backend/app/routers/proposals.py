"""Inspector product proposals (F10)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.auth import require_inspector
from app.errors import AppError
from app.http import WRITE_LIMIT, limiter
from app.models.common import Page
from app.models.proposals import ProposalIn, ProposalOut, ProposalReplyIn
from app.principal import Principal
from app.repositories import inspections as insp_repo
from app.repositories import proposals as repo

router = APIRouter(prefix="/api/v1", tags=["proposals"])
Insp = Annotated[Principal, Depends(require_inspector)]


def to_out(d: dict[str, Any]) -> dict[str, Any]:
    out = dict(d)
    out["id"] = out.pop("_id")
    out["has_report"] = bool(d.get("report_file_id"))
    return out


@router.post("/proposals", response_model=ProposalOut, status_code=201)
@limiter.limit(WRITE_LIMIT)
async def create(request: Request, p: Insp, body: ProposalIn) -> dict[str, Any]:
    insp = await insp_repo.get(p, body.inspection_id)  # ownership check (404 otherwise)
    if insp["status"] != "completed" or not insp.get("report"):
        raise AppError(
            409, "invalid_state", "Generate the inspection report before submitting a proposal."
        )
    product = body.product.model_dump()
    product["fssai_licence"] = "".join(ch for ch in product["fssai_licence"] if ch.isdigit())
    doc = await repo.create(
        p,
        body.inspection_id,
        product,
        body.remarks,
        insp["report"]["file_id"],
        len(insp.get("photos", [])),
    )
    await insp_repo.update(p, body.inspection_id, {"proposal_id": doc["_id"]})
    return to_out(doc)


@router.get("/proposals", response_model=Page[ProposalOut])
async def list_mine(
    p: Insp,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    items, total = await repo.list_own(p, page, page_size)
    return {
        "items": [to_out(d) for d in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/proposals/{proposal_id}", response_model=ProposalOut)
async def get_mine(p: Insp, proposal_id: str) -> dict[str, Any]:
    return to_out(await repo.get_own(p, proposal_id))


@router.post("/proposals/{proposal_id}/reply", response_model=ProposalOut)
async def reply(p: Insp, proposal_id: str, body: ProposalReplyIn) -> dict[str, Any]:
    return to_out(await repo.reply(p, proposal_id, body.message))
