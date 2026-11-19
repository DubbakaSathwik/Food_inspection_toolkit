"""Provider chain: primary → backup → (extraction only) OCR fallback (D-05)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config import get_settings
from app.repositories.base import now
from app.services.ai import ocr
from app.services.ai.base import ChatResult, Provider, ProviderError, safe_error
from app.services.ai.fake import FakeProvider
from app.services.ai.gemini import GeminiProvider
from app.services.ai.openai_compat import huggingface, nvidia
from app.services.images import ImageInput

log = logging.getLogger("crate_scan.ai")


def build_providers() -> list[Provider]:
    s = get_settings()
    out: list[Provider] = []
    for name in s.provider_order:
        if name == "gemini":
            out.append(GeminiProvider())
        elif name == "nvidia":
            out.append(nvidia())
        elif name == "huggingface":
            out.append(huggingface())
        elif name in ("fake", "fake_fail"):
            if s.is_production:
                log.warning("fake AI provider ignored in production")
                continue
            out.append(FakeProvider(fail=name == "fake_fail"))
    return out


def provider_status() -> list[dict[str, Any]]:
    s = get_settings()
    models = {"gemini": s.gemini_model, "nvidia": s.nvidia_model, "huggingface": s.hf_model}
    return [
        {
            "name": p.name,
            "configured": p.configured(),
            "model": models.get(p.name),
            "position": i + 1,
        }
        for i, p in enumerate(build_providers())
    ]


@dataclass
class ChainResult:
    data: dict[str, Any] | None
    provider: str | None
    attempts: list[dict[str, Any]] = field(default_factory=list)
    ocr_used: bool = False


async def run_extract(images: list[ImageInput], prompt: str, allow_ocr: bool) -> ChainResult:
    attempts: list[dict[str, Any]] = []
    for p in build_providers():
        if not p.configured():
            attempts.append(
                {"provider": p.name, "ok": False, "error": "not configured", "at": now()}
            )
            continue
        try:
            data = await p.extract(images, prompt)
            attempts.append({"provider": p.name, "ok": True, "error": None, "at": now()})
            return ChainResult(data, p.name, attempts)
        except ProviderError as e:
            attempts.append({"provider": p.name, "ok": False, "error": safe_error(e), "at": now()})
        except Exception as e:  # provider bugs must not lose the inspection (NFR-03)
            log.exception("provider %s crashed", p.name)
            attempts.append({"provider": p.name, "ok": False, "error": safe_error(e), "at": now()})
    if allow_ocr:
        try:
            data = await ocr.extract(images)
            attempts.append({"provider": "ocr", "ok": True, "error": None, "at": now()})
            return ChainResult(data, "ocr", attempts, ocr_used=True)
        except ProviderError as e:
            attempts.append({"provider": "ocr", "ok": False, "error": safe_error(e), "at": now()})
        except Exception as e:
            log.exception("ocr crashed")
            attempts.append({"provider": "ocr", "ok": False, "error": safe_error(e), "at": now()})
    return ChainResult(None, None, attempts)


async def run_compare(
    uploaded: list[ImageInput], reference: list[ImageInput], prompt: str
) -> ChainResult:
    attempts: list[dict[str, Any]] = []
    for p in build_providers():
        if not p.configured():
            continue
        try:
            data = await p.compare(uploaded, reference, prompt)
            attempts.append({"provider": p.name, "ok": True, "error": None, "at": now()})
            return ChainResult(data, p.name, attempts)
        except Exception as e:
            attempts.append({"provider": p.name, "ok": False, "error": safe_error(e), "at": now()})
    return ChainResult(None, None, attempts)


async def run_chat(system: str, messages: list[dict[str, str]], web: bool) -> ChatResult:
    errors: list[str] = []
    for p in build_providers():
        if not p.configured() or (web and not p.supports_web):
            continue
        try:
            return await p.chat(system, messages, web)
        except Exception as e:
            errors.append(f"{p.name}: {safe_error(e)}")
    if web:
        raise ProviderError(
            "Internet research is unavailable right now (needs a working Gemini key)."
        )
    raise ProviderError("The assistant is unavailable right now. " + "; ".join(errors)[:300])
