"""Rate limiting (T-38). Disabled for the rest of the suite (APP_ENV=test); enabled explicitly here."""

from __future__ import annotations

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.config import get_settings
from app.ratelimit import RateLimitMiddleware, parse_limit


def _mw(
    default: str = "3/minute", write: str = "2/minute", ai: str = "1/minute"
) -> RateLimitMiddleware:
    async def app(
        scope: object, receive: object, send: object
    ) -> None:  # pragma: no cover - never called
        return None

    return RateLimitMiddleware(app, default=default, write=write, ai=ai)  # type: ignore[arg-type]


def test_parse_limit() -> None:
    assert parse_limit("60/minute") == (60, 60)
    assert parse_limit("10/seconds") == (10, 1)
    with pytest.raises(ValueError):
        parse_limit("lots/minute")


def test_default_write_and_ai_buckets() -> None:
    mw = _mw()
    t = 1_000_020.0
    assert [mw.check("1.1.1.1", "GET", "/api/v1/me", t) for _ in range(3)] == [None, None, None]
    assert mw.check("1.1.1.1", "GET", "/api/v1/me", t) is not None  # 4th GET in the window
    assert mw.check("2.2.2.2", "GET", "/api/v1/me", t) is None  # other clients unaffected
    assert mw.check("3.3.3.3", "POST", "/api/v1/inspections/CS-2026-0001/extract", t) is None
    assert (
        mw.check("3.3.3.3", "POST", "/api/v1/inspections/CS-2026-0001/extract", t) is not None
    )  # AI: 1/minute
    assert mw.check("4.4.4.4", "PATCH", "/api/v1/me", t) is None
    assert mw.check("4.4.4.4", "PATCH", "/api/v1/me", t) is None
    assert mw.check("4.4.4.4", "PATCH", "/api/v1/me", t) is not None  # writes: 2/minute
    assert mw.check("1.1.1.1", "GET", "/api/v1/me", t + 60) is None  # next window


async def test_app_returns_429_with_error_format(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.main import create_app

    s = get_settings()
    monkeypatch.setattr(s, "app_env", "development")
    monkeypatch.setattr(s, "rate_limit_default", "3/minute")
    app = create_app()
    async with LifespanManager(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            codes = [(await c.get("/api/v1/public/site-images")).status_code for _ in range(4)]
            assert codes == [200, 200, 200, 429]
            r = await c.get("/api/v1/public/site-images")
            assert r.json()["error"]["code"] == "rate_limited"
            assert int(r.headers["retry-after"]) >= 1
            assert (
                await c.options(
                    "/api/v1/me",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "GET",
                    },
                )
            ).status_code == 200
