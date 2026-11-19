"""Deterministic provider for tests and local demos without keys (D-10).
Refused when APP_ENV=production. All values are fictional and labelled as test output."""

from __future__ import annotations

from typing import Any

from app.services.ai.base import ChatResult, ProviderError
from app.services.images import ImageInput

FAKE_FIELDS: dict[str, tuple[str | None, float, int | None]] = {
    "product_name": ("Whole Grain Muesli — Nut & Seed Mix", 0.95, 1),
    "brand": ("Harvest Lane", 0.96, 1),
    "variant": ("Nut & Seed Mix", 0.9, 1),
    "manufacturer_name": ("Harvest Lane Foods Pvt. Ltd.", 0.92, 2),
    "manufacturer_address": ("Plot 14, MIDC Ambad, Nashik, Maharashtra 422010", 0.74, 2),
    "fssai_licence": ("10012022001234", 0.78, 2),
    "customer_care": ("1800-000-0000 / care@harvestlane.example", 0.7, 2),
    "mfg_date": ("12/09/2026", 0.55, 2),
    "expiry": ("Best before 9 months from manufacture", 0.72, 2),
    "batch": ("HL-0926-B", 0.7, 2),
    "net_quantity": ("500 g", 0.95, 1),
    "mrp": ("245.00 (incl. of all taxes)", 0.9, 2),
    "selling_price": (None, 0.2, None),
    "ingredients": (
        "Rolled oats (42%), wheat flakes, cane sugar, almonds (6%), cashews (4%), "
        "sunflower seeds, raisins, honey, salt",
        0.75,
        2,
    ),
    "nutrition": (
        "Energy 389 kcal; Protein 10.2 g; Carbohydrate 62.4 g; Total sugars 14.1 g; "
        "Fat 10.8 g; per 100 g",
        0.73,
        2,
    ),
    "allergens": (None, 0.3, None),
    "veg_symbol": ("Vegetarian (green dot)", 0.93, 1),
    "claims": ("High in fibre; Supports heart health; No added preservatives", 0.8, 1),
    "certifications": ("Recyclable mark; green dot", 0.5, 1),
    "barcode": ("8901234567890", 0.9, 1),
    "qr_code": (None, 0.2, None),
    "other_text": ("Store in a cool, dry place away from sunlight", 0.7, 1),
}


class FakeProvider:
    supports_web = True

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.name = "fake_fail" if fail else "fake"

    def configured(self) -> bool:
        return True

    def _maybe_fail(self) -> None:
        if self.fail:
            raise ProviderError("simulated provider failure")

    async def extract(self, images: list[ImageInput], prompt: str) -> dict[str, Any]:
        self._maybe_fail()
        n = len(images)
        fields = {
            k: {
                "value": v,
                "confidence": c,
                "photo": (min(p, n) if p else None),
                "note": None if v else "Not found on photographs",
            }
            for k, (v, c, p) in FAKE_FIELDS.items()
        }
        return {"category": "staples", "category_confidence": 0.8, "fields": fields}

    async def compare(
        self, uploaded: list[ImageInput], reference: list[ImageInput], prompt: str
    ) -> dict[str, Any]:
        self._maybe_fail()
        return {
            "summary": "Test provider: layout broadly consistent with the reference.",
            "observations": [
                {
                    "area": "Brand logo",
                    "observation": "Logo colour appears slightly lighter than the reference.",
                    "severity": "info",
                    "photo": 1,
                },
            ],
        }

    async def chat(self, system: str, messages: list[dict[str, str]], web: bool) -> ChatResult:
        self._maybe_fail()
        q = messages[-1]["text"] if messages else ""
        text = (
            "[Test provider — not a real AI answer] I received your question: "
            f'"{q[:200]}". Configure GEMINI_API_KEY for real answers. '
            "I cannot verify regulatory information in test mode."
        )
        sources = (
            [{"title": "FSSAI (test source)", "url": "https://www.fssai.gov.in/"}] if web else []
        )
        return ChatResult(text=text, sources=sources, provider=self.name, web_used=web)
