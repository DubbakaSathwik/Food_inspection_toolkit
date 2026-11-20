"""C2 — Authentication: every protected route must reject missing/invalid/forged tokens with 401."""

from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any

import httpx
import pytest

from conftest import Actor, redact

PUBLIC = {("GET", "/health"), ("HEAD", "/health"), ("GET", "/api/v1/public/site-images"), ("GET", "/api/v1/public/site-images/{key}")}
METHODS = ("get", "post", "put", "patch", "delete")


def _b64(obj: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def forged(uid: str, **over: Any) -> str:
    now = int(time.time())
    payload = {
        "iss": "https://securetoken.google.com/some-other-project",
        "aud": "some-other-project",
        "auth_time": now,
        "user_id": uid,
        "sub": uid,
        "iat": now,
        "exp": now + 3600,
        "email": "admin@example.com",
        "email_verified": True,
        "role": "super_admin",
        "active": True,
        "firebase": {"identities": {}, "sign_in_provider": "google.com"},
    }
    payload.update(over)
    return f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(payload)}."


def operations(spec: dict[str, Any]) -> list[tuple[str, str]]:
    ops = []
    for path, item in spec["paths"].items():
        for m in METHODS:
            if m in item and (m.upper(), path) not in PUBLIC:
                ops.append((m.upper(), path))
    return ops


def concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path)


def bad_headers(admin: Actor) -> dict[str, dict[str, str]]:
    return {
        "no_header": {},
        "empty_bearer": {"Authorization": "Bearer"},
        "wrong_scheme": {"Authorization": f"Basic {admin.token}"},
        "malformed": {"Authorization": "Bearer not.a.jwt"},
        "oversized": {"Authorization": "Bearer " + "A" * 5000},
        "other_project_forged_admin": {"Authorization": f"Bearer {forged(admin.uid)}"},
        "custom_token_shape": {"Authorization": f"Bearer {forged(admin.uid, iss='firebase-adminsdk@x.iam.gserviceaccount.com', aud='https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit', firebase=None)}"},
    }


def test_every_protected_route_rejects_bad_tokens(anon: httpx.Client, openapi: dict[str, Any], admin: Actor) -> None:
    failures: list[str] = []
    ops = operations(openapi)
    assert len(ops) > 60
    for method, path in ops:
        for name, headers in bad_headers(admin).items():
            r = anon.request(method, concrete(path), headers=headers, json={} if method != "GET" else None)
            if r.status_code != 401:
                failures.append(f"{method} {path} [{name}] -> {r.status_code} {redact(r.text[:100])}")
    assert not failures, "\n".join(failures[:20])


REAL_MODE = os.environ.get("SEC_REALMODE_URL")


@pytest.mark.skipif(not REAL_MODE, reason="needs a second API instance WITHOUT the Firebase emulator (SEC_REALMODE_URL)")
def test_real_verification_mode_rejects_unsigned_and_expired_tokens(openapi: dict[str, Any], admin: Actor) -> None:
    """The Firebase emulator skips signature/expiry checks by design. With the emulator OFF the Admin SDK's real
    verification runs: unsigned (alg=none), expired and wrong-project tokens must all be refused with 401, never 2xx/5xx."""
    c = httpx.Client(base_url=REAL_MODE, timeout=30)
    cases = {
        "unsigned_matching_project": forged(admin.uid, iss="https://securetoken.google.com/demo-cratescan", aud="demo-cratescan"),
        "unsigned_expired": forged(admin.uid, exp=int(time.time()) - 600, iss="https://securetoken.google.com/demo-cratescan", aud="demo-cratescan"),
        "emulator_token_replayed": admin.token,  # an (unsigned) emulator token must not work against a real-mode server
    }
    bad = []
    for method, path in operations(openapi):
        for name, tok in cases.items():
            r = c.request(method, concrete(path), headers={"Authorization": f"Bearer {tok}"}, json={} if method != "GET" else None)
            if r.status_code != 401:
                bad.append(f"{method} {path} [{name}] -> {r.status_code}")
    assert not bad, "\n".join(bad[:15])


def test_token_in_query_string_is_not_accepted(anon: httpx.Client, admin: Actor) -> None:
    for param in ("token", "access_token", "id_token", "auth"):
        r = anon.get("/api/v1/me", params={param: admin.token})
        assert r.status_code == 401, param


def test_public_routes_expose_only_public_data(anon: httpx.Client) -> None:
    for url in ("/health", "/api/v1/public/site-images", "/api/v1/public/site-images/landing"):
        r = anon.get(url)
        body = r.text.lower()
        assert r.status_code in (200, 404), (url, r.status_code)
        for leak in ("mongodb", "private_key", "uid", "@example.com", "password", "secret"):
            assert leak not in body, (url, leak)


def test_error_bodies_are_uniform_and_safe(anon: httpx.Client, admin: Actor) -> None:
    for r in (anon.get("/api/v1/me"), anon.get("/api/v1/nope"), anon.post("/api/v1/inspections", content=b"{bad json", headers={"content-type": "application/json", **admin.h})):
        assert "error" in r.json(), r.text
        txt = r.text
        for leak in ("Traceback", 'File "', "pymongo", "site-packages", "/home/", "motor", "bson"):
            assert leak not in txt, (r.status_code, leak)


def test_unverified_email_cannot_take_over_super_admin(unverified: Actor) -> None:
    """An UNVERIFIED-email account gets no role. (The Super Admin bootstrap by address is unit-tested in
    backend/tests/test_auth.py::test_unverified_email_never_bootstraps; the emulator blocks re-using the admin's address.)"""
    me = unverified.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["role"] is None and me.json()["status"] == "pending", me.text
    for url in ("/api/v1/admin/users", "/api/v1/admin/dashboard", "/api/v1/inspections"):
        assert unverified.get(url).status_code == 403, url


def test_pending_account_cannot_use_app_apis(pending: Actor, openapi: dict[str, Any]) -> None:
    for method, path in operations(openapi):
        if path in ("/api/v1/me",):
            continue
        r = pending.req(method, concrete(path), json={} if method != "GET" else None)
        assert r.status_code in (401, 403), f"{method} {path} -> {r.status_code}"


def test_disabled_user_loses_access_and_revoked_token_fails_on_writes(admin: Actor) -> None:
    from conftest import _activate

    victim = _activate(admin, "VICTIM")
    old = victim.token
    assert victim.get("/api/v1/inspector/dashboard").status_code == 200
    r = admin.patch(f"/api/v1/admin/users/{victim.uid}", json={"status": "disabled"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {old}"}
    assert httpx.get(f"{admin.http.base_url}/api/v1/inspector/dashboard", headers=h).status_code in (401, 403)
    assert httpx.post(f"{admin.http.base_url}/api/v1/inspections", headers=h).status_code in (401, 403)


def test_admin_write_checks_token_revocation(admin: Actor) -> None:
    """Revoke an admin's refresh tokens by disabling then re-enabling: the pre-revocation token must not do admin writes."""
    from conftest import _activate

    adm = _activate(admin, "REVADM", role="admin")
    old = dict(adm.h)
    assert adm.get("/api/v1/admin/users").status_code == 200
    assert admin.patch(f"/api/v1/admin/users/{adm.uid}", json={"status": "disabled"}).status_code == 200
    r = httpx.post(f"{admin.http.base_url}/api/v1/admin/users/invites", headers=old, json={"email": "x@example.com"})
    assert r.status_code in (401, 403), r.status_code
