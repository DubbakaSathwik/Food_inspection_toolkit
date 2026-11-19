"""Provider adapters tested against mocked HTTP (request shape + parsing only).
These do NOT prove the real APIs work; the owner verifies with real keys (D-10)."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest

from app.config import get_settings
from app.services.ai import chain
from app.services.ai.base import ProviderError, parse_json, safe_error
from app.services.ai.gemini import GeminiProvider
from app.services.ai.openai_compat import OpenAICompatProvider
from app.services.images import ImageInput, fit_to_limit
from tests.conftest import png_bytes

IMG = ImageInput(png_bytes(), "image/png", "front", 1)


def _patch_client(
    monkeypatch: pytest.MonkeyPatch, module: Any, handler: Any
) -> list[httpx.Request]:
    seen: list[httpx.Request] = []
    real = httpx.AsyncClient

    def factory(*a: Any, **kw: Any) -> httpx.AsyncClient:
        def h(req: httpx.Request) -> httpx.Response:
            seen.append(req)
            return handler(req)  # type: ignore[no-any-return]

        return real(transport=httpx.MockTransport(h))

    monkeypatch.setattr(module.httpx, "AsyncClient", factory)
    return seen


async def test_gemini_extract_sends_original_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai import gemini as mod

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    payload = {
        "category": "snacks",
        "fields": {"brand": {"value": "X", "confidence": 0.9, "photo": 1}},
    }
    seen = _patch_client(
        monkeypatch,
        mod,
        lambda r: httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "```json\n" + json.dumps(payload) + "\n```"}]}}
                ]
            },
        ),
    )
    out = await GeminiProvider().extract([IMG], "prompt")
    assert out["category"] == "snacks" and out["_resized"] is False
    req = seen[0]
    assert req.headers["x-goog-api-key"] == "test-key" and "key=" not in str(req.url)
    body = json.loads(req.content)
    inline = body["contents"][0]["parts"][2]["inline_data"]
    assert base64.b64decode(inline["data"]) == IMG.data  # full-quality original (D-04)


async def test_gemini_chat_web_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai import gemini as mod

    monkeypatch.setattr(get_settings(), "gemini_api_key", "k")
    seen = _patch_client(
        monkeypatch,
        mod,
        lambda r: httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Answer"}]},
                        "groundingMetadata": {
                            "groundingChunks": [
                                {"web": {"uri": "https://fssai.gov.in/x", "title": "FSSAI"}}
                            ]
                        },
                    }
                ]
            },
        ),
    )
    res = await GeminiProvider().chat("sys", [{"role": "user", "text": "q"}], web=True)
    assert res.sources == [{"title": "FSSAI", "url": "https://fssai.gov.in/x"}]
    assert json.loads(seen[0].content)["tools"] == [{"google_search": {}}]
    res = await GeminiProvider().chat("sys", [{"role": "user", "text": "q"}], web=False)
    assert "tools" not in json.loads(seen[1].content)


async def test_gemini_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai import gemini as mod

    monkeypatch.setattr(get_settings(), "gemini_api_key", "k")
    _patch_client(monkeypatch, mod, lambda r: httpx.Response(429, json={}))
    with pytest.raises(ProviderError, match="HTTP 429"):
        await GeminiProvider().extract([IMG], "p")


async def test_openai_compat_single_image_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai import openai_compat as mod

    answers = iter(
        [
            {"fields": {"brand": {"value": "A", "confidence": 0.5}}, "category": "dairy"},
            {"fields": {"brand": {"value": "B", "confidence": 0.9}}},
        ]
    )
    seen = _patch_client(
        monkeypatch,
        mod,
        lambda r: httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(next(answers))}}]}
        ),
    )
    p = OpenAICompatProvider("nvidia", "key", "https://x.test/v1", "m", 4096, single_image=True)
    out = await p.extract([IMG, ImageInput(png_bytes(), "image/png", "back", 2)], "p")
    assert out["fields"]["brand"]["value"] == "B" and out["category"] == "dairy"
    assert seen[0].headers["authorization"] == "Bearer key"
    with pytest.raises(ProviderError):
        await p.compare([IMG], [IMG], "p")


async def test_chain_skips_unconfigured_and_records_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "ai_provider_order", "gemini,nvidia,fake")
    monkeypatch.setattr(get_settings(), "gemini_api_key", None)
    monkeypatch.setattr(get_settings(), "nvidia_api_key", None)
    res = await chain.run_extract([IMG], "p", allow_ocr=True)
    assert res.provider == "fake"
    assert [a["provider"] for a in res.attempts] == ["gemini", "nvidia", "fake"]
    status = chain.provider_status()
    assert [s["configured"] for s in status] == [False, False, True]


async def test_chain_ocr_unavailable_then_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "ai_provider_order", "fake_fail")
    res = await chain.run_extract([IMG], "p", allow_ocr=True)
    assert res.data is None and [a["provider"] for a in res.attempts] == ["fake_fail", "ocr"]
    assert "not available" in res.attempts[-1]["error"]


async def test_fake_provider_refused_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "app_env", "production")
    monkeypatch.setattr(get_settings(), "ai_provider_order", "fake")
    assert chain.build_providers() == []


def test_helpers() -> None:
    assert parse_json('noise {"a": 1} trailing') == {"a": 1}
    with pytest.raises(ProviderError):
        parse_json("no json")
    assert "***" in safe_error(Exception("failed key=abc123&x"))
    big = png_bytes(size=(1800, 1800))
    same, _, resized = fit_to_limit(big, "image/png", len(big) + 1)
    assert same == big and resized is False
    small, mime, resized = fit_to_limit(big, "image/png", 60_000)
    assert resized and mime == "image/jpeg" and len(small) <= 60_000


async def test_fake_provider_fail_marker() -> None:
    from app.services.ai.fake import FAIL_MARKER, FakeProvider

    with pytest.raises(ProviderError):
        await FakeProvider().extract(
            [ImageInput(png_bytes() + FAIL_MARKER, "image/png", "front", 1)], "p"
        )
    assert (await FakeProvider().extract([IMG], "p"))["fields"]


async def test_transient_503_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai import base
    from app.services.ai import gemini as mod

    monkeypatch.setattr(base, "RETRY_DELAYS", (0.0, 0.0))
    monkeypatch.setattr(get_settings(), "gemini_api_key", "k")
    calls = {"n": 0}

    def handler(r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, json={"error": {"message": "high demand"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})

    _patch_client(monkeypatch, mod, handler)
    res = await GeminiProvider().chat("s", [{"role": "user", "text": "q"}], web=False)
    assert res.text == "OK" and calls["n"] == 3


async def test_persistent_503_reports_provider_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ai import base
    from app.services.ai import gemini as mod

    monkeypatch.setattr(base, "RETRY_DELAYS", (0.0,))
    monkeypatch.setattr(get_settings(), "gemini_api_key", "k")
    _patch_client(
        monkeypatch, mod, lambda r: httpx.Response(503, json={"error": {"message": "high demand"}})
    )
    with pytest.raises(ProviderError, match="HTTP 503 — high demand"):
        await GeminiProvider().extract([IMG], "p")


async def test_reasoning_model_think_block_removed_and_cutoff_explained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.ai import openai_compat as mod

    monkeypatch.setattr(get_settings(), "nvidia_api_key", "k")
    state: dict[str, Any] = {"cut_off": False, "max_tokens": 0}

    def handler(r: httpx.Request) -> httpx.Response:
        state["max_tokens"] = json.loads(r.content)["max_tokens"]
        if state["cut_off"]:
            msg = {"message": {"content": None}, "finish_reason": "length"}
        else:
            content = '<think>maybe {"x": 1}</think>{"fields": {}}'
            msg = {"message": {"content": content}}
        return httpx.Response(200, json={"choices": [msg]})

    _patch_client(monkeypatch, mod, handler)
    p = mod.nvidia()
    p.model = "nvidia/some-reasoning-model"
    assert (await p.extract([IMG], "p")) == {"fields": {}}
    assert state["max_tokens"] >= 8192
    state["cut_off"] = True
    with pytest.raises(ProviderError, match="used all its tokens"):
        await p.extract([IMG], "p")
