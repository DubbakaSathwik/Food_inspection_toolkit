from __future__ import annotations

import io
import os
import pathlib
from typing import Any

import httpx
import pytest
from pypdf import PdfReader

from app.db import get_db
from app.services.report_pdf import SECTIONS
from tests.conftest import User, png_bytes


async def _new(u: User) -> str:
    r = await u.post("/api/v1/inspections")
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _upload(u: User, iid: str, label: str = "front", blur: bool = False) -> dict[str, Any]:
    r = await u.post(
        f"/api/v1/inspections/{iid}/photos",
        files={"file": ("a.png", png_bytes(blur=blur), "image/png")},
        data={"label": label},
    )
    assert r.status_code == 201, r.text
    return dict(r.json())


async def _to_analysed(u: User) -> str:
    iid = await _new(u)
    await _upload(u, iid, "front")
    await _upload(u, iid, "back")
    r = await u.post(f"/api/v1/inspections/{iid}/extract")
    assert r.status_code == 200, r.text
    r = await u.post(f"/api/v1/inspections/{iid}/fields/confirm", json={"keys": []})
    assert r.status_code == 200
    r = await u.post(f"/api/v1/inspections/{iid}/analyze")
    assert r.status_code == 200, r.text
    return iid


async def test_create_and_upload_quality(inspector: User) -> None:
    iid = await _new(inspector)
    assert iid.startswith("CS-")
    d = await _upload(inspector, iid, "front")
    assert d["photos"][0]["quality"]["ok"] is True
    d = await _upload(inspector, iid, "back", blur=True)
    q = d["photos"][1]["quality"]
    assert q["ok"] is False and any("blurry" in i for i in q["issues"])
    pid = d["photos"][0]["id"]
    r = await inspector.get(f"/api/v1/inspections/{iid}/photos/{pid}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    r = await inspector.get(f"/api/v1/inspections/{iid}/photos/{pid}?thumb=true")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"


async def test_upload_validation(inspector: User) -> None:
    iid = await _new(inspector)
    r = await inspector.post(
        f"/api/v1/inspections/{iid}/photos",
        files={"file": ("x.png", b"%PDF-1.4 not an image", "image/png")},
    )
    assert r.status_code == 415
    r = await inspector.post(
        f"/api/v1/inspections/{iid}/photos", files={"file": ("e.png", b"", "image/png")}
    )
    assert r.status_code == 400
    for _ in range(5):
        await _upload(inspector, iid)
    r = await inspector.post(
        f"/api/v1/inspections/{iid}/photos", files={"file": ("a.png", png_bytes(), "image/png")}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "too_many_photos"


async def test_crop_and_remove(inspector: User) -> None:
    iid = await _new(inspector)
    d = await _upload(inspector, iid)
    pid = d["photos"][0]["id"]
    r = await inspector.patch(
        f"/api/v1/inspections/{iid}/photos/{pid}",
        json={"crop": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}},
    )
    assert r.status_code == 200 and r.json()["photos"][0]["crop"]["w"] == 0.5
    r = await inspector.patch(
        f"/api/v1/inspections/{iid}/photos/{pid}",
        json={"crop": {"x": 0.8, "y": 0, "w": 0.5, "h": 0.5}},
    )
    assert r.status_code == 422
    r = await inspector.delete(f"/api/v1/inspections/{iid}/photos/{pid}")
    assert r.status_code == 200 and r.json()["photos"] == []
    assert (
        await get_db()["photos.files"].count_documents(
            {"_id": {"$exists": True}, "metadata.inspection_id": iid}
        )
        == 0
    )


async def test_extract_fields_and_corrections(inspector: User) -> None:
    iid = await _new(inspector)
    r = await inspector.post(f"/api/v1/inspections/{iid}/extract")
    assert r.status_code == 400  # no photos
    await _upload(inspector, iid)
    r = await inspector.post(f"/api/v1/inspections/{iid}/extract")
    d = r.json()
    assert d["status"] == "extracted" and d["category"] == "staples"
    fields = {f["key"]: f for f in d["fields"]}
    assert len(fields) == 22
    assert fields["brand"]["status"] == "auto"
    assert fields["mfg_date"]["status"] == "pending"
    assert fields["allergens"]["flag"] == "not_found"
    r = await inspector.post(f"/api/v1/inspections/{iid}/analyze")
    assert r.status_code == 409 and r.json()["error"]["code"] == "fields_unconfirmed"
    r = await inspector.patch(
        f"/api/v1/inspections/{iid}/fields/mfg_date", json={"value": "12/09/2025"}
    )
    f = {x["key"]: x for x in r.json()["fields"]}["mfg_date"]
    assert f["value"] == "12/09/2025" and f["ai_value"] == "12/09/2026" and f["status"] == "edited"
    assert f["history"][-1]["value"] == "12/09/2025"
    r = await inspector.patch(
        f"/api/v1/inspections/{iid}/fields/fssai_licence", json={"value": "123"}
    )
    f = {x["key"]: x for x in r.json()["fields"]}["fssai_licence"]
    assert f["flag"] == "check" and "14 digits" in f["note"]
    r = await inspector.patch(f"/api/v1/inspections/{iid}/fields/not_a_field", json={"value": "x"})
    assert r.status_code == 400


async def test_full_flow_report_and_photo_deletion(inspector: User) -> None:
    iid = await _to_analysed(inspector)
    d = (await inspector.get(f"/api/v1/inspections/{iid}")).json()
    assert d["status"] == "analysed"
    assert d["analysis"]["reference"]["status"] in ("exact", "partial")
    assert d["analysis"]["licence"]["status"] == "found"
    ids = {f["id"] for f in d["findings"]}
    assert "rule-DR-FS-09" in ids  # allergen not found
    assert "rule-DR-CL-03" in ids  # health claim review
    assert d["suggestion"]["provisional"] is True
    r = await inspector.patch(
        f"/api/v1/inspections/{iid}/findings/rule-DR-CL-03",
        json={"action": "corrected", "corrected_value": None},
    )
    assert r.status_code == 422
    r = await inspector.patch(
        f"/api/v1/inspections/{iid}/findings/rule-DR-CL-03",
        json={"action": "dismissed", "note": "Claim substantiated on pack"},
    )
    assert r.status_code == 200
    r = await inspector.post(
        f"/api/v1/inspections/{iid}/report",
        json={"signature_name": "Asha", "confirm_reviewed": True},
    )
    assert r.status_code == 409  # decision missing
    r = await inspector.put(
        f"/api/v1/inspections/{iid}/decision",
        json={"classification": "not_verified", "remarks": "Allergens missing"},
    )
    assert r.status_code == 200
    r = await inspector.post(
        f"/api/v1/inspections/{iid}/report",
        json={"signature_name": "Asha", "confirm_reviewed": False},
    )
    assert r.status_code == 422
    r = await inspector.post(
        f"/api/v1/inspections/{iid}/report",
        json={"signature_name": "Asha Rao", "confirm_reviewed": True},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "completed" and d["photos_deleted"] is True and d["report"]["pages"] >= 2
    assert await get_db()["photos.files"].count_documents({"metadata.inspection_id": iid}) == 0
    r = await inspector.get(f"/api/v1/inspections/{iid}/report.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    if os.environ.get("SAVE_REPORT_PDF"):
        pathlib.Path(os.environ["SAVE_REPORT_PDF"]).write_bytes(r.content)
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    positions = [text.find(s) for s in SECTIONS]
    assert all(p >= 0 for p in positions), [
        s for s, p in zip(SECTIONS, positions, strict=True) if p < 0
    ]
    assert positions == sorted(positions)
    assert "not a certified digital signature" in text
    pid = d["photos"][0]["id"]
    assert (await inspector.get(f"/api/v1/inspections/{iid}/photos/{pid}")).status_code == 404
    r = await inspector.patch(f"/api/v1/inspections/{iid}/fields/brand", json={"value": "X"})
    assert r.status_code == 409  # completed inspections are immutable
    r = await inspector.post(
        f"/api/v1/inspections/{iid}/notes", json={"text": "Follow-up: sample sent to lab"}
    )
    assert r.status_code == 201
    d = (await inspector.get(f"/api/v1/inspections/{iid}")).json()
    assert (
        d["notes"][0]["text"].startswith("Follow-up")
        and d["decision"]["remarks"] == "Allergens missing"
    )


async def test_isolation_between_inspectors(inspector: User, inspector_b: User) -> None:
    iid = await _new(inspector)
    d = await _upload(inspector, iid)
    pid = d["photos"][0]["id"]
    for method, url, kw in [
        ("get", f"/api/v1/inspections/{iid}", {}),
        ("get", f"/api/v1/inspections/{iid}/photos/{pid}", {}),
        ("post", f"/api/v1/inspections/{iid}/extract", {}),
        ("delete", f"/api/v1/inspections/{iid}/photos/{pid}", {}),
        ("patch", f"/api/v1/inspections/{iid}/fields/brand", {"json": {"value": "x"}}),
        ("post", f"/api/v1/inspections/{iid}/notes", {"json": {"text": "x"}}),
        ("get", f"/api/v1/inspections/{iid}/report.pdf", {}),
        ("delete", f"/api/v1/inspections/{iid}", {}),
    ]:
        r = await getattr(inspector_b, method)(url, **kw)
        assert r.status_code == 404, (method, url, r.status_code)
    lst = (await inspector_b.get("/api/v1/inspections")).json()
    assert all(i["id"] != iid for i in lst["items"])
    assert (await inspector.get(f"/api/v1/inspections/{iid}")).status_code == 200


async def test_history_filters_export(inspector: User) -> None:
    iid = await _to_analysed(inspector)
    await inspector.put(
        f"/api/v1/inspections/{iid}/decision", json={"classification": "suspicious", "remarks": ""}
    )
    r = await inspector.get("/api/v1/inspections", params={"q": "muesli"})
    assert any(i["id"] == iid for i in r.json()["items"])
    r = await inspector.get("/api/v1/inspections", params={"classification": "suspicious"})
    assert [i["id"] for i in r.json()["items"]] == [iid]
    r = await inspector.get("/api/v1/inspections", params={"q": '{"$gt": ""}'})
    assert r.status_code == 200 and r.json()["total"] == 0  # operator text treated literally
    r = await inspector.get("/api/v1/inspections", params={"page_size": 500})
    assert r.status_code == 422
    r = await inspector.get("/api/v1/inspections/export", params={"format": "csv"})
    assert r.status_code == 200 and iid in r.text
    r = await inspector.get("/api/v1/inspections/export", params={"format": "xlsx"})
    assert r.status_code == 200 and r.content[:2] == b"PK"
    d = (await inspector.get("/api/v1/inspector/dashboard")).json()
    assert d["total"] >= 1 and d["by_classification"]["suspicious"] >= 1


async def test_provider_failure_marks_incomplete_and_retry(
    inspector: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    iid = await _new(inspector)
    await _upload(inspector, iid)
    monkeypatch.setattr(get_settings(), "ai_provider_order", "fake_fail")
    r = await inspector.post(f"/api/v1/inspections/{iid}/extract")
    d = r.json()
    assert (
        r.status_code == 200
        and d["status"] == "incomplete"
        and d["extraction"]["status"] == "failed"
    )
    assert len(d["photos"]) == 1  # evidence preserved
    monkeypatch.setattr(get_settings(), "ai_provider_order", "fake_fail,fake")
    d = (await inspector.post(f"/api/v1/inspections/{iid}/extract")).json()
    assert d["status"] == "extracted" and d["extraction"]["provider"] == "fake"
    assert [a["ok"] for a in d["extraction"]["attempts"][-2:]] == [False, True]


async def test_ai_quota(inspector: User) -> None:
    from app.repositories import settings as settings_repo  # noqa: F401

    await get_db()["settings"].update_one(
        {"_id": "global"}, {"$set": {"limits.ai_daily_limit_per_user": 1}}, upsert=True
    )
    try:
        iid = await _new(inspector)
        await _upload(inspector, iid)
        assert (await inspector.post(f"/api/v1/inspections/{iid}/extract")).status_code == 200
        r = await inspector.post(f"/api/v1/inspections/{iid}/extract")
        assert r.status_code == 429 and r.json()["error"]["code"] == "ai_quota_exceeded"
    finally:
        await get_db()["settings"].update_one(
            {"_id": "global"}, {"$unset": {"limits.ai_daily_limit_per_user": ""}}
        )


async def test_admin_cannot_use_inspector_api(admin: User) -> None:
    assert (await admin.post("/api/v1/inspections")).status_code == 403


async def test_expired_photo_cleanup(inspector: User, client: httpx.AsyncClient) -> None:
    from datetime import UTC, datetime, timedelta

    from app.services.maintenance import cleanup_expired_photos

    iid = await _new(inspector)
    d = await _upload(inspector, iid)
    await get_db()["photos.files"].update_many(
        {"metadata.inspection_id": iid},
        {"$set": {"metadata.expires_at": datetime.now(UTC) - timedelta(days=1)}},
    )
    res = await cleanup_expired_photos()
    assert res["expired_photos_deleted"] >= 1
    assert (await get_db()["inspections"].find_one({"_id": iid}))["photos_deleted"] is True
    assert (
        await inspector.get(f"/api/v1/inspections/{iid}/photos/{d['photos'][0]['id']}")
    ).status_code == 404
