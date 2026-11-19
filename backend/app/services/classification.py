"""Provisional classification suggestion (D-09 / A-04). The owner will finalise the criteria (U-01).
The inspector always selects the final classification (BR-01, BR-06)."""

from __future__ import annotations

from typing import Any

CRITERIA_NOTE = (
    "Provisional suggestion — criteria are not finalised. Any open high-severity finding suggests "
    "Suspicious; an exact demo-reference match with no open warnings suggests Verified; otherwise Not verified."
)


def open_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in findings if not (f.get("decision") or {}).get("action") == "dismissed"]


def suggest(findings: list[dict[str, Any]], reference_status: str | None) -> dict[str, Any]:
    active = open_findings(findings)
    high = [f for f in active if f["severity"] == "high"]
    warn = [f for f in active if f["severity"] == "warning"]
    if high:
        cls = "suspicious"
        reasons = [f"{f['title']}: {f['status_label']}" for f in high[:4]]
    elif reference_status == "exact" and not warn:
        cls = "verified"
        reasons = ["Exact match with a demo reference record", "No open warnings"]
    else:
        cls = "not_verified"
        reasons = [f"Reference: {reference_status or 'not checked'}"] + [
            f["title"] for f in warn[:3]
        ]
    return {"classification": cls, "reasons": reasons, "provisional": True, "note": CRITERIA_NOTE}
