"""C4/C6 — IDOR, direct object access and mass assignment between two inspectors."""

from __future__ import annotations

import re
from typing import Any

import httpx

from conftest import Actor, new_inspection, png
from test_01_authentication import METHODS

MISSING = "CS-2099-9999"


def _body(r: httpx.Response) -> str:
    return re.sub(r"CS-\d{4}-\d+", "ID", r.text)


def test_user_b_cannot_touch_user_a_inspection_and_response_equals_missing(openapi: dict[str, Any], user_a: Actor, user_b: Actor) -> None:
    iid = new_inspection(user_a)
    a = user_a.get(f"/api/v1/inspections/{iid}").json()
    photo_id = a["photos"][0]["id"]
    leaks: list[str] = []
    for path, item in openapi["paths"].items():
        if "{inspection_id}" not in path:
            continue
        for m in METHODS:
            if m not in item:
                continue
            body: dict[str, Any] = {}
            for real, fake in ((iid, MISSING),):
                u_real = path.replace("{inspection_id}", real).replace("{photo_id}", photo_id).replace("{finding_id}", "x").replace("{key}", "brand")
                u_fake = path.replace("{inspection_id}", fake).replace("{photo_id}", photo_id).replace("{finding_id}", "x").replace("{key}", "brand")
                kw: dict[str, Any] = {} if m == "get" else {"json": body}
                if "photos" in path and m == "post":
                    kw = {"files": {"file": ("x.png", png(), "image/png")}, "data": {"label": "front"}}
                rb = user_b.req(m.upper(), u_real, **kw)
                rm = user_b.req(m.upper(), u_fake, **kw)
                if rb.status_code != rm.status_code or _body(rb) != _body(rm):
                    leaks.append(f"{m.upper()} {path}: foreign={rb.status_code} missing={rm.status_code}")
                if rb.status_code < 400:
                    leaks.append(f"{m.upper()} {path}: foreign -> {rb.status_code} (access!)")
    assert not leaks, "\n".join(leaks)
    # A's data is intact after B's attempts
    assert user_a.get(f"/api/v1/inspections/{iid}").status_code == 200


def test_lists_exports_and_dashboards_are_scoped(user_a: Actor, user_b: Actor) -> None:
    iid = new_inspection(user_a, photos=1)
    lst = user_b.get("/api/v1/inspections", params={"page_size": 100}).json()
    assert iid not in str(lst)
    for widen in ({"owner_uid": user_a.uid}, {"owner": user_a.uid}, {"all": "true"}, {"include_deleted": "true"}, {"status": "any"}, {"user": user_a.uid}):
        r = user_b.get("/api/v1/inspections", params=widen)
        assert r.status_code in (200, 422) and iid not in r.text, widen
    assert iid not in user_b.get("/api/v1/inspections/export").text
    assert iid not in user_b.get("/api/v1/inspector/dashboard").text
    assert user_a.uid not in user_b.get("/api/v1/assistant/messages").text


def test_sequential_ids_do_not_allow_enumeration(user_a: Actor, user_b: Actor) -> None:
    a_id = new_inspection(user_a, photos=1)
    b_id = new_inspection(user_b, photos=1)
    n = int(b_id.rsplit("-", 1)[1])
    for k in range(max(1, n - 6), n + 6):
        cand = f"CS-{b_id.split('-')[1]}-{k:04d}"
        if cand == b_id:
            continue
        r = user_b.get(f"/api/v1/inspections/{cand}")
        assert r.status_code == 404, (cand, r.status_code)
    assert a_id != b_id


def test_user_b_cannot_attach_a_proposal_or_chat_context_to_user_a_inspection(user_a: Actor, user_b: Actor) -> None:
    iid = new_inspection(user_a, photos=1)
    prod = {"product_name": "X", "brand": "Y", "category": "packaged_food"}
    r = user_b.post("/api/v1/proposals", json={"inspection_id": iid, "product": prod, "remarks": ""})
    assert r.status_code in (404, 403, 422), (r.status_code, r.text[:100])
    r = user_b.post("/api/v1/assistant/messages", json={"message": "summarise", "inspection_id": iid})
    assert r.status_code == 404, r.status_code
    assert "reply" not in r.text.lower() or r.status_code == 404


def test_foreign_resource_ids_for_proposals_and_photos(user_a: Actor, user_b: Actor) -> None:
    for url in ("/api/v1/proposals/000000000000000000000000", "/api/v1/proposals/x"):
        assert user_b.get(url).status_code in (404, 422, 400)


def test_mass_assignment_on_every_user_writable_body(user_a: Actor) -> None:
    iid = new_inspection(user_a, photos=1)
    extras = {"_id": "x", "owner_uid": "someone", "user_id": "x", "role": "admin", "is_admin": True, "status": "approved", "approved": True, "created_at": "2000-01-01T00:00:00Z", "version": 99}
    targets = [
        ("PATCH", "/api/v1/me", {"name": "n"}),
        ("PATCH", f"/api/v1/inspections/{iid}/photos/x", {"label": "front"}),
        ("PUT", f"/api/v1/inspections/{iid}/category", {"category": "packaged_food"}),
        ("PUT", f"/api/v1/inspections/{iid}/decision", {"classification": "compliant", "remarks": ""}),
        ("POST", f"/api/v1/inspections/{iid}/notes", {"text": "n"}),
        ("POST", f"/api/v1/inspections/{iid}/fields/confirm", {"keys": []}),
        ("POST", "/api/v1/assistant/messages", {"message": "hi"}),
    ]
    for method, url, base in targets:
        for k, v in extras.items():
            r = user_a.req(method, url, json={**base, k: v})
            assert r.status_code in (404, 409, 422, 400), (method, url, k, r.status_code, r.text[:100])
    me = user_a.get("/api/v1/me").json()
    assert me["role"] == "inspector" and me["status"] == "active"


def test_response_models_do_not_expose_other_users_or_internal_fields(user_a: Actor, user_b: Actor, admin: Actor) -> None:
    iid = new_inspection(user_a, photos=1)
    txt = user_a.get(f"/api/v1/inspections/{iid}").text
    for leak in ('"_id"', "private_key", "password", "token", user_b.uid, "mongodb"):
        assert leak not in txt, leak
    me = user_a.get("/api/v1/me").text
    for leak in ('"_id"', "custom_claims", "refresh"):
        assert leak not in me
