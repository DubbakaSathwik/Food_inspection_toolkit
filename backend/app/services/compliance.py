"""Compliance engine over admin-maintained demo rules (REQ-024/025). No legal verdicts (BR-01)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.services.fields import FIELD_BY_KEY, is_blank, parse_date

MAX_TEXT = 4000


def evaluate_rule(
    rule: dict[str, Any], values: dict[str, str | None], today: date
) -> dict[str, Any]:
    key = rule["field"]
    val = values.get(key)
    label = FIELD_BY_KEY[key].label if key in FIELD_BY_KEY else key
    ct = rule["check_type"]
    result, reason = "pass", ""
    if ct == "required_field":
        if is_blank(val):
            result, reason = "fail", f"{label} was not found on the photographs."
    elif ct == "pattern":
        if is_blank(val):
            result, reason = (
                "fail",
                f"{label} was not found, so the required wording could not be checked.",
            )
        else:
            assert val is not None
            try:
                ok = re.search(rule.get("pattern") or "", val[:MAX_TEXT], re.I) is not None
            except re.error:
                ok = True
                result, reason = (
                    "not_applicable",
                    "Rule pattern is invalid; ask an administrator to fix it.",
                )
            if not ok:
                result, reason = "fail", f"{label} does not contain the expected statement."
    elif ct == "claim_keywords":
        if not is_blank(val):
            assert val is not None
            hits = [k for k in rule.get("keywords", []) if k and k.lower() in val.lower()]
            if hits:
                result = "review"
                reason = (
                    "Claim wording needs substantiation review: "
                    + ", ".join(f"'{h}'" for h in hits)
                    + "."
                )
        else:
            result = "not_applicable"
    elif ct == "date_not_expired":
        d = parse_date(val)
        if is_blank(val):
            result, reason = "fail", f"{label} was not found."
        elif d is None:
            result, reason = (
                "review",
                f"{label} could not be read as a calendar date; check it on the pack.",
            )
        elif d < today:
            result, reason = "fail", f"{label} ({d.isoformat()}) is before the inspection date."
    return {
        "rule_id": str(rule.get("_id", "")),
        "rule_code": rule["code"],
        "title": rule["title"],
        "category": rule["category"],
        "version": rule.get("version", 1),
        "severity": rule.get("severity", "warning"),
        "requirement": rule.get("requirement", ""),
        "reference": rule.get("reference", ""),
        "field": key,
        "field_label": label,
        "extracted": val,
        "result": result,
        "reason": reason,
        "claim": ct == "claim_keywords",
    }


def evaluate(
    rules: list[dict[str, Any]], values: dict[str, str | None], today: date | None = None
) -> list[dict[str, Any]]:
    today = today or date.today()
    return [evaluate_rule(r, values, today) for r in rules]
