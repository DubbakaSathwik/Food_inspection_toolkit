from __future__ import annotations

import httpx
from firebase_admin import auth as fb_auth

from app.db import get_db
from tests.conftest import User, emulator_sign_in, make_user


async def test_no_token_is_401(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


async def test_garbage_and_malformed_tokens_rejected(client: httpx.AsyncClient) -> None:
    for header in ("Bearer not-a-token", "Basic abc", "Bearer ", "Bearer " + "x" * 5000):
        r = await client.get("/api/v1/inspector/dashboard", headers={"Authorization": header})
        assert r.status_code == 401, header
        assert "Traceback" not in r.text


async def test_new_user_is_pending_and_blocked(client: httpx.AsyncClient) -> None:
    u = await make_user(client, role=None)
    me = await u.me()
    assert me["status"] == "pending" and me["role"] is None
    r = await u.get("/api/v1/inspector/dashboard")
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_pending"
    r = await u.get("/api/v1/admin/dashboard")
    assert r.status_code == 403


async def test_super_admin_bootstrap(super_admin: User) -> None:
    me = await super_admin.me()
    assert me["role"] == "super_admin" and me["status"] == "active" and me["claims_stale"] is False
    r = await super_admin.get("/api/v1/admin/dashboard")
    assert r.status_code == 200, r.text


async def test_unverified_email_never_bootstraps(client: httpx.AsyncClient) -> None:
    from app.repositories import users as users_repo

    doc = await users_repo.ensure_profile(
        "unverified-uid-1", "boss@example.com", "X", None, False, "boss@example.com"
    )
    assert doc["status"] == "pending" and doc["role"] is None
    doc = await users_repo.ensure_profile(
        "unverified-uid-1", "boss@example.com", "X", None, False, "boss@example.com"
    )
    assert doc["status"] == "pending"
    token = emulator_sign_in("someone-unverified@example.com", "unv-1", verified=False)
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["status"] == "pending"


async def test_approval_flow_with_claims_refresh(
    client: httpx.AsyncClient, super_admin: User
) -> None:
    u = await make_user(client, role=None)
    r = await super_admin.post(f"/api/v1/admin/users/{u.uid}/approve", json={"role": "inspector"})
    assert r.status_code == 200, r.text
    # old token has no claims → stale until refreshed
    r = await u.get("/api/v1/inspector/dashboard")
    assert r.status_code == 401 and r.json()["error"]["code"] == "claims_stale"
    u.refresh()
    assert (await u.get("/api/v1/inspector/dashboard")).status_code == 200


async def test_role_escalation_attempts_fail(client: httpx.AsyncClient, inspector: User) -> None:
    r = await inspector.patch("/api/v1/me", json={"role": "admin"})
    assert r.status_code == 422
    r = await inspector.patch("/api/v1/me", json={"name": "Ok", "status": "active"})
    assert r.status_code == 422
    assert (await inspector.get("/api/v1/admin/users")).status_code == 403
    r = await inspector.post(
        f"/api/v1/admin/users/{inspector.uid}/approve", json={"role": "super_admin"}
    )
    assert r.status_code == 403
    me = await inspector.me()
    assert me["role"] == "inspector"


async def test_admin_cannot_grant_admin_roles(client: httpx.AsyncClient, admin: User) -> None:
    u = await make_user(client, role=None)
    r = await admin.post(f"/api/v1/admin/users/{u.uid}/approve", json={"role": "admin"})
    assert r.status_code == 403
    r = await admin.post(f"/api/v1/admin/users/{u.uid}/approve", json={"role": "inspector"})
    assert r.status_code == 200
    r = await admin.patch(f"/api/v1/admin/users/{admin.uid}", json={"status": "disabled"})
    assert r.status_code == 403  # cannot change self


async def test_disable_blocks_immediately(client: httpx.AsyncClient, super_admin: User) -> None:
    u = await make_user(client, "inspector")
    assert (await u.get("/api/v1/inspector/dashboard")).status_code == 200
    r = await super_admin.patch(f"/api/v1/admin/users/{u.uid}", json={"status": "disabled"})
    assert r.status_code == 200 and r.json()["status"] == "disabled"
    r = await u.get("/api/v1/inspector/dashboard")
    assert r.status_code in (401, 403)


async def test_demotion_removes_admin_access(client: httpx.AsyncClient, super_admin: User) -> None:
    a = await make_user(client, "admin")
    assert (await a.get("/api/v1/admin/users")).status_code == 200
    r = await super_admin.patch(f"/api/v1/admin/users/{a.uid}", json={"role": "inspector"})
    assert r.status_code == 200
    r = await a.get("/api/v1/admin/users")
    assert r.status_code in (401, 403)
    a.refresh()
    assert (await a.get("/api/v1/admin/users")).status_code == 403
    assert (await a.get("/api/v1/inspector/dashboard")).status_code == 200


async def test_last_super_admin_protected(super_admin: User, client: httpx.AsyncClient) -> None:
    other = await make_user(client, "super_admin")
    r = await other.patch(f"/api/v1/admin/users/{super_admin.uid}", json={"role": "admin"})
    assert r.status_code == 200  # two super admins exist → allowed
    r = await other.patch(f"/api/v1/admin/users/{super_admin.uid}", json={"role": "super_admin"})
    assert r.status_code == 200
    await get_db()["users"].update_one({"_id": other.uid}, {"$set": {"status": "disabled"}})
    fb_auth.set_custom_user_claims(super_admin.uid, {"role": "super_admin", "active": True})
    super_admin.refresh()
    await super_admin.me()


async def test_invite_preauthorises_role(client: httpx.AsyncClient, super_admin: User) -> None:
    r = await super_admin.post(
        "/api/v1/admin/users/invites",
        json={"email": "Invited.Person@example.com", "name": "Invited", "role": "inspector"},
    )
    assert r.status_code == 201, r.text
    u = User(client, "invited.person@example.com", "Invited")
    me = await u.me()
    assert me["status"] == "active" and me["role"] == "inspector"
    assert (await u.get("/api/v1/inspector/dashboard")).status_code == 200


async def test_profile_update(inspector: User) -> None:
    r = await inspector.patch(
        "/api/v1/me", json={"designation": "Food Safety Officer", "office": "Nashik"}
    )
    assert r.status_code == 200 and r.json()["office"] == "Nashik"


def test_production_refuses_to_start_without_firebase_credentials() -> None:
    """SEC-004: a production server with no service account must fail at startup, not 500 on every request."""
    import os
    import subprocess
    import sys

    env = {k: v for k, v in os.environ.items() if k != "GOOGLE_APPLICATION_CREDENTIALS"}
    # blank (not removed) so a developer's backend/.env cannot re-introduce the emulator host
    env.update(
        {
            "APP_ENV": "production",
            "FIREBASE_PROJECT_ID": "x",
            "FIREBASE_SERVICE_ACCOUNT_JSON": "",
            "FIREBASE_AUTH_EMULATOR_HOST": "",
        }
    )
    out = subprocess.run(
        [sys.executable, "-c", "from app.auth import init_firebase; init_firebase()"],
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        env=env,
        capture_output=True,
        text=True,
    )
    assert out.returncode != 0
    assert "FIREBASE_SERVICE_ACCOUNT_JSON is required" in out.stderr, out.stderr[-300:]
