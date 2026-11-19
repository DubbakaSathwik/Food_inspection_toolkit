"""Seed fictional demo reference records and demo compliance rules (labelled Demo; idempotent upserts).

All names, addresses and licence numbers are FICTIONAL. Regulatory references name the published
regulations the demo rules are derived from; the owner must verify the exact wording (U-03)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

NOW = datetime(2026, 11, 1, tzinfo=UTC)
LAB = "FSS (Labelling & Display) Regulations, 2020"
CLM = "FSS (Advertising & Claims) Regulations, 2018"


def _ref(
    i: int,
    name: str,
    brand: str,
    variant: str,
    cat: str,
    qty: str,
    sizes: list[str],
    gtin: str,
    mfr: str,
    addr: str,
    state: str,
    district: str,
    lic: str,
    lic_status: str = "active",
    valid_until: str = "2028-03-31",
) -> dict[str, Any]:
    return {
        "_id": f"REF-{i:04d}",
        "product_name": name,
        "brand": brand,
        "variant": variant,
        "category": cat,
        "net_quantity": qty,
        "package_sizes": sizes,
        "gtin": gtin,
        "manufacturer": {
            "name": mfr,
            "registered_address": addr,
            "facility_address": addr,
            "state": state,
            "district": district,
            "contact": "1800-000-0000 (demo)",
        },
        "licence": {
            "number": lic,
            "valid_from": "2023-04-01",
            "valid_until": valid_until,
            "status": lic_status,
            "fbo_category": "Manufacturer",
        },
        "notes": "Fictional demo record.",
        "source": "manual",
        "status": "active",
        "demo": True,
        "packaging_versions": [],
        "created_by": "seed",
        "created_at": NOW,
        "updated_at": NOW,
    }


REFERENCES = [
    _ref(
        1,
        "Whole Grain Muesli — Nut & Seed Mix",
        "Harvest Lane",
        "Nut & Seed Mix",
        "staples",
        "500 g",
        ["500 g", "1 kg"],
        "8901234567890",
        "Harvest Lane Foods Pvt. Ltd.",
        "Plot 14, MIDC Ambad, Nashik, Maharashtra 422010",
        "Maharashtra",
        "Nashik",
        "10012022001234",
    ),
    _ref(
        2,
        "Spring Water",
        "Tarangini",
        "Natural mineral",
        "beverages",
        "1 L",
        ["500 ml", "1 L"],
        "8901111222233",
        "Tarangini Beverages Pvt. Ltd.",
        "Survey 22, Industrial Area, Dehradun, Uttarakhand 248001",
        "Uttarakhand",
        "Dehradun",
        "10019011000456",
    ),
    _ref(
        3,
        "Masala Peanuts",
        "Crunchory",
        "Masala",
        "snacks",
        "150 g",
        ["150 g", "400 g"],
        "8902222333344",
        "Crunchory Snacks LLP",
        "Unit 7, GIDC Estate, Rajkot, Gujarat 360003",
        "Gujarat",
        "Rajkot",
        "10717999000789",
        lic_status="expired",
        valid_until="2025-12-31",
    ),
    _ref(
        4,
        "Toned Milk",
        "Milkora",
        "Toned",
        "dairy",
        "500 ml",
        ["500 ml", "1 L"],
        "8903333444455",
        "Milkora Dairy Co-operative (Demo)",
        "Dairy Road, Anand, Gujarat 388001",
        "Gujarat",
        "Anand",
        "10012099000321",
    ),
    _ref(
        5,
        "Basmati Rice",
        "Granara",
        "Premium",
        "staples",
        "5 kg",
        ["1 kg", "5 kg"],
        "8904444555566",
        "Granara Agro Foods Pvt. Ltd.",
        "GT Road, Karnal, Haryana 132001",
        "Haryana",
        "Karnal",
        "10816005000654",
        lic_status="suspended",
    ),
]


def _rule(
    code: str,
    title: str,
    cat: str,
    check: str,
    field: str,
    req: str,
    sev: str = "warning",
    ref: str = LAB,
    pattern: str | None = None,
    keywords: list[str] | None = None,
    status: str = "active",
) -> dict[str, Any]:
    return {
        "code": code,
        "title": title,
        "category": cat,
        "check_type": check,
        "field": field,
        "pattern": pattern,
        "keywords": keywords or [],
        "severity": sev,
        "requirement": req,
        "reference": ref,
        "status": status,
        "notes": "Demo rule — wording and reference to be verified by the owner.",
        "version": 1,
        "demo": True,
        "created_at": NOW,
        "updated_at": NOW,
        "history": [
            {"version": 1, "at": NOW, "by": "seed", "note": "Seeded demo rule", "changes": {}}
        ],
    }


RULES = [
    _rule(
        "DR-GN-01",
        "FSSAI licence / registration number",
        "all",
        "required_field",
        "fssai_licence",
        "The label should show the FSSAI licence or registration number.",
        "high",
    ),
    _rule(
        "DR-GN-02",
        "Manufacturer name",
        "all",
        "required_field",
        "manufacturer_name",
        "The label should name the manufacturer, packer or marketer.",
    ),
    _rule(
        "DR-GN-03",
        "Manufacturer address",
        "all",
        "required_field",
        "manufacturer_address",
        "The label should give the complete address of the manufacturer.",
    ),
    _rule(
        "DR-GN-04",
        "Batch / lot number",
        "all",
        "required_field",
        "batch",
        "The label should show a batch, lot or code number.",
    ),
    _rule(
        "DR-GN-05",
        "Maximum retail price",
        "all",
        "required_field",
        "mrp",
        "The label should show the MRP (inclusive of all taxes).",
    ),
    _rule(
        "DR-GN-06",
        "Ingredients list",
        "all",
        "required_field",
        "ingredients",
        "The label should list ingredients (where applicable).",
    ),
    _rule(
        "DR-GN-07",
        "Customer care details",
        "all",
        "required_field",
        "customer_care",
        "The label should give consumer-care contact details.",
        "info",
    ),
    _rule(
        "DR-FS-04",
        "Net quantity declaration",
        "staples",
        "required_field",
        "net_quantity",
        "Net quantity must be declared with a unit of weight or volume.",
    ),
    _rule(
        "DR-FS-09",
        "Allergen declaration",
        "staples",
        "required_field",
        "allergens",
        "Allergens present (e.g. nuts, gluten) should be declared.",
    ),
    _rule(
        "DR-FS-11",
        "Nutritional information panel",
        "staples",
        "required_field",
        "nutrition",
        "Nutritional information per 100 g should be shown.",
    ),
    _rule(
        "DR-DY-02",
        "Date of manufacture and use-by",
        "dairy",
        "date_not_expired",
        "expiry",
        "Use-by / expiry date must be shown and not passed on the inspection date.",
        "high",
    ),
    _rule(
        "DR-DY-06",
        "Storage temperature statement",
        "dairy",
        "pattern",
        "other_text",
        "Dairy products should state storage conditions (e.g. 'Store below 5°C').",
        pattern=r"(store|keep|refrigerat).*(°c|deg|cool|refrigerat)",
    ),
    _rule(
        "DR-BV-03",
        "Packaged water source declaration",
        "beverages",
        "pattern",
        "other_text",
        "Packaged water should declare its source.",
        pattern=r"source|spring|natural mineral",
    ),
    _rule(
        "DR-SN-05",
        "Veg / non-veg symbol",
        "snacks",
        "required_field",
        "veg_symbol",
        "The vegetarian / non-vegetarian symbol should be displayed.",
    ),
    _rule(
        "DR-SN-06",
        "Manufacturing date",
        "snacks",
        "required_field",
        "mfg_date",
        "The date of manufacture or packing should be shown.",
    ),
    _rule(
        "DR-CL-03",
        "Health and nutrition claims",
        "all",
        "claim_keywords",
        "claims",
        "Health or nutrition claims need substantiation and must not be misleading.",
        ref=CLM,
        keywords=[
            "heart health",
            "immunity",
            "boosts",
            "cures",
            "clinically",
            "doctor recommended",
            "high in",
        ],
    ),
    _rule(
        "DR-CL-07",
        "Organic and natural claims",
        "all",
        "claim_keywords",
        "claims",
        "'Natural' / 'organic' / '100% pure' claims must meet the conditions for their use.",
        ref=CLM,
        keywords=["organic", "natural", "100% pure", "chemical free"],
        status="draft",
    ),
]


async def up(db: AsyncDatabase) -> None:  # type: ignore[type-arg]
    for r in REFERENCES:
        await db["reference_records"].update_one(
            {"_id": r["_id"]}, {"$setOnInsert": r}, upsert=True
        )
    await db["counters"].update_one(
        {"_id": "reference-0"}, {"$max": {"seq": len(REFERENCES)}}, upsert=True
    )
    for r in RULES:
        await db["compliance_rules"].update_one(
            {"code": r["code"]}, {"$setOnInsert": r}, upsert=True
        )
