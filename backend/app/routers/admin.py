"""Admin portal API: dashboard, rules, proposals, users, analytics, audit, settings, storage (F11–F18)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.auth import require_admin, revoke_tokens, set_claims
from app.config import get_settings
from app.errors import AppError, not_found
from app.http import csv_response, file_response, read_upload
from app.models.admin import (
    AdminDashboardOut,
    AnalyticsOut,
    AuditOut,
    DiagnosticInfo,
    DiagnosticOut,
    RuleIn,
    RuleOut,
    RulePatch,
    RulesStatsOut,
    SettingsOut,
    SettingsPatch,
    StorageOut,
)
from app.models.common import Category, OkOut, Page
from app.models.proposals import ProposalDecisionIn, ProposalOut
from app.models.reference import ReferenceIn
from app.models.users import (
    ApproveIn,
    InviteIn,
    InviteOut,
    UserAdminOut,
    UserDetailOut,
    UserPatchIn,
)
from app.principal import Principal
from app.repositories import audit, files, proposals, reference, rules, usage, users
from app.repositories import inspections as insp_repo
from app.repositories import settings as settings_repo
from app.repositories.settings import IMAGE_KEYS
from app.routers.proposals import to_out as proposal_out
from app.services import diagnostics, images, maintenance
from app.services.ai import chain, ocr

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
Admin = Annotated[Principal, Depends(require_admin)]


# ---------------------------------------------------------------- dashboard


@router.get("/dashboard", response_model=AdminDashboardOut)
async def dashboard(p: Admin) -> dict[str, Any]:
    uc = await users.counts()
    act = await users.active_counts()
    st = await insp_repo.stats(p, datetime.now().astimezone() - timedelta(days=7))
    refc = await reference.counts()
    return {
        "users_total": uc.get("total", 0),
        "inspectors": uc.get("role_inspector", 0),
        "pending_approvals": uc.get("status_pending", 0),
        **act,
        "inspections_total": st["total"],
        "inspections_week": st["since"],
        "reference_products": refc["active"],
        "proposals": await proposals.counts(),
        "pending_users": await users.pending_list(),
        "pending_proposals": await proposals.pending_list(),
        "recent_activity": await audit.recent(8),
    }


# ---------------------------------------------------------------- compliance rules


@router.get("/rules", response_model=Page[RuleOut])
async def list_rules(
    p: Admin,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Literal["beverages", "snacks", "dairy", "staples", "all"] | None = None,
    status: Literal["active", "draft", "archived"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:
    items, total = await rules.list_rules(p, q, category, status, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/rules/stats", response_model=RulesStatsOut)
async def rules_stats(p: Admin) -> dict[str, Any]:
    return await rules.stats()


@router.get("/rules/{rule_id}", response_model=RuleOut)
async def get_rule(p: Admin, rule_id: str) -> dict[str, Any]:
    return await rules.get(p, rule_id)


@router.post("/rules", response_model=RuleOut, status_code=201)
async def create_rule(request: Request, p: Admin, body: RuleIn) -> dict[str, Any]:
    return await rules.create(p, body.model_dump())


@router.patch("/rules/{rule_id}", response_model=RuleOut)
async def update_rule(p: Admin, rule_id: str, body: RulePatch) -> dict[str, Any]:
    data = body.model_dump(exclude={"change_note"}, exclude_none=True)
    current = await rules.get(p, rule_id)
    merged = {
        **{
            k: current.get(k)
            for k in (
                "code",
                "title",
                "category",
                "check_type",
                "field",
                "pattern",
                "keywords",
                "severity",
                "requirement",
                "reference",
                "notes",
            )
        },
        **{k: v for k, v in data.items() if k != "status"},
    }
    merged["status"] = (
        "draft"
        if data.get("status", current["status"]) == "archived"
        else data.get("status", current["status"])
    )
    RuleIn.model_validate(merged)  # validate the resulting rule as a whole
    return await rules.update(p, rule_id, data, body.change_note)


@router.post("/rules/{rule_id}/archive", response_model=RuleOut)
async def archive_rule(p: Admin, rule_id: str) -> dict[str, Any]:
    return await rules.update(p, rule_id, {"status": "archived"}, "Archived")


# ---------------------------------------------------------------- proposals


@router.get("/proposals", response_model=Page[ProposalOut])
async def list_proposals(
    p: Admin,
    status: Literal["pending", "approved", "rejected", "info_requested"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    items, total = await proposals.list_all(p, status, page, page_size)
    return {
        "items": [proposal_out(d) for d in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/proposals/{proposal_id}", response_model=ProposalOut)
async def get_proposal(p: Admin, proposal_id: str) -> dict[str, Any]:
    return proposal_out(await proposals.get_any(p, proposal_id))


@router.get("/proposals/{proposal_id}/report.pdf")
async def proposal_report(p: Admin, proposal_id: str) -> StreamingResponse:
    d = await proposals.get_any(p, proposal_id)
    if not d.get("report_file_id"):
        raise not_found("Report")
    it, info = await files.stream("reports", d["report_file_id"])
    return file_response(it, info, filename=f"{d['inspection_id']}.pdf", cache="private, no-store")


@router.post("/proposals/{proposal_id}/decision", response_model=ProposalOut)
async def decide_proposal(
    request: Request, p: Admin, proposal_id: str, body: ProposalDecisionIn
) -> dict[str, Any]:
    prop = await proposals.get_any(p, proposal_id)
    if body.outcome == "rejected" and not body.note.strip():
        raise AppError(
            422, "validation_error", "A reason is required when rejecting.", {"note": "Required"}
        )
    if body.outcome == "info_requested" and not body.note.strip():
        raise AppError(
            422, "validation_error", "Say what information is needed.", {"note": "Required"}
        )
    ref_id = None
    product = None
    if body.outcome == "approved":
        src = prop["product"]
        data = body.reference or ReferenceIn.model_validate(
            {
                "product_name": src["product_name"],
                "brand": src["brand"],
                "variant": src.get("variant", ""),
                "category": src["category"],
                "net_quantity": src.get("net_quantity", ""),
                "gtin": src.get("gtin", ""),
                "manufacturer": {
                    "name": src.get("manufacturer_name", ""),
                    "facility_address": src.get("manufacturer_address", ""),
                },
                "licence": {"number": src.get("fssai_licence", "")},
            }
        )
        rec = await reference.create(p, data.model_dump(mode="json"), source="proposal")
        ref_id = rec["_id"]
        if body.reference:
            product = {**prop["product"], "product_name": data.product_name, "brand": data.brand}
    return proposal_out(
        await proposals.decide(p, proposal_id, body.outcome, body.note, ref_id, product)
    )


# ---------------------------------------------------------------- users


def _user_out(u: dict[str, Any]) -> dict[str, Any]:
    u = dict(u)
    u["uid"] = u.pop("_id", u.get("uid"))
    return u


@router.get("/users", response_model=Page[UserAdminOut])
async def list_users(
    p: Admin,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: Literal["inspector", "admin", "super_admin"] | None = None,
    status: Literal["pending", "active", "disabled", "declined"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    items, total = await users.list_users(p, q, role, status, page, page_size)
    return {
        "items": [_user_out(u) for u in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/invites", response_model=list[InviteOut])
async def list_invites(p: Admin) -> list[dict[str, Any]]:
    return await users.list_invites(p)


@router.post("/users/invites", response_model=InviteOut, status_code=201)
async def create_invite(p: Admin, body: InviteIn) -> dict[str, Any]:
    return await users.create_invite(p, body.email, body.name, body.role)


@router.delete("/users/invites/{email}", response_model=OkOut)
async def delete_invite(p: Admin, email: str) -> dict[str, Any]:
    await users.delete_invite(p, email)
    return {"ok": True}


@router.get("/users/{uid}", response_model=UserDetailOut)
async def user_detail(p: Admin, uid: str) -> dict[str, Any]:
    return _user_out(await users.user_detail(p, uid))


@router.post("/users/{uid}/approve", response_model=UserAdminOut)
async def approve(p: Admin, uid: str, body: ApproveIn) -> dict[str, Any]:
    doc = await users.approve(p, uid, body.role)
    await set_claims(uid, body.role, True)
    return _user_out(doc)


@router.post("/users/{uid}/decline", response_model=UserAdminOut)
async def decline(p: Admin, uid: str) -> dict[str, Any]:
    doc = await users.decline(p, uid)
    await set_claims(uid, None, False)
    return _user_out(doc)


@router.patch("/users/{uid}", response_model=UserAdminOut)
async def patch_user(p: Admin, uid: str, body: UserPatchIn) -> dict[str, Any]:
    doc = await users.patch_user(p, uid, body.model_dump(exclude_none=True))
    if body.role is not None or body.status is not None:
        active = doc.get("status") == "active"
        await set_claims(uid, doc.get("role") if active else None, active)
        if body.status == "disabled":
            await revoke_tokens(uid)
    return _user_out(doc)


# ---------------------------------------------------------------- analytics, audit


@router.get("/analytics", response_model=AnalyticsOut)
async def analytics(
    p: Admin, range_days: Annotated[int, Query(ge=7, le=365)] = 30
) -> dict[str, Any]:
    since = datetime.now().astimezone() - timedelta(days=range_days)
    st = await insp_repo.stats(p, since)
    uc = await users.counts()
    return {
        "range_days": range_days,
        "inspections_by_day": st["by_day"],
        "by_category": st["by_category"],
        "by_classification": st["by_classification"],
        "by_status": st["by_status"],
        "top_products": st["top"],
        "proposals": await proposals.counts(),
        "users": uc,
        "active": await users.active_counts(),
        "ai_calls": await usage.calls_summary(),
        "storage": await maintenance.storage(),
    }


@router.get("/audit", response_model=Page[AuditOut])
async def audit_logs(
    p: Admin,
    q: Annotated[str | None, Query(max_length=100)] = None,
    action: Annotated[str | None, Query(max_length=40, pattern=r"^[a-z_.]+$")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    items, total = await audit.list_logs(p, q, action, date_from, date_to, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/audit/export")
async def audit_export(
    p: Admin,
    q: Annotated[str | None, Query(max_length=100)] = None,
    action: Annotated[str | None, Query(max_length=40, pattern=r"^[a-z_.]+$")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    rows = await audit.export_logs(p, q, action, date_from, date_to)
    return csv_response(
        (
            [
                r["at"].isoformat(),
                r["actor_name"],
                r.get("actor_role") or "",
                r["action"],
                r["target_type"],
                r["target_id"],
                r.get("summary", ""),
                str(r.get("changes") or {}),
            ]
            for r in rows
        ),
        ["Time (UTC)", "Actor", "Role", "Action", "Target type", "Target", "Summary", "Changes"],
        "audit-log.csv",
    )


# ---------------------------------------------------------------- settings, storage


async def _settings_out() -> dict[str, Any]:
    cfg = await settings_repo.load()
    return {
        **cfg,
        "providers": chain.provider_status(),
        "ocr_available": ocr.available(),
        "usage_today": await usage.calls_today(),
    }


@router.get("/settings", response_model=SettingsOut)
async def get_settings_(p: Admin) -> dict[str, Any]:
    return await _settings_out()


@router.patch("/settings", response_model=SettingsOut)
async def patch_settings(p: Admin, body: SettingsPatch) -> dict[str, Any]:
    await settings_repo.patch(p, body.model_dump(exclude_none=True))
    return await _settings_out()


@router.put("/settings/images/{key}", response_model=SettingsOut)
async def upload_site_image(
    request: Request, p: Admin, key: str, file: Annotated[UploadFile, File()]
) -> dict[str, Any]:
    if key not in IMAGE_KEYS:
        raise not_found("Image slot")
    max_b = 5 * 1_048_576
    data = await read_upload(file, max_b)
    meta = images.inspect_upload(data, max_b)
    fid = await files.put(
        "siteimages", data, f"{key}.{meta['format'].lower()}", meta["content_type"], {"key": key}
    )
    _, prev = await settings_repo.set_image(
        p,
        key,
        {
            "file_id": fid,
            "content_type": meta["content_type"],
            "width": meta["width"],
            "height": meta["height"],
        },
    )
    if prev:
        await files.delete("siteimages", prev)
    return await _settings_out()


@router.delete("/settings/images/{key}", response_model=SettingsOut)
async def reset_site_image(p: Admin, key: str) -> dict[str, Any]:
    if key not in IMAGE_KEYS:
        raise not_found("Image slot")
    _, prev = await settings_repo.set_image(p, key, None)
    if prev:
        await files.delete("siteimages", prev)
    return await _settings_out()


@router.get("/storage", response_model=StorageOut)
async def storage(p: Admin) -> dict[str, Any]:
    return await maintenance.storage()


@router.post("/storage/cleanup")
async def storage_cleanup(p: Admin) -> dict[str, int]:
    res = await maintenance.cleanup_expired_photos()
    await audit.log(
        p,
        "storage.cleanup",
        "storage",
        "photos",
        "Ran temporary-photo cleanup",
        {k: [0, v] for k, v in res.items()},
    )
    return res


_ = (Category, get_settings)  # re-exported types used in annotations elsewhere


# ---------------------------------------------------------------- diagnostics


@router.get("/diagnostics", response_model=list[DiagnosticInfo])
async def diagnostics_list(p: Admin) -> list[dict[str, str]]:
    return diagnostics.catalogue()


@router.post("/diagnostics/{check_id}", response_model=DiagnosticOut)
async def diagnostics_run(p: Admin, check_id: str) -> dict[str, Any]:
    res = await diagnostics.run_check(check_id)
    if res is None:
        raise not_found("Check")
    return res
