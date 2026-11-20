"""C9 — race conditions and rate limits (short bursts only; no denial-of-service)."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from conftest import BASE, Actor, _activate, emulator_token


def test_ai_daily_quota_is_atomic_under_parallel_requests(admin: Actor) -> None:
    cur = admin.get("/api/v1/admin/settings").json()
    limits = cur["limits"]
    try:
        assert admin.patch("/api/v1/admin/settings", json={"limits": {**limits, "ai_daily_limit_per_user": 5}}).status_code == 200
        u = _activate(admin, "RACE")

        def ask(i: int) -> int:
            return u.post("/api/v1/assistant/messages", json={"message": f"q{i}"}).status_code

        with ThreadPoolExecutor(30) as ex:
            codes = list(ex.map(ask, range(30)))
        ok = codes.count(200)
        assert ok <= 5, f"quota bypassed by parallel requests: {ok} successes with a limit of 5 ({sorted(set(codes))})"
        assert ok >= 1 and all(c in (200, 429) for c in codes), sorted(set(codes))
    finally:
        admin.patch("/api/v1/admin/settings", json={"limits": limits})


def test_parallel_creates_yield_unique_ids_and_no_errors(admin: Actor) -> None:
    u = _activate(admin, "PAR")
    with ThreadPoolExecutor(25) as ex:
        res = list(ex.map(lambda _: u.post("/api/v1/inspections"), range(25)))
    assert all(r.status_code == 201 for r in res), sorted({r.status_code for r in res})
    ids = [r.json()["id"] for r in res]
    assert len(set(ids)) == 25, "duplicate inspection numbers under concurrency"


def test_parallel_status_transitions_do_not_corrupt(admin: Actor) -> None:
    from conftest import new_inspection

    u = _activate(admin, "TRANS")
    iid = new_inspection(u)
    with ThreadPoolExecutor(10) as ex:
        codes = list(ex.map(lambda _: u.post(f"/api/v1/inspections/{iid}/extract").status_code, range(10)))
    assert all(c in (200, 409, 429) for c in codes), sorted(set(codes))
    assert u.get(f"/api/v1/inspections/{iid}").status_code == 200


RATE = os.environ.get("SEC_RATELIMIT_URL")


@pytest.mark.skipif(not RATE, reason="needs the rate-limit instance (security-tests/start-instances.sh)")
def test_rate_limit_applies_and_x_forwarded_for_cannot_bypass_it() -> None:
    """SEC-003: behind Render the app trusts X-Forwarded-For (forwarded-allow-ips '*'). If the left-most value is
    attacker-controlled, rotating it gives every request its own bucket and the limiter never fires."""
    c = httpx.Client(base_url=RATE, timeout=15)
    plain = [c.get("/health").status_code for _ in range(10)]
    assert 429 in plain, plain  # the limiter itself works for one client
    c2 = httpx.Client(base_url=RATE, timeout=15)
    spoofed = [c2.get("/api/v1/public/site-images", headers={"X-Forwarded-For": f"203.0.113.{i}"}).status_code for i in range(40)]
    assert 429 in spoofed, f"rate limit bypassed by spoofed X-Forwarded-For: {sorted(set(spoofed))}"
