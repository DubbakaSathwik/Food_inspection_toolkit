from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator

from app.models.common import Category, MediumStr, OutModel, ShortStr, StrictModel

LicenceStatus = Literal["active", "expired", "suspended"]


class ManufacturerIn(StrictModel):
    name: ShortStr = ""
    registered_address: MediumStr = ""
    facility_address: MediumStr = ""
    state: ShortStr = ""
    district: ShortStr = ""
    contact: ShortStr = ""


class LicenceIn(StrictModel):
    number: str = Field("", max_length=20)
    valid_from: date | None = None
    valid_until: date | None = None
    status: LicenceStatus = "active"
    fbo_category: ShortStr = ""

    @field_validator("number")
    @classmethod
    def _digits(cls, v: str) -> str:
        v = "".join(ch for ch in v if ch.isdigit())
        if v and len(v) != 14:
            raise ValueError("FSSAI licence / registration numbers have 14 digits.")
        return v


class ReferenceIn(StrictModel):
    product_name: ShortStr = Field(min_length=1)
    brand: ShortStr = Field(min_length=1)
    variant: ShortStr = ""
    category: Category
    net_quantity: ShortStr = ""
    package_sizes: list[ShortStr] = Field(default_factory=list, max_length=20)
    gtin: str = Field("", max_length=14, pattern=r"^\d{0,14}$")
    manufacturer: ManufacturerIn = ManufacturerIn()
    licence: LicenceIn = LicenceIn()
    notes: MediumStr = ""
    source: Literal["manual", "ai_assisted", "import", "proposal"] = "manual"


class ReferencePatch(StrictModel):
    product_name: ShortStr | None = Field(None, min_length=1)
    brand: ShortStr | None = Field(None, min_length=1)
    variant: ShortStr | None = None
    category: Category | None = None
    net_quantity: ShortStr | None = None
    package_sizes: list[ShortStr] | None = Field(None, max_length=20)
    gtin: str | None = Field(None, max_length=14, pattern=r"^\d{0,14}$")
    manufacturer: ManufacturerIn | None = None
    licence: LicenceIn | None = None
    notes: MediumStr | None = None


class RefImageOut(OutModel):
    file_id: str
    side: str = "front"
    uploaded_at: datetime | None = None


class PackagingVersionOut(OutModel):
    id: str
    label: str
    notes: str = ""
    images: list[RefImageOut] = []
    created_at: datetime | None = None


class ReferenceOut(OutModel):
    id: str
    product_name: str
    brand: str
    variant: str = ""
    category: Category
    net_quantity: str = ""
    package_sizes: list[str] = []
    gtin: str = ""
    manufacturer: dict[str, str] = {}
    licence: dict[str, str | None] = {}
    notes: str = ""
    source: str = "manual"
    status: Literal["active", "archived"] = "active"
    demo: bool = True
    packaging_versions: list[PackagingVersionOut] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReferenceQuery(StrictModel):
    q: ShortStr | None = None
    category: Category | None = None
    status: Literal["active", "archived", "all"] = "active"
    page: int = Field(1, ge=1, le=10_000)
    page_size: int = Field(20, ge=1, le=100)


class ImportRow(OutModel):
    row: int
    data: dict[str, object] | None = None
    errors: dict[str, str] = {}


class ImportPreviewOut(OutModel):
    rows: list[ImportRow]
    valid: int
    invalid: int


class ImportCommitIn(StrictModel):
    rows: list[ReferenceIn] = Field(min_length=1, max_length=1000)


class AiDraftOut(OutModel):
    draft: dict[str, object]
    confidence: dict[str, str]
    provider: str
