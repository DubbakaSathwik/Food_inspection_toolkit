from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.models.common import OutModel, ShortStr, StrictModel

RoleT = Literal["inspector", "admin", "super_admin"]
StatusT = Literal["pending", "active", "disabled", "declined"]


class UserDoc(OutModel):
    """Stored in `users` (_id = Firebase UID)."""

    uid: str = Field(alias="_id")
    email: str
    name: str = ""
    photo_url: str | None = None
    role: RoleT | None = None
    status: StatusT = "pending"
    designation: str = ""
    office: str = ""
    phone: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    last_active_at: datetime | None = None


class MeOut(OutModel):
    uid: str
    email: str
    name: str
    photo_url: str | None = None
    role: RoleT | None
    status: StatusT
    designation: str = ""
    office: str = ""
    phone: str = ""
    created_at: datetime | None = None
    claims_stale: bool = False


class MeUpdate(StrictModel):
    name: ShortStr | None = Field(None, min_length=1)
    designation: ShortStr | None = None
    office: ShortStr | None = None
    phone: str | None = Field(None, max_length=40, pattern=r"^[0-9+()\-\s]*$")


class UserAdminOut(OutModel):
    uid: str
    email: str
    name: str
    role: RoleT | None
    status: StatusT
    designation: str = ""
    office: str = ""
    created_at: datetime | None = None
    approved_at: datetime | None = None
    last_active_at: datetime | None = None
    inspections: int = 0


class UserDetailOut(UserAdminOut):
    completed_inspections: int = 0
    proposals: int = 0
    recent: list[dict[str, str]] = []


class ApproveIn(StrictModel):
    role: RoleT = "inspector"


class UserPatchIn(StrictModel):
    role: RoleT | None = None
    status: Literal["active", "disabled"] | None = None
    name: ShortStr | None = None
    designation: ShortStr | None = None
    office: ShortStr | None = None


class InviteIn(StrictModel):
    email: EmailStr
    name: ShortStr = ""
    role: RoleT = "inspector"


class InviteOut(OutModel):
    email: str
    name: str
    role: RoleT
    created_at: datetime | None = None
    created_by_name: str = ""
