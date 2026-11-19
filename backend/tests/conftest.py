"""Tests run against a disposable MongoDB database and the Firebase Auth emulator (real token path).

Start services first:
  docker run -d -p 27017:27017 mirror.gcr.io/library/mongo:7
  firebase emulators:start --only auth --project demo-cratescan
"""

from __future__ import annotations

import io
import json
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

os.environ.update(
    {
        "APP_ENV": "test",
        "MONGODB_URI": os.environ.get(
            "TEST_MONGODB_URI", "mongodb://localhost:27017/?directConnection=true"
        ),
        "MONGODB_DB_NAME": "crate_scan_test",
        "FIREBASE_PROJECT_ID": "demo-cratescan",
        "FIREBASE_AUTH_EMULATOR_HOST": os.environ.get(
            "FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099"
        ),
        "AI_PROVIDER_ORDER": "fake",
        "SUPER_ADMIN_EMAIL": "root@example.com",
        "CORS_ALLOWED_ORIGINS": "http://localhost:3000",
        "OCR_ENABLED": "false",
    }
)
os.environ.pop("FIREBASE_SERVICE_ACCOUNT_JSON", None)

import httpx
import pytest
from asgi_lifespan import LifespanManager
from firebase_admin import auth as fb_auth
from PIL import Image, ImageDraw

from app.auth import init_firebase
from app.db import get_client, get_db
from app.main import app
from migrations.runner import run as run_migrations

EMU = os.environ["FIREBASE_AUTH_EMULATOR_HOST"]


@pytest.fixture(scope="session", autouse=True)
async def database() -> AsyncIterator[None]:
    await get_client().drop_database("crate_scan_test")
    await run_migrations(get_db())
    init_firebase()
    # Emulator accounts are NOT wiped: a shared local emulator also serves the dev stack / e2e tests.
    # Test users have unique emails and the test database is dropped, so stale accounts are harmless.
    yield
    await get_client().drop_database("crate_scan_test")


@pytest.fixture(scope="session")
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


def emulator_sign_in(email: str, sub: str, name: str = "Test User", verified: bool = True) -> str:
    """Google sign-in against the Auth emulator; returns a real (emulator-signed) ID token."""
    id_token = json.dumps({"sub": sub, "email": email, "email_verified": verified, "name": name})
    r = httpx.post(
        f"http://{EMU}/identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=fake-api-key",
        json={
            "postBody": f"id_token={id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnSecureToken": True,
            "returnIdpCredential": True,
        },
    )
    r.raise_for_status()
    return str(r.json()["idToken"])


class User:
    def __init__(self, client: httpx.AsyncClient, email: str, name: str) -> None:
        self.client, self.email, self.name = client, email, name
        self.sub = uuid.uuid4().hex[:20]
        self.token = emulator_sign_in(email, self.sub, name)
        self.uid: str = ""

    def refresh(self) -> None:
        self.token = emulator_sign_in(self.email, self.sub, self.name)

    @property
    def h(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def me(self) -> dict[str, Any]:
        r = await self.client.get("/api/v1/me", headers=self.h)
        assert r.status_code == 200, r.text
        data: dict[str, Any] = r.json()
        self.uid = data["uid"]
        if data["claims_stale"]:
            self.refresh()
        return data

    async def get(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.get(url, headers=self.h, **kw)

    async def post(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.post(url, headers=self.h, **kw)

    async def patch(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.patch(url, headers=self.h, **kw)

    async def put(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.put(url, headers=self.h, **kw)

    async def delete(self, url: str, **kw: Any) -> httpx.Response:
        return await self.client.delete(url, headers=self.h, **kw)


async def make_user(
    client: httpx.AsyncClient,
    role: str | None = "inspector",
    email: str | None = None,
    name: str | None = None,
) -> User:
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    u = User(client, email, name or email.split("@")[0].title())
    await u.me()
    if role:
        await get_db()["users"].update_one(
            {"_id": u.uid}, {"$set": {"role": role, "status": "active"}}
        )
        fb_auth.set_custom_user_claims(u.uid, {"role": role, "active": True})
        u.refresh()
    return u


@pytest.fixture
async def inspector(client: httpx.AsyncClient) -> User:
    return await make_user(client, "inspector")


@pytest.fixture
async def inspector_b(client: httpx.AsyncClient) -> User:
    return await make_user(client, "inspector")


@pytest.fixture
async def admin(client: httpx.AsyncClient) -> User:
    return await make_user(client, "admin")


@pytest.fixture(scope="session")
async def super_admin(client: httpx.AsyncClient) -> User:
    u = User(client, "root@example.com", "Root Admin")
    await u.me()
    await u.me()
    return u


def png_bytes(
    text: str = "HARVEST LANE MUESLI", size: tuple[int, int] = (900, 700), blur: bool = False
) -> bytes:
    img = Image.new("RGB", size, (250, 248, 240))
    d = ImageDraw.Draw(img)
    for i in range(0, size[1], 28):
        d.text((20, i), f"{text} {i} FSSAI 10012022001234 MRP 245", fill=(20, 20, 20))
        d.line([(0, i + 20), (size[0], i + 20)], fill=(60, 90, 40), width=2)
    if blur:
        from PIL import ImageFilter

        img = img.filter(ImageFilter.GaussianBlur(8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
