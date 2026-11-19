"""Label fields extracted from product photographs (groups/labels match the Verify Fields design)
and deterministic validation of their values (REQ-017)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

CATEGORIES: dict[str, str] = {
    "beverages": "Packaged beverages and water",
    "snacks": "Packaged snacks",
    "dairy": "Dairy products",
    "staples": "Packaged groceries and food staples",
}


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str
    group: str


FIELD_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Product identity",
        [("product_name", "Product name"), ("brand", "Brand"), ("variant", "Variant / flavour")],
    ),
    (
        "Manufacturer and licence",
        [
            ("manufacturer_name", "Manufacturer name"),
            ("manufacturer_address", "Manufacturer address"),
            ("fssai_licence", "FSSAI licence / registration no."),
            ("customer_care", "Customer care"),
        ],
    ),
    (
        "Dates and batch",
        [
            ("mfg_date", "Manufacturing date"),
            ("expiry", "Expiry / best before"),
            ("batch", "Batch / lot number"),
        ],
    ),
    (
        "Quantity and pricing",
        [("net_quantity", "Net quantity"), ("mrp", "MRP"), ("selling_price", "Selling price")],
    ),
    (
        "Ingredients and nutrition",
        [
            ("ingredients", "Ingredients"),
            ("nutrition", "Nutritional information"),
            ("allergens", "Allergen declaration"),
        ],
    ),
    (
        "Declarations and symbols",
        [
            ("veg_symbol", "Vegetarian / non-vegetarian symbol"),
            ("claims", "Packaging claims"),
            ("certifications", "Certification logos"),
        ],
    ),
    (
        "Codes and other text",
        [
            ("barcode", "Barcode contents"),
            ("qr_code", "QR code contents"),
            ("other_text", "Other readable text"),
        ],
    ),
]

FIELDS: list[FieldDef] = [FieldDef(k, label, g) for g, items in FIELD_GROUPS for k, label in items]
FIELD_KEYS: list[str] = [f.key for f in FIELDS]
FIELD_BY_KEY: dict[str, FieldDef] = {f.key: f for f in FIELDS}

_NOT_FOUND = re.compile(
    r"^\s*(not (found|detected|printed|visible|readable)\b.*|n/?a|none|-+|—)\s*$", re.I
)


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip() or bool(_NOT_FOUND.match(value))


def confidence_level(conf: float | None) -> str:
    if conf is None:
        return "Low"
    if conf >= 0.85:
        return "High"
    if conf >= 0.6:
        return "Medium"
    return "Low"


_DATE_PATTERNS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %Y",
    "%B %Y",
    "%m/%Y",
    "%m-%Y",
    "%Y-%m-%d",
]


def parse_date(text: str | None) -> date | None:
    if is_blank(text):
        return None
    assert text is not None
    t = re.sub(
        r"(?i)\b(mfd|mfg|pkd|packed|manufactured|date|of|on|exp|expiry|use by|best before|bb)\b[:.]?",
        " ",
        text,
    )
    t = re.sub(r"\s+", " ", t).strip(" :.-")
    for cand in {
        t,
        *re.findall(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2}", t),
    }:
        for fmt in _DATE_PATTERNS:
            try:
                return datetime.strptime(cand.strip(), fmt).date()
            except ValueError:
                continue
    return None


def ean13_valid(code: str) -> bool:
    digits = re.sub(r"\D", "", code)
    if len(digits) != 13:
        return False
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == int(digits[12])


def validate_field(key: str, value: str | None, today: date | None = None) -> str | None:
    """Return a short validation note when the value looks wrong; None when it is fine/blank."""
    if is_blank(value):
        return None
    assert value is not None
    v = value.strip()
    today = today or date.today()
    if key == "fssai_licence":
        digits = re.sub(r"\D", "", v)
        if len(digits) != 14:
            return f"FSSAI numbers have 14 digits; this reading has {len(digits)}."
    elif key == "mfg_date":
        d = parse_date(v)
        if d is None:
            return "Could not read this as a date."
        if d > today:
            return "Manufacturing date is in the future."
    elif key == "expiry":
        if re.search(r"(?i)\d+\s*(day|month|year)s?\b.*(from|after)", v):
            return None
        d = parse_date(v)
        if d is None:
            return "Could not read this as a date or shelf-life statement."
    elif key == "net_quantity":
        if not re.search(r"(?i)\d+(\.\d+)?\s*(g|gm|gram|kg|mg|ml|l|ltr|litre|liter|pcs|n)\b", v):
            return "No quantity with a unit (g, kg, ml, L) found."
    elif key in ("mrp", "selling_price"):
        if not re.search(r"\d+(\.\d{1,2})?", v):
            return "No amount found."
    elif key == "barcode":
        digits = re.sub(r"\D", "", v)
        if len(digits) == 13 and not ean13_valid(digits):
            return "Barcode check digit does not match (EAN-13)."
    return None


def normalise_quantity(text: str | None) -> str | None:
    """'500 gm' -> '500g', '1 Ltr' -> '1l' for comparison."""
    if is_blank(text):
        return None
    assert text is not None
    m = re.search(r"(?i)(\d+(?:\.\d+)?)\s*(kg|g|gm|gram|grams|mg|ml|l|ltr|litre|liter)\b", text)
    if not m:
        return None
    num, unit = m.group(1), m.group(2).lower()
    unit = {"gm": "g", "gram": "g", "grams": "g", "ltr": "l", "litre": "l", "liter": "l"}.get(
        unit, unit
    )
    n = float(num)
    if unit == "kg":
        n, unit = n * 1000, "g"
    if unit == "l":
        n, unit = n * 1000, "ml"
    return f"{n:g}{unit}"
