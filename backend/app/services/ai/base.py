from __future__ import annotations

import asyncio
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


def http_error(r: Any) -> ProviderError:
    """ProviderError for a non-200 response, including the provider's own reason (no secrets)."""
    reason = ""
    try:
        body = r.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        err = body.get("error", body)
        if isinstance(err, dict):
            reason = str(err.get("message") or err.get("detail") or err.get("title") or "")
        else:
            reason = str(err or body.get("detail") or body.get("title") or "")
    elif isinstance(body, str):
        reason = body
    reason = re.sub(r"\s+", " ", reason).strip()
    return ProviderError(f"HTTP {r.status_code}" + (f" — {reason[:110]}" if reason else ""))


TRANSIENT_STATUS = {500, 502, 503, 504}
RETRY_DELAYS: tuple[float, ...] = (2.0, 5.0)  # seconds between attempts; overridden in tests


async def post_with_retry(client: Any, url: str, **kwargs: Any) -> Any:
    """POST, retrying a few times when the provider reports a temporary overload (5xx)."""
    r = await client.post(url, **kwargs)
    for delay in RETRY_DELAYS:
        if r.status_code not in TRANSIENT_STATUS:
            break
        await asyncio.sleep(delay)
        r = await client.post(url, **kwargs)
    return r
