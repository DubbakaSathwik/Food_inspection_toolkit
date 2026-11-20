"""Per-client rate limiting (ASGI middleware, fixed windows, in memory).

Replaces slowapi, whose middleware did not apply limits to our routes (found in Phase 4, T-38).
In-memory counters are per process: correct for the single Render instance (A1); a multi-instance
deployment would need a shared store (documented in SECURITY.md)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_AI_PATH = re.compile(r"/(extract|analyze|ai-extract)$|/assistant/messages$")


def parse_limit(text: str) -> tuple[int, int]:
    """'60/minute' -> (60, 60 seconds)."""
    count, _, unit = text.strip().partition("/")
    seconds = _UNITS.get(unit.strip().rstrip("s"), 0)
    if not count.strip().isdigit() or not seconds:
        raise ValueError(f"Invalid rate limit '{text}' (use e.g. 60/minute)")
    return int(count), seconds


@dataclass
class Rule:
    name: str
    count: int
    window: int


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        default: str,
        write: str,
        ai: str,
        enabled: bool = True,
        trusted_proxy_hops: int = 0,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.hops = trusted_proxy_hops
        self.rules = {
            name: Rule(name, *parse_limit(v))
            for name, v in (("default", default), ("write", write), ("ai", ai))
        }
        self.hits: dict[tuple[str, str, int], int] = {}
        self._last_sweep = 0.0

    def _rules_for(self, method: str, path: str) -> list[Rule]:
        rules = [self.rules["default"]]
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            rules.append(
                self.rules["ai"]
                if (method == "POST" and _AI_PATH.search(path))
                else self.rules["write"]
            )
        return rules

    def _client(self, scope: Scope) -> str:
        """Client key for the limiter (SEC-003). X-Forwarded-For is attacker-controlled on the left, so it is ignored
        unless TRUSTED_PROXY_HOPS says how many proxies of ours sit in front; then the entry that the nearest
        trusted proxy appended (counting from the right) is used. Run uvicorn WITHOUT --forwarded-allow-ips '*'."""
        client = scope.get("client")
        peer: str = str(client[0]) if client else "unknown"
        if self.hops > 0:
            raw = dict(scope.get("headers") or []).get(b"x-forwarded-for", b"").decode("latin-1")
            parts: list[str] = [str(p).strip() for p in raw.split(",") if p.strip()]
            if len(parts) >= self.hops:
                return str(parts[-self.hops])[:64]
        return peer

    def check(self, client: str, method: str, path: str, now: float | None = None) -> int | None:
        """Count the request; return seconds to wait when a limit is exceeded, else None."""
        now = time.time() if now is None else now
        if now - self._last_sweep > 60:
            self._sweep(now)
        retry: int | None = None
        for rule in self._rules_for(method, path):
            window = int(now // rule.window)
            key = (client, rule.name, window)
            self.hits[key] = self.hits.get(key, 0) + 1
            if self.hits[key] > rule.count:
                retry = max(retry or 0, int((window + 1) * rule.window - now) + 1)
        return retry

    def _sweep(self, now: float) -> None:
        self._last_sweep = now
        longest = max(r.window for r in self.rules.values())
        cutoff = int(now // longest) - 1
        self.hits = {
            k: v
            for k, v in self.hits.items()
            if k[2] * self.rules[k[1]].window // longest >= cutoff
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled or scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        retry = self.check(self._client(scope), scope["method"], scope["path"])
        if retry is None:
            await self.app(scope, receive, send)
            return
        body = b'{"error":{"code":"rate_limited","message":"Too many requests. Please wait a moment and try again."}}'
        headers: list[Any] = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"retry-after", str(retry).encode()),
        ]
        await send({"type": "http.response.start", "status": 429, "headers": headers})
        await send({"type": "http.response.body", "body": body})
