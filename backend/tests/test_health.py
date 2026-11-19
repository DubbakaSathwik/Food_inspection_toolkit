from __future__ import annotations

import httpx

from tests.conftest import make_user


async def test_health(client: httpx.AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    head = await client.head("/health")  # uptime monitors often use HEAD
    assert head.status_code == 200


async def test_nosql_operators_are_treated_as_data(client: httpx.AsyncClient) -> None:
    u = await make_user(client, "inspector")
    created = (await u.post("/api/v1/inspections")).json()
    # Operator objects in JSON bodies are rejected by strict models (422), never passed to MongoDB.
    url = f"/api/v1/inspections/{created['id']}/fields/confirm"
    assert (await u.post(url, json={"keys": {"$ne": None}})).status_code == 422
    assert (await u.post(url, json={"keys": [], "$where": "sleep(1000)"})).status_code == 422
    # Operator-looking text in query strings is matched literally (escaped regex): no results.
    r = await u.get("/api/v1/inspections", params={"q": '{"$ne": null}'})
    assert r.status_code == 200 and r.json()["total"] == 0
    r = await u.get("/api/v1/inspections", params={"q": ".*"})
    assert r.json()["total"] == 0


async def test_unknown_route_uses_error_format(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


async def test_cors_allows_only_configured_origin(client: httpx.AsyncClient) -> None:
    ok = await client.options(
        "/api/v1/me",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = await client.options(
        "/api/v1/me",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers


async def test_body_size_limit(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/v1/assistant/messages",
        content=b"x" * (2 * 1024 * 1024),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 413


async def test_public_site_images_empty(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/public/site-images")
    assert r.status_code == 200
    assert set(r.json()) == {"hero", "signin", "banner"}
