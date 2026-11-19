"""The verified caller, passed into every repository function that touches user data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["inspector", "admin", "super_admin"]
Status = Literal["pending", "active", "disabled", "declined"]
ROLES: tuple[Role, ...] = ("inspector", "admin", "super_admin")


@dataclass(frozen=True)
class Principal:
    uid: str
    email: str
    name: str
    role: Role | None
    status: Status

    @property
    def is_admin(self) -> bool:
        return self.status == "active" and self.role in ("admin", "super_admin")

    @property
    def is_super_admin(self) -> bool:
        return self.status == "active" and self.role == "super_admin"

    @property
    def is_inspector(self) -> bool:
        return self.status == "active" and self.role == "inspector"
