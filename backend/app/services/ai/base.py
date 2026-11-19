from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.services.images import ImageInput


class ProviderError(Exception):
    """A provider could not produce a usable answer (network, quota, bad JSON…)."""


@dataclass
class ChatResult:
    text: str
    sources: list[dict[str, str]] = field(default_factory=list)
    provider: str = ""
    web_used: bool = False


class Provider(Protocol):
    name: str
    supports_web: bool

    def configured(self) -> bool: ...

    async def extract(self, images: list[ImageInput], prompt: str) -> dict[str, Any]: ...

    async def compare(
        self, uploaded: list[ImageInput], reference: list[ImageInput], prompt: str
    ) -> dict[str, Any]: ...

    async def chat(self, system: str, messages: list[dict[str, str]], web: bool) -> ChatResult: ...


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


def parse_json(text: str) -> dict[str, Any]:
    t = _FENCE.sub("", text.strip())
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < start:
        raise ProviderError("response was not JSON")
    try:
        obj = json.loads(t[start : end + 1])
    except json.JSONDecodeError as e:
        raise ProviderError("response JSON could not be parsed") from e
    if not isinstance(obj, dict):
        raise ProviderError("response JSON is not an object")
    return obj


def safe_error(e: Exception) -> str:
    """Short, secret-free description for attempt logs shown to users."""
    msg = str(e)
    msg = re.sub(r"key=[^&\s]+", "key=***", msg)
    msg = re.sub(r"(?i)(bearer|api[-_ ]?key)[:= ]+\S+", r"\1 ***", msg)
    return f"{type(e).__name__}: {msg[:160]}"
