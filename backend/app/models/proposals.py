from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.models.common import Category, LongStr, MediumStr, OutModel, ShortStr, StrictModel
from app.models.reference import ReferenceIn

ProposalStatus = Literal["pending", "approved", "rejected", "info_requested"]


class ProposalProductIn(StrictModel):
    product_name: ShortStr = Field(min_length=1)
    brand: ShortStr = Field(min_length=1)
    variant: ShortStr = ""
    category: Category
    net_quantity: ShortStr = ""
    gtin: str = Field("", max_length=14, pattern=r"^\d{0,14}$")
    manufacturer_name: ShortStr = ""
    manufacturer_address: MediumStr = ""
    fssai_licence: str = Field("", max_length=20)


class ProposalIn(StrictModel):
    inspection_id: str = Field(pattern=r"^CS-\d{4}-\d{4,6}$")
    product: ProposalProductIn
    remarks: LongStr = ""


class ProposalReplyIn(StrictModel):
    message: LongStr = Field(min_length=1)


class ProposalDecisionIn(StrictModel):
    outcome: Literal["approved", "rejected", "info_requested", "pending"]
    note: LongStr = ""
    reference: ReferenceIn | None = None  # admin-edited data used when approving


class ProposalOut(OutModel):
    id: str
    inspection_id: str
    owner_uid: str
    owner_name: str = ""
    product: dict[str, Any]
    remarks: str = ""
    status: ProposalStatus
    reviews: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    reference_id: str | None = None
    has_report: bool = False
    photo_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None
