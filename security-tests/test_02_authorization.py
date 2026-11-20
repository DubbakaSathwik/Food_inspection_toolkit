"""C3 — role-based authorization and privilege escalation."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import httpx

from conftest import Actor, _activate
from test_01_authentication import concrete, operations

OUT = pathlib.Path(__file__).parent / "last-run"


def test_admin_routes_refuse_non_admins_and_write_matrix(openapi: dict[str, Any], user_a: Actor, pending: Actor, unverified: Actor, anon: httpx.Client) -> None:
    rows: list[dict[str, Any]] = []
    bad: list[str] = []
    for method, path in operations(openapi):
        if not path.startswith("/api/v1/admin"):
            continue
        for who, call in (("ANON", lambda m, p: anon.request(m, p, json={})), ("PENDING", lambda m, p, a=pending: a.req(m, p, json={})),
                          ("UNVERIFIED", lambda m, p, a=unverified: a.req(m, p, json={})), ("INSPECTOR", lambda m, p, a=user_a: a.req(m, p, json={}))):
            r = call(method, concrete(path))
            rows.append({"identity": who, "method": method, "route": path, "status": r.status_code})
            if r.status_code not in (401, 403):
                bad.append(f"{who} {method} {path} -> {r.status_code}")
    OUT.mkdir(exist_ok=True)
    (OUT / "authz-matrix-admin.json").write_text(json.dumps(rows, indent=1))
    assert not bad, "\n".join(bad[:20])


def test_inspector_cannot_escalate_via_profile_or_headers(user_a: Actor) -> None:
    for body in ({"role": "admin"}, {"role": "super_admin", "status": "active"}, {"is_admin": True}, {"claims": {"role": "admin"}}, {"permissions": ["*"]}, {"status": "active"}, {"email": "x@example.com"}):
        r = user_a.patch("/api/v1/me", json={"name": "Renamed", **body})
        assert r.status_code == 422, (body, r.status_code, r.text[:120])
    for h in ({"X-Role": "admin"}, {"X-User-Role": "super_admin"}, {"X-Forwarded-User": "admin"}, {"X-Admin": "true"}):
        assert user_a.get("/api/v1/admin/dashboard", headers=h).status_code == 403
    assert user_a.get("/api/v1/me").json()["role"] == "inspector"


def test_plain_admin_cannot_touch_privileged_roles(admin: Actor, plain_admin: Actor, user_a: Actor) -> None:
    pa = plain_admin
    assert pa.get("/api/v1/admin/users").status_code == 200
    assert pa.patch(f"/api/v1/admin/users/{user_a.uid}", json={"role": "admin"}).status_code == 403
    assert pa.patch(f"/api/v1/admin/users/{user_a.uid}", json={"role": "super_admin"}).status_code == 403
    assert pa.patch(f"/api/v1/admin/users/{admin.uid}", json={"status": "disabled"}).status_code == 403
    assert pa.patch(f"/api/v1/admin/users/{admin.uid}", json={"role": "inspector"}).status_code == 403
    assert pa.patch(f"/api/v1/admin/users/{pa.uid}", json={"role": "super_admin"}).status_code in (403, 409)
    assert pa.post("/api/v1/admin/users/invites", json={"email": "evil@example.com", "role": "super_admin"}).status_code == 403
    assert pa.post("/api/v1/admin/users/invites", json={"email": "evil2@example.com", "role": "admin"}).status_code == 403
    assert admin.get("/api/v1/me").json()["role"] == "super_admin"


def test_last_super_admin_cannot_be_removed(admin: Actor) -> None:
    for body in ({"status": "disabled"}, {"role": "inspector"}, {"role": "admin"}):
        r = admin.patch(f"/api/v1/admin/users/{admin.uid}", json=body)
        assert r.status_code in (403, 409, 422), (body, r.status_code)
    assert admin.get("/api/v1/me").json()["role"] == "super_admin"


def test_role_change_takes_effect_and_old_claims_are_refused(admin: Actor) -> None:
    adm = _activate(admin, "DEMOTE", role="admin")
    old = dict(adm.h)
    assert adm.get("/api/v1/admin/users").status_code == 200
    assert admin.patch(f"/api/v1/admin/users/{adm.uid}", json={"role": "inspector"}).status_code == 200
    r = httpx.get(f"{admin.http.base_url}/api/v1/admin/users", headers=old)
    assert r.status_code in (401, 403), r.status_code  # claims_stale / forbidden, never 200
    r = httpx.post(f"{admin.http.base_url}/api/v1/admin/users/invites", headers=old, json={"email": "z@example.com"})
    assert r.status_code in (401, 403)


def test_decline_and_pending_users_cannot_self_activate(admin: Actor, pending: Actor) -> None:
    assert pending.get("/api/v1/inspections").status_code == 403
    assert pending.patch("/api/v1/me", json={"name": "x", "status": "active"}).status_code == 422
    assert pending.post(f"/api/v1/admin/users/{pending.uid}/approve", json={"role": "inspector"}).status_code in (401, 403)
    assert pending.get("/api/v1/me").json()["status"] == "pending"
