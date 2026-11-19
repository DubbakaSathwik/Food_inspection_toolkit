"""Excel/CSV bulk import of reference records with a validation preview (REQ-055)."""

from __future__ import annotations

import csv
import io
from typing import Any

from pydantic import ValidationError

from app.errors import AppError
from app.models.reference import ReferenceIn

COLUMNS = [
    "product_name",
    "brand",
    "variant",
    "category",
    "net_quantity",
    "package_sizes",
    "gtin",
    "manufacturer_name",
    "registered_address",
    "facility_address",
    "state",
    "district",
    "contact",
    "licence_number",
    "licence_valid_from",
    "licence_valid_until",
    "licence_status",
    "fbo_category",
    "notes",
]
MAX_ROWS = 1000


def _rows_from_csv(data: bytes) -> list[dict[str, str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise AppError(400, "bad_file", "CSV must be UTF-8 encoded.") from e
    reader = csv.DictReader(io.StringIO(text))
    return [
        {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader
    ]


def _rows_from_xlsx(data: bytes) -> list[dict[str, str]]:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as e:
        raise AppError(400, "bad_file", "Could not read the Excel file.") from e
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = [str(c or "").strip().lower() for c in next(rows, [])]
    out = []
    for r in rows:
        if r is None or all(c in (None, "") for c in r):
            continue
        out.append(
            {
                header[i]: ("" if c is None else str(c).strip())
                for i, c in enumerate(r)
                if i < len(header)
            }
        )
    return out


def to_reference(row: dict[str, str]) -> dict[str, Any]:
    sizes = [s.strip() for s in (row.get("package_sizes") or "").split(";") if s.strip()]
    return {
        "product_name": row.get("product_name", ""),
        "brand": row.get("brand", ""),
        "variant": row.get("variant", ""),
        "category": (row.get("category") or "").lower(),
        "net_quantity": row.get("net_quantity", ""),
        "package_sizes": sizes,
        "gtin": "".join(ch for ch in row.get("gtin", "") if ch.isdigit()),
        "manufacturer": {
            "name": row.get("manufacturer_name", ""),
            "registered_address": row.get("registered_address", ""),
            "facility_address": row.get("facility_address", ""),
            "state": row.get("state", ""),
            "district": row.get("district", ""),
            "contact": row.get("contact", ""),
        },
        "licence": {
            "number": row.get("licence_number", ""),
            "valid_from": (row.get("licence_valid_from") or "")[:10] or None,
            "valid_until": (row.get("licence_valid_until") or "")[:10] or None,
            "status": (row.get("licence_status") or "active").lower(),
            "fbo_category": row.get("fbo_category", ""),
        },
        "notes": row.get("notes", ""),
        "source": "import",
    }


def preview(filename: str, data: bytes) -> dict[str, Any]:
    name = filename.lower()
    if name.endswith(".csv"):
        rows = _rows_from_csv(data)
    elif name.endswith(".xlsx"):
        rows = _rows_from_xlsx(data)
    else:
        raise AppError(415, "unsupported_file", "Upload a .csv or .xlsx file.")
    if not rows:
        raise AppError(400, "empty_file", "No data rows found.")
    if len(rows) > MAX_ROWS:
        raise AppError(400, "too_many_rows", f"Import at most {MAX_ROWS} rows at a time.")
    missing = [c for c in ("product_name", "brand", "category") if c not in rows[0]]
    if missing:
        raise AppError(
            400,
            "bad_columns",
            "Missing required columns: " + ", ".join(missing),
            {"columns": "Expected: " + ", ".join(COLUMNS)},
        )
    out, valid = [], 0
    for i, row in enumerate(rows, start=2):
        candidate = to_reference(row)
        try:
            model = ReferenceIn.model_validate(candidate)
            out.append({"row": i, "data": model.model_dump(mode="json"), "errors": {}})
            valid += 1
        except ValidationError as e:
            errs = {".".join(str(p) for p in er["loc"]) or "row": er["msg"] for er in e.errors()}
            out.append({"row": i, "data": candidate, "errors": errs})
    return {"rows": out, "valid": valid, "invalid": len(out) - valid}
