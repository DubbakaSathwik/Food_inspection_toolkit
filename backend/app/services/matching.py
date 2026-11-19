"""Reference matching (REQ-020/021) and demo licence check (REQ-022). Pure functions + repository reads.

Results are comparisons against fictional demo records — never government verification (BR-03)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from rapidfuzz import fuzz

from app.services.fields import is_blank, normalise_quantity

_CORP = re.compile(r"\b(pvt|private|ltd|limited|llp|inc|co|company|industries|foods?)\b\.?", re.I)


def norm(text: str | None) -> str:
    if is_blank(text):
        return ""
    assert text is not None
    t = text.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_company(text: str | None) -> str:
    return re.sub(r"\s+", " ", _CORP.sub(" ", norm(text))).strip()


def digits(text: str | None) -> str:
    return re.sub(r"\D", "", text or "")


def sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return float(fuzz.token_set_ratio(a, b))


def _row(label: str, extracted: str | None, reference: str | None, result: str) -> dict[str, Any]:
    return {
        "field": label,
        "extracted": extracted or "—",
        "reference": reference or "—",
        "result": result,
    }


def score_record(v: dict[str, str | None], rec: dict[str, Any]) -> dict[str, float]:
    m = rec.get("manufacturer") or {}
    return {
        "brand": sim(norm(v.get("brand")), norm(rec.get("brand"))),
        "product": sim(norm(v.get("product_name")), norm(rec.get("product_name"))),
        "variant": sim(norm(v.get("variant")), norm(rec.get("variant"))),
        "manufacturer": sim(norm_company(v.get("manufacturer_name")), norm_company(m.get("name"))),
        "address": sim(
            norm(v.get("manufacturer_address")),
            norm(m.get("facility_address") or m.get("registered_address")),
        ),
        "licence": 100.0
        if digits(v.get("fssai_licence"))
        and digits(v.get("fssai_licence")) == (rec.get("licence") or {}).get("number")
        else 0.0,
        "gtin": 100.0
        if digits(v.get("barcode")) and digits(v.get("barcode")) == rec.get("gtin")
        else 0.0,
    }


def match(values: dict[str, str | None], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Return status exact|partial|mismatch|no_record|insufficient with evidence rows."""
    has_identity = any(
        not is_blank(values.get(k)) for k in ("brand", "product_name", "fssai_licence", "barcode")
    )
    if not has_identity:
        return {
            "status": "insufficient",
            "record_id": None,
            "record_label": None,
            "score": 0,
            "comparisons": [],
            "detail": "Brand, product name, licence and barcode could not be read.",
        }
    best, best_s, best_total = None, None, -1.0
    for rec in candidates:
        s = score_record(values, rec)
        total = s["brand"] * 0.3 + s["product"] * 0.35 + s["licence"] * 0.2 + s["gtin"] * 0.15
        if total > best_total:
            best, best_s, best_total = rec, s, total
    if (
        best is None
        or best_s is None
        or (best_s["brand"] < 70 and best_s["licence"] < 100 and best_s["gtin"] < 100)
    ):
        return {
            "status": "no_record",
            "record_id": None,
            "record_label": None,
            "score": 0,
            "comparisons": [],
            "detail": "No matching record in the demo reference database. This does not mean the product is fake.",
        }

    m = best.get("manufacturer") or {}
    lic = best.get("licence") or {}
    q_ext, q_ref = (
        normalise_quantity(values.get("net_quantity")),
        normalise_quantity(best.get("net_quantity")),
    )
    sizes = {normalise_quantity(x) for x in best.get("package_sizes", []) if x} | (
        {q_ref} if q_ref else set()
    )
    qty_ok = (q_ext in sizes) if (q_ext and sizes) else None

    def res(score: float, present: bool, threshold: float = 85) -> str:
        if not present:
            return "missing"
        return "match" if score >= threshold else "differs"

    rows = [
        _row(
            "Brand",
            values.get("brand"),
            best.get("brand"),
            res(best_s["brand"], not is_blank(values.get("brand"))),
        ),
        _row(
            "Product name",
            values.get("product_name"),
            best.get("product_name"),
            res(best_s["product"], not is_blank(values.get("product_name"))),
        ),
        _row(
            "Variant",
            values.get("variant"),
            best.get("variant"),
            res(
                best_s["variant"],
                not is_blank(values.get("variant")) and bool(best.get("variant")),
                80,
            ),
        ),
        _row(
            "Net quantity / pack size",
            values.get("net_quantity"),
            ", ".join(best.get("package_sizes") or []) or best.get("net_quantity"),
            "missing" if qty_ok is None else ("match" if qty_ok else "differs"),
        ),
        _row(
            "Manufacturer",
            values.get("manufacturer_name"),
            m.get("name"),
            res(best_s["manufacturer"], not is_blank(values.get("manufacturer_name"))),
        ),
        _row(
            "Manufacturer address",
            values.get("manufacturer_address"),
            m.get("facility_address") or m.get("registered_address"),
            res(best_s["address"], not is_blank(values.get("manufacturer_address")), 80),
        ),
        _row(
            "FSSAI licence (demo)",
            values.get("fssai_licence"),
            lic.get("number"),
            "missing"
            if not digits(values.get("fssai_licence"))
            else ("match" if best_s["licence"] == 100 else "differs"),
        ),
        _row(
            "Barcode / GTIN",
            values.get("barcode"),
            best.get("gtin"),
            "missing"
            if not digits(values.get("barcode")) or not best.get("gtin")
            else ("match" if best_s["gtin"] == 100 else "differs"),
        ),
    ]
    differs = [r for r in rows if r["result"] == "differs"]
    identity_ok = best_s["brand"] >= 85 and best_s["product"] >= 85
    critical_diff = any(r["field"] in ("FSSAI licence (demo)", "Manufacturer") for r in differs)
    if (
        identity_ok
        and not differs
        and all(r["result"] == "match" for r in rows[:2])
        and rows[6]["result"] == "match"
        and rows[4]["result"] == "match"
    ):
        status = "exact"
    elif identity_ok and critical_diff:
        status = "mismatch"
    else:
        status = "partial"
    detail = {
        "exact": "Product, manufacturer and demo licence match the reference record.",
        "partial": "Some details match the reference record; others differ or could not be read.",
        "mismatch": "Product identity matches a reference record but the manufacturer or licence differs.",
    }[status]
    return {
        "status": status,
        "record_id": best["_id"],
        "record_label": f"{best.get('brand', '')} {best.get('product_name', '')}".strip(),
        "score": round(best_total, 1),
        "comparisons": rows,
        "detail": detail,
    }


