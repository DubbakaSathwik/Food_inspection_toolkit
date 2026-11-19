from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.models.common import (
    Category,
    Classification,
    LongStr,
    MediumStr,
    OutModel,
    Severity,
    ShortStr,
    StrictModel,
)

InspectionStatus = Literal["draft", "incomplete", "extracted", "analysed", "completed"]
PhotoLabel = Literal["front", "back", "side", "closeup", "other"]


class CropRect(StrictModel):
    """Fractions of the original image (0–1)."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0.02, le=1)
    h: float = Field(gt=0.02, le=1)

    @model_validator(mode="after")
    def _inside(self) -> CropRect:
        if self.x + self.w > 1.0001 or self.y + self.h > 1.0001:
            raise ValueError("Crop must stay inside the photo.")
        return self


class PhotoQuality(OutModel):
    ok: bool
    issues: list[str] = []
    blur_score: float | None = None
    brightness: float | None = None


class PhotoOut(OutModel):
    id: str
    label: PhotoLabel = "other"
    filename: str = ""
    content_type: str = ""
    width: int = 0
    height: int = 0
    size: int = 0
    quality: PhotoQuality
    crop: CropRect | None = None
    uploaded_at: datetime | None = None


class PhotoUpdate(StrictModel):
    label: PhotoLabel | None = None
    crop: CropRect | None = None
    clear_crop: bool = False


class FieldHistory(OutModel):
    value: str | None
    at: datetime
    by: str


class FieldOut(OutModel):
    key: str
    label: str
    group: str
    ai_value: str | None = None
    ai_confidence: float | None = None
    confidence_level: str = "Low"
    source_photo: int | None = None
    flag: Literal["ok", "check", "not_found"] = "not_found"
    note: str | None = None
    value: str | None = None
    status: Literal["auto", "pending", "confirmed", "edited"] = "pending"
    history: list[FieldHistory] = []


class FieldUpdate(StrictModel):
    value: str | None = Field(None, max_length=4000)
    confirm: bool = True


class ConfirmFieldsIn(StrictModel):
    keys: list[str] = Field(default_factory=list, max_length=40)


class CategoryIn(StrictModel):
    category: Category


class ExtractionAttempt(OutModel):
    provider: str
    ok: bool
    error: str | None = None
    at: datetime


class ExtractionOut(OutModel):
    status: Literal["not_started", "done", "failed"] = "not_started"
    provider: str | None = None
    ocr_used: bool = False
    at: datetime | None = None
    attempts: list[ExtractionAttempt] = []


class Decision(OutModel):
    action: Literal["accepted", "dismissed", "corrected"]
    corrected_value: str | None = None
    note: str | None = None
    at: datetime | None = None


class FindingOut(OutModel):
    id: str
    kind: Literal["reference", "licence", "packaging", "compliance", "claim", "extraction"]
    title: str
    severity: Severity
    status_label: str
    detail: str
    extracted: str | None = None
    expected: str | None = None
    rule_code: str | None = None
    rule_reference: str | None = None
    evidence_photo: int | None = None
    ai_original: str | None = None
    decision: Decision | None = None


class FindingDecisionIn(StrictModel):
    action: Literal["accepted", "dismissed", "corrected"]
    corrected_value: MediumStr | None = None
    note: MediumStr | None = None

    @model_validator(mode="after")
    def _needs_value(self) -> FindingDecisionIn:
        if self.action == "corrected" and not (self.corrected_value or "").strip():
            raise ValueError("A corrected value is required.")
        return self


class Suggestion(OutModel):
    classification: Classification
    reasons: list[str] = []
    provisional: bool = True


class DecisionIn(StrictModel):
    classification: Classification
    remarks: LongStr = ""


class InspectionDecisionOut(OutModel):
    classification: Classification
    remarks: str = ""
    at: datetime | None = None


class ReportIn(StrictModel):
    signature_name: ShortStr = Field(min_length=2)
    confirm_reviewed: bool

    @model_validator(mode="after")
    def _confirmed(self) -> ReportIn:
        if not self.confirm_reviewed:
            raise ValueError("Confirm that you have reviewed the findings.")
        return self


class ReportOut(OutModel):
    generated_at: datetime
    size: int
    signature_name: str
    pages: int = 0


class NoteIn(StrictModel):
    text: LongStr = Field(min_length=1)


class NoteOut(OutModel):
    id: str
    text: str
    created_at: datetime


class InspectionSummary(OutModel):
    id: str
    product_name: str | None = None
    brand: str | None = None
    category: Category | None = None
    status: InspectionStatus
    classification: Classification | None = None
    photo_count: int = 0
    fields_extracted: int = 0
    findings_open: int = 0
    created_at: datetime
    updated_at: datetime | None = None
    has_report: bool = False


class InspectionOut(OutModel):
    id: str
    status: InspectionStatus
    owner_name: str = ""
    created_at: datetime
    updated_at: datetime | None = None
    photos: list[PhotoOut] = []
    photos_deleted: bool = False
    category: Category | None = None
    category_source: str | None = None
    extraction: ExtractionOut = ExtractionOut()
    fields: list[FieldOut] = []
    analysis: dict[str, Any] | None = None
    findings: list[FindingOut] = []
    suggestion: Suggestion | None = None
    decision: InspectionDecisionOut | None = None
    report: ReportOut | None = None
    notes: list[NoteOut] = []
    proposal_id: str | None = None


class HistoryQuery(StrictModel):
    q: ShortStr | None = None
    category: Category | None = None
    classification: Classification | None = None
    status: InspectionStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(1, ge=1, le=10_000)
    page_size: int = Field(20, ge=1, le=100)


class DashboardOut(OutModel):
    total: int
    completed: int
    pending_reviews: int
    proposals: int
    continue_items: list[InspectionSummary]
    recent: list[InspectionSummary]
    by_classification: dict[str, int]


class CreateInspectionIn(StrictModel):
    note: ShortStr | None = None
