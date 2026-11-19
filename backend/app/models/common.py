from __future__ import annotations

from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

T = TypeVar("T")

Category = Literal["beverages", "snacks", "dairy", "staples"]
Classification = Literal["verified", "not_verified", "suspicious"]
Severity = Literal["info", "warning", "high"]

ShortStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
MediumStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
LongStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=8000)]
NonEmptyShort = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class StrictModel(BaseModel):
    """Request bodies: reject unknown fields (prevents mass-assignment of protected fields)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OutModel(BaseModel):
    """Response bodies: ignore extra stored fields."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Page(OutModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams(StrictModel):
    page: int = Field(1, ge=1, le=10_000)
    page_size: int = Field(20, ge=1, le=100)


class OkOut(OutModel):
    ok: bool = True


class TimestampedOut(OutModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
