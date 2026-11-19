"""C5/C8 — NoSQL operator injection, odd IDs, pagination abuse, ReDoS, upload abuse."""

from __future__ import annotations

import io
import time
from typing import Any

import pytest
from PIL import Image

from conftest import Actor, new_inspection, png

OPS = ['{"$ne": null}', '{"$gt": ""}', '{"$regex": ".*"}', '{"$where": "sleep(2000)"}', '{"$expr": {"$eq": [1,1]}}', "$ne", "a[$ne]=1", "'; return true; //", "\x00", "{{7*7}}", "${7*7}"]


def _ok(r: Any) -> bool:
    return r.status_code in (200, 400, 404, 409, 413, 415, 422) and "Traceback" not in r.text and "pymongo" not in r.text.lower()


def test_operator_strings_in_every_query_parameter_never_widen_or_500(admin: Actor, user_a: Actor, user_b: Actor) -> None:
    a_id = new_inspection(user_a, photos=1)
    baseline = user_b.get("/api/v1/inspections").json()["total"]  # B's own inspections only
    for payload in OPS:
        for url, who in (("/api/v1/inspections", user_b), ("/api/v1/proposals", user_b), ("/api/v1/admin/users", admin), ("/api/v1/admin/reference", admin),
                         ("/api/v1/admin/rules", admin), ("/api/v1/admin/audit", admin), ("/api/v1/admin/proposals", admin)):
            for key in ("q", "status", "category", "role", "sort", "order", "action", "classification"):
                r = who.get(url, params={key: payload})
                assert _ok(r), (url, key, payload, r.status_code, r.text[:100])
                if who is user_b and url == "/api/v1/inspections" and r.status_code == 200:
                    assert r.json()["total"] <= baseline and a_id not in r.text, ("widened", key, payload)  # never more than B's own


def test_operator_objects_in_json_bodies_are_rejected(user_a: Actor, admin: Actor) -> None:
    iid = new_inspection(user_a, photos=1)
    bad = {"$ne": None}
    cases = [
        ("PATCH", "/api/v1/me", {"name": bad}),
        ("PATCH", "/api/v1/me", {"designation": {"$set": {"role": "admin"}}}),
        ("POST", f"/api/v1/inspections/{iid}/notes", {"text": bad}),
        ("PATCH", f"/api/v1/inspections/{iid}/fields/brand", {"value": bad}),
        ("PUT", f"/api/v1/inspections/{iid}/decision", {"classification": bad, "remarks": ""}),
        ("POST", "/api/v1/assistant/messages", {"message": bad}),
        ("POST", "/api/v1/assistant/messages", {"message": "x", "web": bad}),
        ("POST", "/api/v1/admin/rules", {"code": bad, "title": "t"}),
        ("PATCH", "/api/v1/admin/settings", {"limits": {"ai_daily_limit_per_user": bad}}),
        ("POST", "/api/v1/admin/users/invites", {"email": bad}),
    ]
    for method, url, body in cases:
        who = admin if "/admin/" in url else user_a
        r = who.req(method, url, json=body)
        assert r.status_code == 422, (method, url, r.status_code, r.text[:100])


def test_dollar_and_dotted_keys_cannot_reach_update_paths(user_a: Actor) -> None:
    iid = new_inspection(user_a, photos=1)
    for key in ("$set", "a.b", "brand.value", "__proto__", "..", "brand%00", "$where", "fields", "x" * 300):
        r = user_a.patch(f"/api/v1/inspections/{iid}/fields/{key}", json={"value": "v"})
        assert r.status_code in (400, 404, 405, 422), (key, r.status_code)
    for body in ({"value": "v", "$set": {"status": "x"}}, {"value": "v", "fields.brand.value": "x"}, {"$unset": {"fields": 1}}):
        assert user_a.patch(f"/api/v1/inspections/{iid}/fields/brand", json=body).status_code == 422
    assert user_a.get(f"/api/v1/inspections/{iid}").status_code == 200


@pytest.mark.parametrize("bad_id", ["x" * 5000, "%00", "../../etc/passwd", "{\"$ne\":1}", "é" * 50, "0" * 24, "null", "-1"])
def test_malformed_ids_give_clean_errors(user_a: Actor, admin: Actor, bad_id: str) -> None:
    for who, tmpl in ((user_a, "/api/v1/inspections/{}"), (user_a, "/api/v1/proposals/{}"), (admin, "/api/v1/admin/users/{}"), (admin, "/api/v1/admin/reference/{}"),
                      (admin, "/api/v1/admin/rules/{}"), (admin, "/api/v1/admin/proposals/{}"), (user_a, "/api/v1/reference-images/{}")):
        r = who.get(tmpl.format(bad_id))
        assert r.status_code in (400, 404, 414, 422), (tmpl, bad_id[:20], r.status_code)
        assert "Traceback" not in r.text and "bson" not in r.text.lower()


