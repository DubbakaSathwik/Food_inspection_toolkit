"""Firebase ID-token verification and role guards (single authentication path for all routes).

Roles come from verified custom claims {role, active}. The database status is also checked so a
disabled account is blocked immediately; a claim/DB mismatch returns 401 `claims_stale` so the client
refreshes its token (after an approval or role change)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import firebase_admin
from fastapi import Depends, Request
from firebase_admin import auth as fb_auth
from firebase_admin import credentials
from google.auth.exceptions import DefaultCredentialsError
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.errors import AppError
from app.principal import Principal
from app.repositories import users as users_repo

log = logging.getLogger("crate_scan.auth")


def init_firebase() -> None:
    if firebase_admin._apps:
        return
    s = get_settings()
    if s.firebase_auth_emulator_host:
        if s.is_production:
            raise RuntimeError("FIREBASE_AUTH_EMULATOR_HOST must not be set in production")
        # The Admin SDK reads the emulator host from the process environment (not from .env).
        os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = s.firebase_auth_emulator_host
    cred: credentials.Base | None = None
    if (
        s.is_production
        and not s.firebase_service_account_json
        and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    ):
        # SEC-004: without credentials every token check crashed with a 500 at request time; fail at startup instead.
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is required in production")
    if s.firebase_service_account_json:
        cred = credentials.Certificate(json.loads(s.firebase_service_account_json))
    firebase_admin.initialize_app(cred, {"projectId": s.firebase_project_id})


def _unauth(message: str = "Please sign in again.", code: str = "unauthenticated") -> AppError:
    return AppError(401, code, message)


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 4096:
        raise _unauth("Sign-in required.")
    return token.strip()


async def verify_token(token: str, check_revoked: bool = False) -> dict[str, Any]:
    try:
        return await run_in_threadpool(fb_auth.verify_id_token, token, None, check_revoked, 5)
    except fb_auth.RevokedIdTokenError as e:
        raise _unauth("Your session was ended. Please sign in again.", "session_revoked") from e
    except fb_auth.UserDisabledError as e:
        raise AppError(403, "account_disabled", "This account is disabled.") from e
    except (fb_auth.ExpiredIdTokenError, fb_auth.InvalidIdTokenError, ValueError) as e:
        log.info("token rejected: %s", type(e).__name__)
        raise _unauth() from e
    except (fb_auth.CertificateFetchError, DefaultCredentialsError) as e:
        log.error("sign-in verification unavailable: %s", type(e).__name__)
        raise AppError(503, "auth_unavailable", "Sign-in service unavailable. Try again.") from e


async def token_claims(request: Request) -> dict[str, Any]:
    claims = await verify_token(_bearer(request))
    if not claims.get("email"):
        raise _unauth("A Google account with an email address is required.")
    if claims.get("firebase", {}).get("sign_in_provider") != "google.com":
        raise _unauth("Please sign in with Google.")
    return claims


async def set_claims(uid: str, role: str | None, active: bool) -> None:
    await run_in_threadpool(fb_auth.set_custom_user_claims, uid, {"role": role, "active": active})


async def revoke_tokens(uid: str) -> None:
    await run_in_threadpool(fb_auth.revoke_refresh_tokens, uid)


def claims_match(claims: dict[str, Any], user: dict[str, Any]) -> bool:
    active = user.get("status") == "active"
    if bool(claims.get("active")) != active:
        return False
    return not active or claims.get("role") == user.get("role")


async def current_principal(request: Request) -> Principal:
    """Verified, active user. Pending/declined/disabled accounts are refused."""
    claims = await token_claims(request)
    user = await users_repo.get(claims["uid"])
    if not user:
        raise AppError(
            403, "profile_missing", "Account not set up yet. Open the app to finish sign-in."
        )
    status = user.get("status", "pending")
    if status != "active":
        code = {
            "pending": "account_pending",
            "declined": "account_declined",
            "disabled": "account_disabled",
        }.get(status, "account_inactive")
        raise AppError(403, code, "Your account is not active.")
    if not claims.get("active") or claims.get("role") != user.get("role"):
        raise _unauth("Your access changed. Refreshing your session.", "claims_stale")
    await users_repo.touch_active(user["_id"])
    return Principal(
        uid=user["_id"],
        email=user["email"],
        name=user.get("name") or user["email"],
        role=user.get("role"),
        status="active",
    )


async def require_inspector(p: Principal = Depends(current_principal)) -> Principal:
    if not p.is_inspector:
        raise AppError(403, "forbidden", "This area is for inspectors.")
    return p


async def require_admin(request: Request, p: Principal = Depends(current_principal)) -> Principal:
    if not p.is_admin:
        raise AppError(403, "forbidden", "Administrator access required.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        await verify_token(_bearer(request), check_revoked=True)
    return p


async def require_super_admin(request: Request, p: Principal = Depends(require_admin)) -> Principal:
    if not p.is_super_admin:
        raise AppError(403, "forbidden", "Super Admin access required.")
    return p
