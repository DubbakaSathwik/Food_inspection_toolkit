"""Google Gemini via REST (generateContent). Web research uses the google_search grounding tool."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from app.config import get_settings
from app.services.ai.base import ChatResult, ProviderError, parse_json
from app.services.images import ImageInput, fit_to_limit


class GeminiProvider:
    name = "gemini"
    supports_web = True

    def __init__(self) -> None:
        self.s = get_settings()

    def configured(self) -> bool:
        return bool(self.s.gemini_api_key)

    def _images_parts(self, images: list[ImageInput]) -> tuple[list[dict[str, Any]], bool]:
        # Inline request limit (~20 MB incl. base64 overhead): send originals unless they do not fit.
        budget = int(self.s.gemini_max_request_mb * 1_048_576 * 0.74)
        per_image = max(budget // max(len(images), 1), 512 * 1024)
        parts: list[dict[str, Any]] = []
        resized = False
        total = sum(len(i.data) for i in images)
        for img in images:
            data, mime = img.data, img.mime
            if total > budget:
                data, mime, r = fit_to_limit(data, mime, per_image)
                resized = resized or r
            parts.append({"text": f"Photo {img.index} ({img.label or 'unlabelled'}):"})
            parts.append(
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}
            )
        return parts, resized

    async def _call(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.s.gemini_base_url}/models/{self.s.gemini_model}:generateContent"
        headers = {
            "x-goog-api-key": self.s.gemini_api_key or "",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.s.ai_timeout_seconds) as client:
                r = await client.post(url, json=body, headers=headers)
        except httpx.HTTPError as e:
            raise ProviderError(f"network error ({type(e).__name__})") from e
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        data: dict[str, Any] = r.json()
        if not data.get("candidates"):
            raise ProviderError("no candidates (blocked or empty)")
        return data

    @staticmethod
    def _text(data: dict[str, Any]) -> str:
        parts = data["candidates"][0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)

    async def extract(self, images: list[ImageInput], prompt: str) -> dict[str, Any]:
        parts, resized = self._images_parts(images)
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}, *parts]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
        out = parse_json(self._text(await self._call(body)))
        out["_resized"] = resized
        return out

    async def compare(
        self, uploaded: list[ImageInput], reference: list[ImageInput], prompt: str
    ) -> dict[str, Any]:
        up, _ = self._images_parts(uploaded)
        ref, _ = self._images_parts(reference)
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"text": "UPLOADED (inspected) photographs:"},
                        *up,
                        {"text": "REFERENCE packaging photographs:"},
                        *ref,
                    ],
                }
            ],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
        return parse_json(self._text(await self._call(body)))

    async def chat(self, system: str, messages: list[dict[str, str]], web: bool) -> ChatResult:
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["text"]}],
            }
            for m in messages
        ]
        body: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.3},
        }
        if web:
            body["tools"] = [{"google_search": {}}]
        data = await self._call(body)
        text = self._text(data).strip()
        if not text:
            raise ProviderError("empty answer")
        sources: list[dict[str, str]] = []
        meta = data["candidates"][0].get("groundingMetadata") or {}
        for ch in meta.get("groundingChunks", []):
            web_src = ch.get("web") or {}
            if web_src.get("uri"):
                sources.append(
                    {"title": web_src.get("title") or web_src["uri"], "url": web_src["uri"]}
                )
        return ChatResult(text=text, sources=sources[:8], provider=self.name, web_used=web)
