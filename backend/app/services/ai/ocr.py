"""Optional PaddleOCR fallback (D-06). Installed with `uv sync --extra ocr`; disabled on Render.
Text is parsed with conservative regexes into low-confidence fields for the inspector to verify."""

from __future__ import annotations

import io
import re
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.services.ai.base import ProviderError
from app.services.images import ImageInput

_engine: Any = None


def available() -> bool:
    if not get_settings().ocr_enabled:
        return False
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        return False
    return True


def _get_engine() -> Any:
    global _engine
    if _engine is None:
        from paddleocr import PaddleOCR

        _engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _engine


def _read_text(data: bytes) -> list[str]:
    import numpy as np
    from PIL import Image

    img = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
    result = _get_engine().ocr(img, cls=True) or []
    lines: list[str] = []
    for page in result:
        for item in page or []:
            lines.append(str(item[1][0]))
    return lines


PATTERNS: dict[str, re.Pattern[str]] = {
    "fssai_licence": re.compile(r"(?i)(?:fssai|lic(?:\.|ence|ense)?\s*no)[^0-9]{0,12}(\d{14})"),
    "mrp": re.compile(r"(?i)M\.?R\.?P\.?[^0-9]{0,12}([0-9]+(?:\.[0-9]{1,2})?)"),
    "net_quantity": re.compile(
        r"(?i)net\s*(?:qty|quantity|wt|weight|vol)?[.:\s]*([0-9.]+\s*(?:kg|g|gm|ml|l|ltr))"
    ),
    "batch": re.compile(r"(?i)(?:batch|lot)\s*(?:no\.?|number)?[:.\s]*([A-Z0-9-]{3,20})"),
    "mfg_date": re.compile(
        r"(?i)(?:mfg|mfd|pkd|manufactured)[^0-9]{0,15}(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}[/.-]\d{4})"
    ),
    "expiry": re.compile(r"(?i)((?:best before|use by|exp(?:iry)?)[^\n]{0,40})"),
    "barcode": re.compile(r"\b(\d{13})\b"),
}


async def extract(images: list[ImageInput]) -> dict[str, Any]:
    if not available():
        raise ProviderError("OCR fallback not available (disabled or not installed)")
    fields: dict[str, Any] = {}
    for img in images:
        lines = await run_in_threadpool(_read_text, img.data)
        text = "\n".join(lines)
        for key, rx in PATTERNS.items():
            if key in fields:
                continue
            m = rx.search(text)
            if m:
                fields[key] = {
                    "value": m.group(1).strip(),
                    "confidence": 0.45,
                    "photo": img.index,
                    "note": "Read by OCR fallback — please verify.",
                }
        if "other_text" not in fields and text:
            fields["other_text"] = {
                "value": text[:1500],
                "confidence": 0.4,
                "photo": img.index,
                "note": "Raw OCR text.",
            }
    if not fields:
        raise ProviderError("OCR found no readable text")
    return {"category": None, "fields": fields}