def test_pagination_sort_and_limit_abuse(user_a: Actor, admin: Actor) -> None:
    for params in ({"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 100000}, {"page_size": -5}, {"page": 10**15}, {"page": "NaN"}, {"page_size": "1e9"}):
        r = admin.get("/api/v1/admin/audit", params=params)
        assert r.status_code in (200, 422), (params, r.status_code)
        if r.status_code == 200:
            assert len(r.json()["items"]) <= 100
    assert user_a.get("/api/v1/inspections", params={"sort": "owner_uid", "order": "desc"}).status_code in (200, 422)


def test_regex_search_is_escaped_and_bounded(user_a: Actor, admin: Actor) -> None:
    for q in ("(a+)+$", "a" * 100 + "!", "(.*)*" * 20, ".*", "[", "\\", "(?<=a)" * 50):
        t0 = time.monotonic()
        r = admin.get("/api/v1/admin/reference", params={"q": q})
        assert r.status_code in (200, 422), (q[:20], r.status_code)
        assert time.monotonic() - t0 < 3, ("slow regex", q[:20])
        if r.status_code == 200 and q == ".*":
            assert r.json()["total"] == 0 or r.json()["total"] < 5, "`.*` must be matched literally, not as a wildcard"


def _upload(a: Actor, iid: str, name: str, data: bytes, ctype: str, label: str = "front") -> Any:
    return a.post(f"/api/v1/inspections/{iid}/photos", files={"file": (name, data, ctype)}, data={"label": label})


def test_malicious_uploads_are_rejected(user_a: Actor) -> None:
    iid = new_inspection(user_a, photos=0)
    html = b"<html><script>alert(1)</script></html>"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>alert(1)</script></svg>'
    exe = b"MZ\x90\x00" + b"\x00" * 200
    php = b"<?php system($_GET['c']); ?>"
    polyglot = png() + b"<script>alert(1)</script>"
    for name, data, ctype in (("a.html", html, "text/html"), ("a.png", html, "image/png"), ("a.svg", svg, "image/svg+xml"), ("a.png", svg, "image/png"), ("a.exe", exe, "image/png"),
                              ("a.php.png", php, "image/png"), ("", b"", "image/png"), ("../../x.png", png(), "image/png"), ("a.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, "image/png")):
        r = _upload(user_a, iid, name, data, ctype)
        if name == "../../x.png":
            assert r.status_code in (201, 400, 415, 422)  # valid image: stored by id; the file name must not matter
            continue
        assert r.status_code in (400, 413, 415, 422), (name, ctype, r.status_code, r.text[:100])
    r = _upload(user_a, iid, "poly.png", polyglot, "image/png")
    if r.status_code == 201:  # accepted as an image: it must be served as an image, never as HTML
        pid = r.json()["photos"][-1]["id"]
        d = user_a.get(f"/api/v1/inspections/{iid}/photos/{pid}")
        assert d.headers["content-type"].startswith("image/") and d.headers.get("x-content-type-options") == "nosniff"


def test_oversized_and_bomb_images_are_refused_without_crashing(user_a: Actor) -> None:
    iid = new_inspection(user_a, photos=0)
    assert _upload(user_a, iid, "big.png", b"\x89PNG\r\n\x1a\n" + b"0" * (14 * 1024 * 1024), "image/png").status_code in (400, 413, 415, 422)
    buf = io.BytesIO()
    Image.MAX_IMAGE_PIXELS = None
    Image.new("L", (9000, 9000)).save(buf, "PNG", optimize=True)  # ~81 MP of zeros: tiny file, huge when decoded
    t0 = time.monotonic()
    r = _upload(user_a, iid, "bomb.png", buf.getvalue(), "image/png")
    assert r.status_code in (400, 413, 415, 422), r.status_code
    assert time.monotonic() - t0 < 10
    assert user_a.get("/api/v1/inspector/dashboard").status_code == 200  # server still healthy


def test_stored_text_is_returned_verbatim_for_the_frontend_to_escape(user_a: Actor, admin: Actor) -> None:
    xss = '<img src=x onerror=alert(1)><svg onload=alert(1)>"\'`'
    iid = new_inspection(user_a, photos=1)
    r = user_a.post(f"/api/v1/inspections/{iid}/notes", json={"text": xss})
    assert r.status_code in (200, 201)
    assert r.headers["content-type"].startswith("application/json") and r.headers.get("x-content-type-options") == "nosniff"
    assert user_a.patch("/api/v1/me", json={"name": xss}).status_code in (200, 422)
