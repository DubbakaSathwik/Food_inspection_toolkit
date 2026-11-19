"""Admin diagnostics: live checks of every external dependency, with actionable hints.

Each check returns status ok | warn | fail | skip, a short secret-free detail and hints. Nothing returned here
contains keys, passwords or connection strings."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import firebase_admin
from firebase_admin import auth as fb_auth
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.repositories import files, health
from app.services.ai import chain, ocr
from app.services.ai.base import safe_error

log = logging.getLogger("crate_scan.diagnostics")

Result = dict[str, Any]


def _r(status: str, detail: str, hints: list[str] | None = None) -> Result:
    return {"status": status, "detail": detail, "hints": hints or []}


async def check_config() -> Result:
    s = get_settings()
    problems: list[str] = []
    hints: list[str] = []
    uri = (s.mongodb_uri or "").lower()
    if "<" in uri or "<cluster>" in uri or ">@" in uri:
        problems.append("MONGODB_URI still contains <placeholders>")
        hints.append("Remove the < > brackets and use your real Atlas host and password.")
    email = (s.super_admin_email or "").lower()
    if not email:
        problems.append("SUPER_ADMIN_EMAIL is empty")
    elif email.endswith("@example.com"):
        problems.append("SUPER_ADMIN_EMAIL is an @example.com address")
        hints.append("Use the real Google account that signs in as Super Admin.")
    if s.is_production and any("localhost" in o for o in s.cors_origins):
        problems.append("CORS allows localhost in production")
    detail = (
        f"environment={s.app_env}; AI order={','.join(s.provider_order) or 'none'}; "
        f"CORS={', '.join(s.cors_origins) or 'none'}; limits default/write/AI="
        f"{s.rate_limit_default} / {s.rate_limit_write} / {s.rate_limit_ai}"
    )
    if problems:
        return _r("warn", "; ".join(problems) + ". " + detail, hints)
    return _r("ok", detail)


async def check_database() -> Result:
    if not await health.ping():
        return _r(
            "fail",
            "MongoDB did not answer within 4 seconds.",
            [
                "Check MONGODB_URI (real host, no < > brackets, correct password).",
                "Atlas → Network Access must allow your current IP address.",
                "Restart the backend after editing .env.",
            ],
        )
    return _r("ok", f"MongoDB reachable (database '{get_settings().mongodb_db_name}').")


async def check_storage() -> Result:
    if not await health.ping():
        return _r("skip", "Database is not reachable.")
    try:
        stats = {b: await files.bucket_stats(b) for b in ("photos", "reports")}
    except Exception as e:
        return _r("fail", f"Could not read file storage: {safe_error(e)}")
    detail = "; ".join(f"{b}: {v.get('files', 0):g} files" for b, v in stats.items())
    return _r("ok", f"File storage (GridFS) readable — {detail}.")


async def check_firebase() -> Result:
    s = get_settings()
    if not firebase_admin._apps:
        return _r("fail", "Firebase Admin was not initialised.", ["Restart the backend."])
    if s.firebase_auth_emulator_host:
        return _r(
            "warn",
            f"Using the Auth emulator at {s.firebase_auth_emulator_host} (development only).",
        )
    if not s.firebase_service_account_json:
        return _r(
            "fail",
            "FIREBASE_SERVICE_ACCOUNT_JSON is empty, so the server cannot verify sign-ins.",
            [
                "Put the service-account JSON on ONE line, in single quotes, in backend/.env.",
                "Firebase → Project settings → Service accounts → Generate new private key.",
            ],
        )
    try:
        await asyncio.wait_for(run_in_threadpool(lambda: fb_auth.list_users(max_results=1)), 15)
    except Exception as e:
        return _r(
            "fail",
            f"Firebase rejected the service account: {safe_error(e)}",
            ["Use a freshly generated key for project " + s.firebase_project_id + "."],
        )
    return _r("ok", f"Service account accepted by Firebase project '{s.firebase_project_id}'.")


def _provider_check(name: str) -> Callable[[], Awaitable[Result]]:
    async def run() -> Result:
        provider = next((p for p in chain.build_providers() if p.name == name), None)
        if provider is None:
            return _r("skip", f"'{name}' is not in AI_PROVIDER_ORDER.")
        if not provider.configured():
            return _r(
                "skip", "No API key set.", [f"Add the key for {name} in backend/.env and restart."]
            )
        started = time.monotonic()
        try:
            res = await asyncio.wait_for(
                provider.chat(
                    "You are a connectivity test.",
                    [{"role": "user", "text": "Reply with the single word OK."}],
                    False,
                ),
                get_settings().ai_timeout_seconds + 5,
            )
        except Exception as e:  # report every failure, never crash
            return _r("fail", safe_error(e), _provider_hints(name, str(e)))
        ms = int((time.monotonic() - started) * 1000)
        return _r(
            "ok",
            f"Answered in {ms} ms: “{res.text.strip()[:40]}”. (Text test; image reading uses the same key and model.)",
        )

    return run


def _provider_hints(name: str, msg: str) -> list[str]:
    hints: list[str] = []
    if "HTTP 401" in msg or "HTTP 403" in msg or "invalid" in msg.lower():
        hints.append(
            "The key is wrong, revoked or lacks permission — create a new one and update backend/.env."
        )
    if "HTTP 404" in msg or "HTTP 410" in msg:
        hints.append(
            "The model name is retired or unknown — choose a current model and update its *_MODEL setting."
        )
    if "HTTP 429" in msg:
        hints.append("Quota or rate limit reached — wait a few minutes or use another provider.")
    if "HTTP 5" in msg:
        hints.append(
            "The provider is overloaded or down — retry later; the next provider in the order is used automatically."
        )
    if "network" in msg.lower() or "Timeout" in msg:
        hints.append(
            "The server could not reach the provider — check the internet connection and proxy settings."
        )
    return hints


async def check_ocr() -> Result:
    if ocr.available():
        return _r("ok", "PaddleOCR is installed and enabled.")
    if not get_settings().ocr_enabled:
        return _r("skip", "OCR fallback is disabled (OCR_ENABLED=false). Optional.")
    return _r(
        "fail", "OCR_ENABLED=true but PaddleOCR is not installed.", ["Run: uv sync --extra ocr"]
    )


CHECKS: list[tuple[str, str, str, Callable[[], Awaitable[Result]]]] = [
    ("config", "Configuration", "Environment values the server loaded", check_config),
    (
        "database",
        "Database (MongoDB)",
        "Connection to MongoDB Atlas / local MongoDB",
        check_database,
    ),
    (
        "storage",
        "File storage (GridFS)",
        "Photos and report files stored in MongoDB",
        check_storage,
    ),
    (
        "firebase",
        "Firebase sign-in",
        "Server credentials used to verify Google sign-ins",
        check_firebase,
    ),
    ("gemini", "AI — Gemini", "Live test call to Google Gemini", _provider_check("gemini")),
    ("nvidia", "AI — NVIDIA", "Live test call to NVIDIA", _provider_check("nvidia")),
    (
        "huggingface",
        "AI — Hugging Face",
        "Live test call to Hugging Face",
        _provider_check("huggingface"),
    ),
    ("ocr", "OCR fallback", "Optional offline text reader", check_ocr),
]


def catalogue() -> list[dict[str, str]]:
    return [{"id": i, "title": t, "description": d} for i, t, d, _ in CHECKS]


async def run_check(check_id: str) -> Result | None:
    for i, title, _, fn in CHECKS:
        if i == check_id:
            started = time.monotonic()
            try:
                res = await fn()
            except Exception as e:  # a broken check must not break the page
                log.exception("diagnostic %s crashed", i)
                res = _r("fail", safe_error(e))
            return {"id": i, "title": title, "ms": int((time.monotonic() - started) * 1000), **res}
    return None
