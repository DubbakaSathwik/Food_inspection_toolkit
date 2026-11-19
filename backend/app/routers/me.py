"""/me — profile bootstrap and claim synchronisation (REQ-001/002/004/005)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.auth import claims_match, set_claims, token_claims
from app.config import get_settings
from app.errors import AppError
from app.models.users import MeOut, MeUpdate
from app.principal import Principal
from app.repositories import users as users_repo

router = APIRouter(prefix="/api/v1", tags=["me"])


def _out(user: dict[str, Any], stale: bool) -> MeOut:
    return MeOut(
        uid=user["_id"],
        email=user["email"],
        name=user.get("name", ""),
        photo_url=user.get("photo_url"),
        role=user.get("role"),
        status=user.get("status", "pending"),
        designation=user.get("designation", ""),
        office=user.get("office", ""),
        phone=user.get("phone", ""),
        created_at=user.get("created_at"),
        claims_stale=stale,
    )


@router.get("/me", response_model=MeOut)
async def me(claims: dict[str, Any] = Depends(token_claims)) -> MeOut:
    user = await users_repo.ensure_profile(
        claims["uid"],
        claims["email"],
        claims.get("name") or "",
        claims.get("picture"),
        bool(claims.get("email_verified")),
        get_settings().super_admin_email,
    )
    stale = False
    if not claims_match(claims, user):
        # Server-side claim sync: only this code (and admin actions) ever set roles (BR-09).
        active = user.get("status") == "active"
        await set_claims(user["_id"], user.get("role") if active else None, active)
        stale = True
    if user.get("status") == "active":
        await users_repo.touch_active(user["_id"])
    return _out(user, stale)


@router.patch("/me", response_model=MeOut)
async def update_me(body: MeUpdate, claims: dict[str, Any] = Depends(token_claims)) -> MeOut:
    user = await users_repo.get(claims["uid"])
    if not user:
        raise AppError(404, "not_found", "Profile not found.")
    p = Principal(
        uid=user["_id"],
        email=user["email"],
        name=user.get("name", ""),
        role=user.get("role"),
        status=user.get("status", "pending"),
    )
    doc = await users_repo.update_profile(p, body.model_dump(exclude_none=True))
    return _out(doc, False)
