"""CRATE-SCAN FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.auth import init_firebase
from app.config import get_settings
from app.db import close_client
from app.errors import install_error_handlers
from app.ratelimit import RateLimitMiddleware
from app.routers import admin, admin_reference, assistant, inspections, me, proposals, public


class BodySizeLimit:
    """Reject request bodies above the limit (multipart uploads get the upload limit)."""

    def __init__(self, app: ASGIApp, upload_bytes: int, json_bytes: int) -> None:
        self.app, self.upload_bytes, self.json_bytes = app, upload_bytes, json_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        ctype = headers.get(b"content-type", b"").decode("latin-1")
        limit = self.upload_bytes if ctype.startswith("multipart/") else self.json_bytes
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await self._reject(send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            msg = await receive()
            if msg["type"] == "http.request":
                received += len(msg.get("body", b""))
                if received > limit:
                    raise _TooLarge()
            return msg

        try:
            await self.app(scope, limited_receive, send)
        except _TooLarge:
            await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"error":{"code":"payload_too_large","message":"Request is too large."}}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class _TooLarge(Exception):
    pass


def _security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_headers(request: Any, call_next: Callable[[Any], Awaitable[Any]]) -> Any:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if "cache-control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        if get_settings().is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_firebase()
    yield
    await close_client()


def create_app() -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=s.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    docs = not s.is_production
    app = FastAPI(
        title="CRATE-SCAN API",
        version="1.0.0",
        description="AI-assisted food-product inspection toolkit (decision support only).",
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    install_error_handlers(app)
    _security_headers(app)
    # Inside CORS (added first = inner) so 429 answers still carry CORS headers the browser can read.
    app.add_middleware(
        RateLimitMiddleware,
        default=s.rate_limit_default,
        write=s.rate_limit_write,
        ai=s.rate_limit_ai,
        enabled=s.app_env != "test",
        trusted_proxy_hops=s.trusted_proxy_hops,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition"],
        max_age=600,
    )
    app.add_middleware(
        BodySizeLimit,
        upload_bytes=(s.max_upload_mb + 1) * 1_048_576,
        json_bytes=s.max_json_kb * 1024,
    )
    for r in (
        public.router,
        me.router,
        inspections.router,
        proposals.router,
        assistant.router,
        admin_reference.router,
        admin.router,
    ):
        app.include_router(r)
    return app


app = create_app()
