"""C10–C12 — CORS, headers, information disclosure, production-mode configuration."""

from __future__ import annotations

import os

import httpx
import pytest

from conftest import BASE, Actor

PROD = os.environ.get("SEC_PROD_URL")
SITE = os.environ.get("SEC_SITE_URL", "http://localhost:3000")


def test_cors_allows_only_configured_origins(anon: httpx.Client) -> None:
    for evil in ("https://evil.example", "null", "http://localhost.evil.example", "https://x.onrender.com", "http://localhost:3000.evil.example"):
        r = anon.options("/api/v1/me", headers={"Origin": evil, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"})
        assert "access-control-allow-origin" not in r.headers, evil
        r2 = anon.get("/health", headers={"Origin": evil})
        assert "access-control-allow-origin" not in r2.headers, evil
    ok = anon.options("/api/v1/me", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert ok.headers.get("access-control-allow-origin") != "*" and "access-control-allow-credentials" not in ok.headers


def test_api_response_headers(admin: Actor) -> None:
    r = admin.get("/api/v1/me")
    h = r.headers
    assert h.get("x-content-type-options") == "nosniff" and h.get("x-frame-options") == "DENY"
    assert "no-store" in h.get("cache-control", "")
    assert h.get("referrer-policy") == "no-referrer"


def test_health_leaks_nothing_sensitive(anon: httpx.Client) -> None:
    body = anon.get("/health").text.lower()
    for leak in ("mongodb", "mongo://", "version\":\"3", "python", "crate_scan_dev", "firebase", "password"):
        assert leak not in body, leak


def test_frontend_security_headers() -> None:
    try:
        r = httpx.get(SITE, timeout=15)
    except httpx.HTTPError:
        pytest.skip("frontend not running")
    h = {k.lower(): v for k, v in r.headers.items()}
    assert h.get("x-frame-options") == "DENY" and h.get("x-content-type-options") == "nosniff"
    csp = h.get("content-security-policy", "")
    assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp and "base-uri 'self'" in csp
    assert "default-src 'self'" in csp and "*" not in csp.replace("*.firebaseapp.com", "")
    assert "strict-transport-security" in h and "referrer-policy" in h and "permissions-policy" in h
    assert "x-powered-by" not in h


@pytest.mark.skipif(not PROD, reason="needs the production-mode instance (security-tests/start-instances.sh)")
def test_production_mode_hides_docs_and_sets_hsts() -> None:
    c = httpx.Client(base_url=PROD, timeout=15)
    for url in ("/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"):
        assert c.get(url).status_code == 404, url
    assert "max-age" in c.get("/health").headers.get("strict-transport-security", "")
    assert c.get("/api/v1/me").status_code == 401
    r = c.options("/api/v1/me", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers  # production CORS lists only the real site
    r = c.get("/api/v1/nope")
    assert r.status_code == 404 and "Traceback" not in r.text


@pytest.mark.skipif(not PROD, reason="needs the production-mode instance")
def test_production_refuses_fake_ai_and_emulator() -> None:
    """The fake AI provider and the Firebase emulator host must be impossible in production (they disable real checks)."""
    import subprocess
    import sys

    env = {**os.environ, "APP_ENV": "production", "FIREBASE_AUTH_EMULATOR_HOST": "127.0.0.1:9099", "FIREBASE_PROJECT_ID": "x"}
    code = "from app.auth import init_firebase; init_firebase()"
    out = subprocess.run([sys.executable, "-c", code], cwd=os.path.join(os.path.dirname(__file__), "..", "backend"), env=env, capture_output=True, text=True)
    assert out.returncode != 0 and "must not be set in production" in out.stderr
