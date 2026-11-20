from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.services import classification, compliance, matching
from app.services.fields import ean13_valid, normalise_quantity, parse_date, validate_field

REC: dict[str, Any] = {
    "_id": "REF-9000",
    "brand": "Harvest Lane",
    "product_name": "Whole Grain Muesli",
    "variant": "Nut Mix",
    "net_quantity": "500 g",
    "package_sizes": ["500 g", "1 kg"],
    "gtin": "8901234567890",
    "manufacturer": {
        "name": "Harvest Lane Foods Pvt. Ltd.",
        "facility_address": "Plot 14, MIDC Ambad, Nashik",
    },
    "licence": {"number": "10012022001234", "status": "active", "valid_until": "2030-01-01"},
}
VALS: dict[str, str | None] = {
    "brand": "HARVEST  LANE",
    "product_name": "Whole grain muesli",
    "variant": "Nut mix",
    "net_quantity": "500gm",
    "manufacturer_name": "Harvest Lane Foods Private Limited",
    "manufacturer_address": "Plot 14 MIDC Ambad Nashik",
    "fssai_licence": "100 120 220 01234",
    "barcode": "8901234567890",
}


def test_field_validation() -> None:
    assert validate_field("fssai_licence", "123") is not None
    assert validate_field("fssai_licence", "10012022001234") is None
    assert (
        validate_field("mfg_date", "01/01/2099", date(2026, 1, 1))
        == "Manufacturing date is in the future."
    )
    assert validate_field("expiry", "Best before 9 months from manufacture") is None
    assert validate_field("net_quantity", "five hundred") is not None
    assert parse_date("MFG 12/09/2026") == date(2026, 9, 12)
    assert ean13_valid("8901234567890") and not ean13_valid("8901234567892")
    assert normalise_quantity("1 Ltr") == "1000ml" and normalise_quantity("0.5 kg") == "500g"


def test_match_exact_case_spacing_tolerant() -> None:
    res = matching.match(VALS, [REC])
    assert res["status"] == "exact", res


def test_match_mismatch_on_licence() -> None:
    res = matching.match({**VALS, "fssai_licence": "99999999999999"}, [REC])
    assert res["status"] == "mismatch"


def test_match_partial_and_none_and_insufficient() -> None:
    assert (
        matching.match({**VALS, "manufacturer_address": "Somewhere else entirely, Kolkata"}, [REC])[
            "status"
        ]
        == "partial"
    )
    assert (
        matching.match({"brand": "Zebra", "product_name": "Cola"}, [REC])["status"] == "no_record"
    )
    assert matching.match({}, [REC])["status"] == "insufficient"


def test_licence_check_statuses() -> None:
    assert matching.licence_check(None, [], None)["status"] == "missing"
    assert matching.licence_check("123", [], None)["status"] == "invalid_format"
    assert matching.licence_check("10012022001234", [], None)["status"] == "not_found"
    assert (
        matching.licence_check("10012022001234", [REC], "Harvest Lane Foods")["status"] == "found"
    )
    exp = {**REC, "licence": {**REC["licence"], "valid_until": "2020-01-01"}}
    assert matching.licence_check("10012022001234", [exp], None)["status"] == "expired"
    sus = {**REC, "licence": {**REC["licence"], "status": "suspended"}}
    assert matching.licence_check("10012022001234", [sus], None)["status"] == "suspended"
    assert (
        matching.licence_check("10012022001234", [REC], "Totally Different Corp")["status"]
        == "needs_review"
    )


def test_compliance_rules() -> None:
    rules = [
        {
            "code": "A",
            "title": "Allergen",
            "category": "all",
            "check_type": "required_field",
            "field": "allergens",
            "requirement": "r",
            "severity": "warning",
        },
        {
            "code": "B",
            "title": "Claims",
            "category": "all",
            "check_type": "claim_keywords",
            "field": "claims",
            "keywords": ["heart health"],
            "requirement": "r",
            "severity": "warning",
        },
        {
            "code": "C",
            "title": "Storage",
            "category": "dairy",
            "check_type": "pattern",
            "field": "other_text",
            "pattern": r"store.*°c",
            "requirement": "r",
            "severity": "info",
        },
        {
            "code": "D",
            "title": "Expiry",
            "category": "dairy",
            "check_type": "date_not_expired",
            "field": "expiry",
            "requirement": "r",
            "severity": "high",
        },
    ]
    res = {
        r["rule_code"]: r["result"]
        for r in compliance.evaluate(
            rules,
            {
                "allergens": None,
                "claims": "Supports heart health",
                "other_text": "Store below 5°C",
                "expiry": "01/01/2020",
            },
            date(2026, 1, 1),
        )
    }
    assert res == {"A": "fail", "B": "review", "C": "pass", "D": "fail"}


def test_classification_suggestion() -> None:
    hi = {
        "id": "x",
        "title": "Licence",
        "severity": "high",
        "status_label": "Expired",
        "decision": None,
    }
    warn = {
        "id": "y",
        "title": "Allergen",
        "severity": "warning",
        "status_label": "Missing",
        "decision": None,
    }
    assert classification.suggest([hi], "exact")["classification"] == "suspicious"
    assert classification.suggest([], "exact")["classification"] == "verified"
    assert classification.suggest([warn], "exact")["classification"] == "not_verified"
    dismissed = {**hi, "decision": {"action": "dismissed"}}
    assert classification.suggest([dismissed], "exact")["classification"] == "verified"


async def test_migrations_idempotent() -> None:
    from app.db import get_db
    from migrations.runner import discover

    for mod in discover():
        await mod.up(get_db())  # running again must not fail or duplicate
    assert await get_db()["reference_records"].count_documents({"_id": "REF-0001"}) == 1
    assert await get_db()["compliance_rules"].count_documents({"code": "DR-GN-01"}) == 1


async def test_validator_rejects_bad_document() -> None:
    import pytest
    from pymongo.errors import WriteError

    from app.db import get_db

    with pytest.raises(WriteError):
        await get_db()["inspections"].insert_one(
            {"_id": "bad", "owner_uid": "x", "status": "weird"}
        )


async def test_demo_seed_migration_is_explicit_only_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new production database must not receive fictional demo data unless ALLOW_DEMO_SEED=true."""
    from types import SimpleNamespace

    from app.config import get_settings
    from migrations import m0003_seed_demo as seed

    touched: list[str] = []

    class Col:
        async def update_one(self, *a: object, **k: object) -> None:
            touched.append("write")

    class Db:
        def __getitem__(self, name: str) -> Col:
            return Col()

    monkeypatch.setattr(get_settings(), "app_env", "production")
    monkeypatch.delenv("ALLOW_DEMO_SEED", raising=False)
    await seed.up(Db())  # type: ignore[arg-type]
    assert touched == []
    monkeypatch.setenv("ALLOW_DEMO_SEED", "true")
    await seed.up(Db())  # type: ignore[arg-type]
    assert touched, "explicit opt-in must still seed"
    del SimpleNamespace
