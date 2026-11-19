"""Attack-test identities and helpers. Raw HTTP only (httpx): the UI is never involved.

Environment (never put tokens in source):
  SEC_API_URL        API under test            default http://localhost:8000   (local stack / staging only)
  SEC_EMULATOR       Firebase Auth emulator    default 127.0.0.1:9099
  SEC_ADMIN_EMAIL    seeded Super Admin email  default admin@example.com
  SEC_ALLOW_REMOTE=1 required to run against a non-local URL (staging). NEVER point this at production data.
"""

from __future__ import annotations

import io
import json
import os
import re
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
from PIL import Image, ImageDraw

BASE = os.environ.get("SEC_API_URL", "http://localhost:8000").rstrip("/")
EMU = os.environ.get("SEC_EMULATOR", "127.0.0.1:9099")
ADMIN_EMAIL = os.environ.get("SEC_ADMIN_EMAIL", "admin@example.com")

if urlparse(BASE).hostname not in ("localhost", "127.0.0.1") and os.environ.get("SEC_ALLOW_REMOTE") != "1":
    raise SystemExit(f"Refusing to attack {BASE}: set SEC_ALLOW_REMOTE=1 only for a dedicated staging stack.")

_TOKEN = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]*")


def redact(text: str) -> str:
    return _TOKEN.sub("<token>", text)


def emulator_token(email: str, sub: str, verified: bool = True, name: str = "Sec Test") -> str:
    idt = json.dumps({"sub": sub, "email": email, "email_verified": verified, "name": name})
    r = httpx.post(
        f"http://{EMU}/identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=fake-api-key",
        json={
            "postBody": f"id_token={idt}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnSecureToken": True,
            "returnIdpCredential": True,
        },
    )
    r.raise_for_status()
    return str(r.json()["idToken"])


class Actor:
    def __init__(self, label: str, email: str, sub: str, verified: bool = True) -> None:
        self.label, self.email, self.sub, self.verified = label, email, sub, verified
        self.http = httpx.Client(base_url=BASE, timeout=30)
        self.token = emulator_token(email, sub, verified)
        self.uid = ""

    def refresh(self) -> None:
        self.token = emulator_token(self.email, self.sub, self.verified)

    @property
    def h(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def req(self, method: str, url: str, **kw: Any) -> httpx.Response:
        headers = {**self.h, **kw.pop("headers", {})}
        return self.http.request(method, url, headers=headers, **kw)

    def get(self, url: str, **kw: Any) -> httpx.Response:
        return self.req("GET", url, **kw)

    def post(self, url: str, **kw: Any) -> httpx.Response:
        return self.req("POST", url, **kw)

    def patch(self, url: str, **kw: Any) -> httpx.Response:
        return self.req("PATCH", url, **kw)

    def put(self, url: str, **kw: Any) -> httpx.Response:
        return self.req("PUT", url, **kw)

    def delete(self, url: str, **kw: Any) -> httpx.Response:
        return self.req("DELETE", url, **kw)


def png(text: str = "TEST", size: tuple[int, int] = (640, 480)) -> bytes:
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    for i in range(0, size[0], 40):
        d.line([(i, 0), (i, size[1])], fill="black", width=2)
    d.text((20, 20), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def anon() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=30)


@pytest.fixture(scope="session")
def admin() -> Actor:
    """Seeded Super Admin (created by backend/scripts/dev_seed.py or bootstrap by SUPER_ADMIN_EMAIL)."""
    a = Actor("ADMIN", ADMIN_EMAIL, f"sub-{ADMIN_EMAIL}")
    me = a.get("/api/v1/me").json()
    if me["role"] != "super_admin":
        a.refresh()
        me = a.get("/api/v1/me").json()
    assert me["role"] == "super_admin", "Start the local stack with --fresh so the Super Admin exists"
    a.uid = me["uid"]
    return a


def _activate(admin: Actor, label: str, role: str = "inspector") -> Actor:
    tag = uuid.uuid4().hex[:8]
    a = Actor(label, f"sec-{label.lower()}-{tag}@example.com", f"sec{tag}{label.lower()}")
    me = a.get("/api/v1/me")
    assert me.status_code == 200, me.text
    a.uid = me.json()["uid"]
    assert me.json()["status"] == "pending"  # new accounts never start active
    r = admin.post(f"/api/v1/admin/users/{a.uid}/approve", json={"role": role})
    assert r.status_code == 200, r.text
    a.refresh()
    assert a.get("/api/v1/me").json()["status"] == "active"
    return a


@pytest.fixture(scope="session")
def user_a(admin: Actor) -> Actor:
    return _activate(admin, "A")


@pytest.fixture(scope="session")
def user_b(admin: Actor) -> Actor:
    return _activate(admin, "B")


@pytest.fixture(scope="session")
def plain_admin(admin: Actor) -> Actor:
    """An `admin` (not super_admin) account."""
    return _activate(admin, "ADM", role="admin")


@pytest.fixture(scope="session")
def pending(admin: Actor) -> Actor:
    tag = uuid.uuid4().hex[:8]
    a = Actor("PENDING", f"sec-pending-{tag}@example.com", f"secp{tag}")
    a.uid = a.get("/api/v1/me").json()["uid"]
    return a


@pytest.fixture(scope="session")
def unverified() -> Actor:
    """Signed in with an UNVERIFIED email."""
    tag = uuid.uuid4().hex[:8]
    return Actor("UNVERIFIED", f"sec-unverified-{tag}@example.com", f"unv{tag}", verified=False)


@pytest.fixture(scope="session")
def openapi(anon: httpx.Client) -> dict[str, Any]:
    r = anon.get("/openapi.json")
    assert r.status_code == 200, "OpenAPI is off; run against a development instance to enumerate routes"
    return dict(r.json())


def new_inspection(a: Actor, photos: int = 2) -> str:
    r = a.post("/api/v1/inspections")
    assert r.status_code == 201, r.text
    iid = str(r.json()["id"])
    for label in ("front", "back")[:photos]:
        up = a.post(f"/api/v1/inspections/{iid}/photos", files={"file": ("p.png", png(label), "image/png")}, data={"label": label})
        assert up.status_code == 201, up.text
    return iid
