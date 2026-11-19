"""Image validation, quality checks, cropping and size handling (D-04).

Originals are never modified. AI/OCR receive the original bytes (or a crop cut from the original);
re-encoding happens only when a provider limit requires it. Only PDF copies are compressed."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

from app.errors import AppError

Image.MAX_IMAGE_PIXELS = 60_000_000  # decompression-bomb guard
ImageFile.LOAD_TRUNCATED_IMAGES = False

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MIN_SIDE = 480
BLUR_THRESHOLD = 60.0


@dataclass
class ImageInput:
    data: bytes
    mime: str
    label: str = ""
    index: int = 0  # 1-based photo number shown to the user


def inspect_upload(data: bytes, max_bytes: int) -> dict[str, Any]:
    """Validate an upload by decoding it (not by trusting the filename/MIME). Returns metadata."""
    if len(data) == 0:
        raise AppError(400, "empty_file", "The file is empty.")
    if len(data) > max_bytes:
        raise AppError(
            413, "file_too_large", f"Photos must be at most {max_bytes // 1_048_576} MB."
        )
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format or ""
            probe.verify()
        with Image.open(io.BytesIO(data)) as raw:
            w, h = _oriented(raw).size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise AppError(415, "unsupported_image", "Upload a JPG, PNG or WebP photograph.") from e
    if fmt not in ALLOWED_FORMATS:
        raise AppError(415, "unsupported_image", "Upload a JPG, PNG or WebP photograph.")
    return {"format": fmt, "content_type": ALLOWED_FORMATS[fmt], "width": w, "height": h}


def _oriented(raw: Image.Image) -> Image.Image:
    out = ImageOps.exif_transpose(raw)
    return out if out is not None else raw


def _gray_array(data: bytes, max_side: int = 1024) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as raw:
        img = _oriented(raw).convert("L")
        img.thumbnail((max_side, max_side))
        return np.asarray(img, dtype=np.float32)


def quality_check(data: bytes, width: int, height: int) -> dict[str, Any]:
    """Blur (variance of Laplacian), brightness and resolution. Warnings never block (REQ-013)."""
    g = _gray_array(data)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    blur = float(lap.var()) if lap.size else 0.0
    brightness = float(g.mean()) if g.size else 0.0
    issues: list[str] = []
    if blur < BLUR_THRESHOLD:
        issues.append("Photo looks blurry — text may be hard to read.")
    if brightness < 55:
        issues.append("Photo is too dark.")
    elif brightness > 235:
        issues.append("Photo is over-exposed (too bright).")
    if min(width, height) < MIN_SIDE:
        issues.append(
            f"Low resolution ({width}×{height}); use at least {MIN_SIDE}px on the short side."
        )
    return {
        "ok": not issues,
        "issues": issues,
        "blur_score": round(blur, 1),
        "brightness": round(brightness, 1),
    }


def apply_crop(data: bytes, mime: str, crop: dict[str, float] | None) -> tuple[bytes, str]:
    """Cut the crop rectangle (fractions) from the original at full resolution."""
    if not crop:
        return data, mime
    with Image.open(io.BytesIO(data)) as raw:
        img = _oriented(raw)
        w, h = img.size
        box = (
            int(crop["x"] * w),
            int(crop["y"] * h),
            int(min(1.0, crop["x"] + crop["w"]) * w),
            int(min(1.0, crop["y"] + crop["h"]) * h),
        )
        out = img.crop(box)
        if out.mode not in ("RGB", "L"):
            out = out.convert("RGB")
        buf = io.BytesIO()
        png = mime == "image/png"
        out.save(buf, format="PNG" if png else "JPEG", quality=95)
        return buf.getvalue(), "image/png" if png else "image/jpeg"


def fit_to_limit(data: bytes, mime: str, max_bytes: int) -> tuple[bytes, str, bool]:
    """Return the original when it fits; otherwise re-encode progressively until it fits.
    The bool reports whether resizing happened (recorded for transparency)."""
    if len(data) <= max_bytes:
        return data, mime, False
    with Image.open(io.BytesIO(data)) as raw:
        img = _oriented(raw).convert("RGB")
        side = max(img.size)
        quality = 90
        while True:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if buf.tell() <= max_bytes or side <= 320:
                return buf.getvalue(), "image/jpeg", True
            if quality > 70:
                quality -= 10
            else:
                side = int(side * 0.8)
                img.thumbnail((side, side))


def compress_for_pdf(data: bytes, max_side: int = 1600, quality: int = 72) -> bytes:
    with Image.open(io.BytesIO(data)) as raw:
        img = _oriented(raw).convert("RGB")
        img.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()


def thumbnail(data: bytes, max_side: int = 480) -> bytes:
    return compress_for_pdf(data, max_side=max_side, quality=70)