def licence_check(
    value: str | None,
    records: list[dict[str, Any]],
    manufacturer: str | None,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    num = digits(value)
    if not num:
        return {
            "status": "missing",
            "label": "No licence number read",
            "detail": "Licence number not found on the photographs.",
            "record_id": None,
        }
    if len(num) != 14:
        return {
            "status": "invalid_format",
            "label": "Format appears invalid",
            "detail": f"Read {len(num)} digits; FSSAI numbers have 14.",
            "record_id": None,
            "number": num,
        }
    if not records:
        return {
            "status": "not_found",
            "label": "Not in demo records",
            "detail": "The number is not in the demo reference database (not a government check).",
            "record_id": None,
            "number": num,
        }
    rec = records[0]
    lic = rec.get("licence") or {}
    status = lic.get("status", "active")
    until = lic.get("valid_until")
    expired_by_date = False
    if isinstance(until, str):
        try:
            expired_by_date = date.fromisoformat(until) < today
        except ValueError:
            expired_by_date = False
    if status == "suspended":
        return {
            "status": "suspended",
            "label": "Demo record: suspended",
            "detail": "The demo record marks this licence as suspended.",
            "record_id": rec["_id"],
            "number": num,
        }
    if status == "expired" or expired_by_date:
        return {
            "status": "expired",
            "label": "Demo record: expired",
            "detail": f"The demo record shows validity until {until or 'an earlier date'}.",
            "record_id": rec["_id"],
            "number": num,
        }
    mname = (rec.get("manufacturer") or {}).get("name")
    if manufacturer and mname and sim(norm_company(manufacturer), norm_company(mname)) < 70:
        return {
            "status": "needs_review",
            "label": "Holder differs — review",
            "detail": f"Demo record holder is '{mname}', label shows '{manufacturer}'.",
            "record_id": rec["_id"],
            "number": num,
        }
    return {
        "status": "found",
        "label": "Matching demo record found",
        "detail": "Matches a demo record. This is not official government verification.",
        "record_id": rec["_id"],
        "number": num,
    }
