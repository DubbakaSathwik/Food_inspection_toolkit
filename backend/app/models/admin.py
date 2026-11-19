from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.models.common import MediumStr, OutModel, Severity, ShortStr, StrictModel

RuleCategory = Literal["beverages", "snacks", "dairy", "staples", "all"]
CheckType = Literal["required_field", "pattern", "claim_keywords", "date_not_expired"]
RuleStatus = Literal["active", "draft", "archived"]


class RuleIn(StrictModel):
    code: str = Field(min_length=3, max_length=20, pattern=r"^[A-Z0-9-]+$")
    title: ShortStr = Field(min_length=3)
    category: RuleCategory
    check_type: CheckType
    field: str = Field(min_length=2, max_length=40)
    pattern: str | None = Field(None, max_length=200)
    keywords: list[ShortStr] = Field(default_factory=list, max_length=40)
    severity: Severity = "warning"
    requirement: MediumStr = Field(min_length=3)
    reference: ShortStr = ""
    status: Literal["active", "draft"] = "draft"
    notes: MediumStr = ""

    @field_validator("pattern")
    @classmethod
    def _regex(cls, v: str | None) -> str | None:
        if v:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid pattern: {e}") from e
        return v

    @model_validator(mode="after")
    def _logic(self) -> RuleIn:
        from app.services.fields import FIELD_KEYS

        if self.field not in FIELD_KEYS:
            raise ValueError(f"Unknown field '{self.field}'.")
        if self.check_type == "pattern" and not self.pattern:
            raise ValueError("A pattern rule needs a pattern.")
        if self.check_type == "claim_keywords" and not self.keywords:
            raise ValueError("A claim rule needs at least one keyword.")
        return self


class RulePatch(StrictModel):
    title: ShortStr | None = None
    category: RuleCategory | None = None
    check_type: CheckType | None = None
    field: str | None = Field(None, max_length=40)
    pattern: str | None = Field(None, max_length=200)
    keywords: list[ShortStr] | None = Field(None, max_length=40)
    severity: Severity | None = None
    requirement: MediumStr | None = None
    reference: ShortStr | None = None
    status: RuleStatus | None = None
    notes: MediumStr | None = None
    change_note: ShortStr = ""


class RuleOut(OutModel):
    id: str
    code: str
    title: str
    category: RuleCategory
    check_type: CheckType
    field: str
    pattern: str | None = None
    keywords: list[str] = []
    severity: Severity
    requirement: str
    reference: str = ""
    status: RuleStatus
    notes: str = ""
    version: int = 1
    demo: bool = True
    history: list[dict[str, Any]] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RulesStatsOut(OutModel):
    active: int
    draft: int
    archived: int
    categories: int
    last_update: datetime | None


class AuditOut(OutModel):
    id: str
    actor_uid: str
    actor_name: str
    actor_role: str | None = None
    action: str
    target_type: str
    target_id: str
    summary: str = ""
    changes: dict[str, Any] = {}
    at: datetime


class SettingsGeneral(StrictModel):
    org_name: ShortStr = "CRATE-SCAN"
    report_footer: MediumStr = (
        "Decision-support report. Demo reference data; not official government verification."
    )
    auto_confirm_threshold: float = Field(0.85, ge=0.5, le=1.0)


class SettingsAi(StrictModel):
    web_research_enabled: bool = True
    ocr_fallback_enabled: bool = True


class SettingsLimits(StrictModel):
    ai_daily_limit_per_user: int = Field(60, ge=1, le=10_000)
    photo_retention_days: int = Field(7, ge=1, le=90)


class SettingsPatch(StrictModel):
    general: SettingsGeneral | None = None
    ai: SettingsAi | None = None
    limits: SettingsLimits | None = None


class ProviderStatus(OutModel):
    name: str
    configured: bool
    model: str | None = None
    position: int


class SettingsOut(OutModel):
    general: SettingsGeneral
    ai: SettingsAi
    limits: SettingsLimits
    images: dict[str, dict[str, Any] | None]
    providers: list[ProviderStatus]
    ocr_available: bool
    usage_today: int
    updated_at: datetime | None = None
    updated_by_name: str | None = None


class StorageOut(OutModel):
    data_mb: float
    storage_mb: float
    limit_mb: float
    buckets: dict[str, dict[str, float]]
    temporary_photos_expired: int


class AdminDashboardOut(OutModel):
    users_total: int
    inspectors: int
    pending_approvals: int
    dau: int
    wau: int
    mau: int
    inspections_total: int
    inspections_week: int
    reference_products: int
    proposals: dict[str, int]
    pending_users: list[dict[str, Any]]
    pending_proposals: list[dict[str, Any]]
    recent_activity: list[dict[str, Any]]


class AnalyticsOut(OutModel):
    range_days: int
    inspections_by_day: list[dict[str, Any]]
    by_category: dict[str, int]
    by_classification: dict[str, int]
    by_status: dict[str, int]
    top_products: list[dict[str, Any]]
    proposals: dict[str, int]
    users: dict[str, int]
    active: dict[str, int]
    ai_calls: dict[str, int]
    storage: StorageOut


class DiagnosticInfo(OutModel):
    id: str
    title: str
    description: str


class DiagnosticOut(OutModel):
    id: str
    title: str
    status: Literal["ok", "warn", "fail", "skip"]
    detail: str
    hints: list[str] = []
    ms: int
