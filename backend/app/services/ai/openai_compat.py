"""OpenAI-compatible chat-completions providers: NVIDIA NIM and Hugging Face router (backups)."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from app.config import get_settings
from app.services.ai.base import ChatResult, ProviderError, http_error, parse_json, post_with_retry
from app.services.images import ImageInput, fit_to_limit


class OpenAICompatProvider:
    supports_web = False

    def __init__(
        self,
        name: str,
        api_key: str | None,
        base_url: str,
        model: str,
        max_image_kb: int,
        single_image: bool,
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_image_bytes = max_image_kb * 1024
        self.single_image = single_image
        self.timeout = get_settings().ai_timeout_seconds

    def configured(self) -> bool:
        return bool(self.api_key)

    def _image_content(self, img: ImageInput) -> dict[str, Any]:
        data, mime, _ = fit_to_limit(img.data, img.mime, self.max_image_bytes)
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"},
        }

    async def _complete(self, messages: list[dict[str, Any]], max_tokens: int = 3000) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await post_with_retry(
                    client,
                    f"{self.base_url}/chat/completions",
                    headers={
                        "authorization": f"Bearer {self.api_key}",
                        "accept": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": max_tokens,
                    },
                )
        except httpx.HTTPError as e:
            raise ProviderError(f"network error ({type(e).__name__})") from e
        if r.status_code != 200:
            raise http_error(r)
        try:
            return str(r.json()["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, ValueError) as e:
            raise ProviderError("unexpected response shape") from e

    async def _extract_batch(self, images: list[ImageInput], prompt: str) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img in images:
            content.append(
                {"type": "text", "text": f"Photo {img.index} ({img.label or 'unlabelled'}):"}
            )
            content.append(self._image_content(img))
        return parse_json(await self._complete([{"role": "user", "content": content}]))

    async def extract(self, images: list[ImageInput], prompt: str) -> dict[str, Any]:
        if not self.single_image:
            return await self._extract_batch(images, prompt)
        merged: dict[str, Any] = {"fields": {}}
        for img in images:
            part = await self._extract_batch([img], prompt)
            for k, v in (part.get("fields") or {}).items():
                cur = merged["fields"].get(k)
                if (
                    isinstance(v, dict)
                    and v.get("value")
                    and (
                        not cur
                        or float(v.get("confidence") or 0) > float(cur.get("confidence") or 0)
                    )
                ):
                    merged["fields"][k] = v
            if part.get("category") and not merged.get("category"):
                merged["category"] = part["category"]
                merged["category_confidence"] = part.get("category_confidence")
        return merged

    async def compare(
        self, uploaded: list[ImageInput], reference: list[ImageInput], prompt: str
    ) -> dict[str, Any]:
        if self.single_image:
            raise ProviderError("single-image model cannot compare packaging")
        imgs = uploaded + reference
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for i, img in enumerate(imgs):
            tag = "UPLOADED" if i < len(uploaded) else "REFERENCE"
            content.append({"type": "text", "text": f"{tag} photo:"})
            content.append(self._image_content(img))
        return parse_json(await self._complete([{"role": "user", "content": content}]))

    async def chat(self, system: str, messages: list[dict[str, str]], web: bool) -> ChatResult:
        msgs: list[dict[str, Any]] = [{"role": "system", "content": system}]
        msgs += [{"role": m["role"], "content": m["text"]} for m in messages]
        text = (await self._complete(msgs, max_tokens=1500)).strip()
        if not text:
            raise ProviderError("empty answer")
        return ChatResult(text=text, provider=self.name)


def nvidia() -> OpenAICompatProvider:
    s = get_settings()
    return OpenAICompatProvider(
        "nvidia",
        s.nvidia_api_key,
        s.nvidia_base_url,
        s.nvidia_model,
        s.nvidia_max_image_kb,
        single_image=True,
    )


def huggingface() -> OpenAICompatProvider:
    s = get_settings()
    return OpenAICompatProvider(
        "huggingface",
        s.hf_api_key,
        s.hf_base_url,
        s.hf_model,
        s.hf_max_image_kb,
        single_image=False,
    )
