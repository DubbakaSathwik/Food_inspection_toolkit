from __future__ import annotations

import io

from openpyxl import Workbook

from tests.conftest import User, png_bytes
from tests.test_inspections import _to_analysed

REF = {
    "product_name": "Demo Oat Biscuits",
    "brand": "Testbrand",
    "variant": "Classic",
    "category": "snacks",
    "net_quantity": "200 g",
    "package_sizes": ["200 g"],
    "gtin": "8900000000017",
    "manufacturer": {"name": "Testbrand Foods Pvt Ltd", "facility_address": "Plot 1, Pune"},
    "licence": {"number": "11122233344455", "status": "active", "valid_until": "2030-01-01"},
}


async def test_reference_crud_archive_delete(
    admin: User, super_admin: User, inspector: User
) -> None:
    r = await admin.post("/api/v1/admin/reference", json=REF)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["demo"] is True
    bad = dict(REF, licence={"number": "123"})
    assert (await admin.post("/api/v1/admin/reference", json=bad)).status_code == 422
    assert (
        await admin.post("/api/v1/admin/reference", json=dict(REF, status="archived"))
    ).status_code == 422
    r = await admin.patch(
        f"/api/v1/admin/reference/{rid}",
        json={"licence": {**REF["licence"], "status": "suspended"}},
    )
    assert r.status_code == 200 and r.json()["licence"]["status"] == "suspended"
    r = await admin.get("/api/v1/admin/reference", params={"q": "testbrand"})
    assert r.json()["total"] >= 1
    assert (await inspector.get("/api/v1/admin/reference")).status_code == 403
    r = await admin.post(f"/api/v1/admin/reference/{rid}/archive")
    assert r.json()["status"] == "archived"
    assert (await admin.post(f"/api/v1/admin/reference/{rid}/restore")).json()["status"] == "active"
    assert (await admin.delete(f"/api/v1/admin/reference/{rid}")).status_code == 403
    r = await super_admin.get("/api/v1/admin/audit", params={"q": rid})
    actions = {a["action"] for a in r.json()["items"]}
    assert {"reference.create", "reference.licence_change", "reference.archive"} <= actions
    assert (await super_admin.delete(f"/api/v1/admin/reference/{rid}")).status_code == 200


async def test_packaging_versions_and_images(admin: User, inspector: User) -> None:
    rid = (await admin.post("/api/v1/admin/reference", json=REF)).json()["id"]
    r = await admin.post(
        f"/api/v1/admin/reference/{rid}/versions", data={"label": "2026 design", "notes": "new"}
    )
    assert r.status_code == 201
    vid = r.json()["packaging_versions"][0]["id"]
    r = await admin.post(
        f"/api/v1/admin/reference/{rid}/versions/{vid}/images",
        files={"file": ("f.png", png_bytes(), "image/png")},
        data={"side": "front"},
    )
    assert r.status_code == 201, r.text
    fid = r.json()["packaging_versions"][0]["images"][0]["file_id"]
    assert (await inspector.get(f"/api/v1/reference-images/{fid}")).status_code == 200
    r = await admin.delete(f"/api/v1/admin/reference/{rid}/images/{fid}")
    assert r.status_code == 200 and r.json()["packaging_versions"][0]["images"] == []
    assert (await inspector.get(f"/api/v1/reference-images/{fid}")).status_code == 404


async def test_ai_assisted_entry_returns_draft_only(admin: User) -> None:
    before = (await admin.get("/api/v1/admin/reference/stats")).json()["active"]
    r = await admin.post(
        "/api/v1/admin/reference/ai-extract", files=[("files", ("a.png", png_bytes(), "image/png"))]
    )
    assert r.status_code == 200, r.text
    assert (
        r.json()["draft"]["brand"] == "Harvest Lane"
        and r.json()["draft"]["source"] == "ai_assisted"
    )
    assert (await admin.get("/api/v1/admin/reference/stats")).json()["active"] == before


async def test_import_preview_and_commit(admin: User) -> None:
    csv_data = (
        b"product_name,brand,category,net_quantity,licence_number,gtin\n"
        b"Imported Tea,Leafy,beverages,250 g,10012022009999,8900000000024\n"
        b"Bad Row,,snacks,,123,\n"
    )
    r = await admin.post(
        "/api/v1/admin/reference/import/preview", files={"file": ("refs.csv", csv_data, "text/csv")}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] == 1 and body["invalid"] == 1
    assert body["rows"][1]["errors"]
    valid = [row["data"] for row in body["rows"] if not row["errors"]]
    r = await admin.post("/api/v1/admin/reference/import/commit", json={"rows": valid})
    assert r.status_code == 200 and r.json()["created"] == 1
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["product_name", "brand", "category"])
    ws.append(["Xl Product", "Xl Brand", "dairy"])
    buf = io.BytesIO()
    wb.save(buf)
    r = await admin.post(
        "/api/v1/admin/reference/import/preview",
        files={"file": ("refs.xlsx", buf.getvalue(), "application/octet-stream")},
    )
    assert r.status_code == 200 and r.json()["valid"] == 1
    r = await admin.post(
        "/api/v1/admin/reference/import/preview", files={"file": ("refs.txt", b"x", "text/plain")}
    )
    assert r.status_code == 415


async def test_rules_crud_history_and_validation(admin: User) -> None:
    rule = {
        "code": "DR-TS-01",
        "title": "Test rule",
        "category": "snacks",
        "check_type": "required_field",
        "field": "batch",
        "requirement": "Batch required",
        "status": "active",
    }
    r = await admin.post("/api/v1/admin/rules", json=rule)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert (await admin.post("/api/v1/admin/rules", json=rule)).status_code == 409
    assert (
        await admin.post("/api/v1/admin/rules", json=dict(rule, code="DR-TS-02", field="nope"))
    ).status_code == 422
    assert (
        await admin.post(
            "/api/v1/admin/rules",
            json=dict(rule, code="DR-TS-03", check_type="pattern", pattern="("),
        )
    ).status_code == 422
    r = await admin.patch(
        f"/api/v1/admin/rules/{rid}", json={"severity": "high", "change_note": "Stricter"}
    )
    assert r.json()["version"] == 2 and r.json()["history"][-1]["changes"]["severity"] == [
        "warning",
        "high",
    ]
    r = await admin.patch(f"/api/v1/admin/rules/{rid}", json={"check_type": "pattern"})
    assert r.status_code == 422  # pattern rule without pattern
    r = await admin.post(f"/api/v1/admin/rules/{rid}/archive")
    assert r.json()["status"] == "archived"
    stats = (await admin.get("/api/v1/admin/rules/stats")).json()
    assert stats["active"] >= 10


async def test_proposal_lifecycle(inspector: User, inspector_b: User, admin: User) -> None:
    iid = await _to_analysed(inspector)
    prod = {
        "product_name": "New Granola",
        "brand": "Unknownbrand",
        "category": "staples",
        "fssai_licence": "10012022007777",
    }
    r = await inspector.post(
        "/api/v1/proposals", json={"inspection_id": iid, "product": prod, "remarks": "Not in DB"}
    )
    assert r.status_code == 409  # report first
    await inspector.put(
        f"/api/v1/inspections/{iid}/decision",
        json={"classification": "not_verified", "remarks": ""},
    )
    await inspector.post(
        f"/api/v1/inspections/{iid}/report",
        json={"signature_name": "Asha", "confirm_reviewed": True},
    )
    r = await inspector_b.post("/api/v1/proposals", json={"inspection_id": iid, "product": prod})
    assert r.status_code == 404  # not B's inspection
    r = await inspector.post(
        "/api/v1/proposals", json={"inspection_id": iid, "product": prod, "remarks": "Not in DB"}
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert (
        await inspector.post("/api/v1/proposals", json={"inspection_id": iid, "product": prod})
    ).status_code == 409
    assert (await inspector_b.get(f"/api/v1/proposals/{pid}")).status_code == 404
    r = await admin.post(f"/api/v1/admin/proposals/{pid}/decision", json={"outcome": "rejected"})
    assert r.status_code == 422
    r = await admin.post(
        f"/api/v1/admin/proposals/{pid}/decision",
        json={"outcome": "info_requested", "note": "Send back label"},
    )
    assert r.json()["status"] == "info_requested"
    r = await inspector.post(
        f"/api/v1/proposals/{pid}/reply", json={"message": "Attached in report"}
    )
    assert r.json()["status"] == "pending" and r.json()["messages"][-1]["from"] == "inspector"
    assert (await admin.get(f"/api/v1/admin/proposals/{pid}/report.pdf")).status_code == 200
    r = await admin.post(
        f"/api/v1/admin/proposals/{pid}/decision", json={"outcome": "approved", "note": "Added"}
    )
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["reference_id"]
    ref = (await admin.get(f"/api/v1/admin/reference/{r.json()['reference_id']}")).json()
    assert ref["source"] == "proposal" and ref["demo"] is True
    r = await admin.post(
        f"/api/v1/admin/proposals/{pid}/decision", json={"outcome": "rejected", "note": "x"}
    )
    assert r.status_code == 409
    mine = (await inspector.get("/api/v1/proposals")).json()
    assert mine["items"][0]["status"] == "approved"


async def test_settings_and_site_images(admin: User, client: object, inspector: User) -> None:
    r = await admin.get("/api/v1/admin/settings")
    assert r.status_code == 200
    s = r.json()
    assert {p["name"] for p in s["providers"]} == {"fake"}
    assert "key" not in str(s["providers"]).lower()
    r = await admin.patch(
        "/api/v1/admin/settings",
        json={
            "general": {"org_name": "Test Org", "report_footer": "x", "auto_confirm_threshold": 0.9}
        },
    )
    assert r.json()["general"]["org_name"] == "Test Org"
    assert (
        await admin.patch(
            "/api/v1/admin/settings",
            json={"limits": {"ai_daily_limit_per_user": 0, "photo_retention_days": 7}},
        )
    ).status_code == 422
    r = await admin.put(
        "/api/v1/admin/settings/images/hero", files={"file": ("h.png", png_bytes(), "image/png")}
    )
    assert r.status_code == 200 and r.json()["images"]["hero"]["file_id"]
    pub = (await inspector.client.get("/api/v1/public/site-images")).json()
    assert pub["hero"]["url"].startswith("/api/v1/public/site-images/hero")
    img = await inspector.client.get("/api/v1/public/site-images/hero")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    r = await admin.delete("/api/v1/admin/settings/images/hero")
    assert r.json()["images"]["hero"] is None
    assert (await inspector.client.get("/api/v1/public/site-images/hero")).status_code == 404
    assert (await inspector.patch("/api/v1/admin/settings", json={})).status_code == 403


async def test_dashboard_analytics_audit_storage(admin: User) -> None:
    for url in (
        "/api/v1/admin/dashboard",
        "/api/v1/admin/analytics",
        "/api/v1/admin/storage",
        "/api/v1/admin/audit",
    ):
        r = await admin.get(url)
        assert r.status_code == 200, (url, r.text)
    a = (await admin.get("/api/v1/admin/analytics")).json()
    assert a["storage"]["limit_mb"] == 512 and "photos" in a["storage"]["buckets"]
    r = await admin.get("/api/v1/admin/audit/export")
    assert (
        r.status_code == 200 and r.text.splitlines()[0].startswith("﻿Time")
    ) or "Time (UTC)" in r.text
    r = await admin.post("/api/v1/admin/storage/cleanup")
    assert r.status_code == 200
    # audit log is read-only: no mutation routes exist
    assert (await admin.delete("/api/v1/admin/audit")).status_code == 405


async def test_users_listing_and_detail(admin: User, inspector: User) -> None:
    r = await admin.get("/api/v1/admin/users", params={"role": "inspector", "status": "active"})
    assert r.status_code == 200 and r.json()["total"] >= 1
    r = await admin.get(f"/api/v1/admin/users/{inspector.uid}")
    assert r.status_code == 200 and r.json()["email"] == inspector.email
    assert (await admin.get("/api/v1/admin/users", params={"status": "weird"})).status_code == 422


async def test_diagnostics_admin_only_and_secret_free(admin: User, inspector: User) -> None:
    assert (await inspector.get("/api/v1/admin/diagnostics")).status_code == 403
    assert (await inspector.post("/api/v1/admin/diagnostics/config")).status_code == 403
    items = (await admin.get("/api/v1/admin/diagnostics")).json()
    ids = [i["id"] for i in items]
    assert {"config", "database", "storage", "firebase", "gemini", "ocr"} <= set(ids)
    results = {}
    for cid in ids:
        r = await admin.post(f"/api/v1/admin/diagnostics/{cid}")
        assert r.status_code == 200, r.text
        results[cid] = r.json()
        assert results[cid]["status"] in ("ok", "warn", "fail", "skip")
    assert results["database"]["status"] == "ok"
    assert results["storage"]["status"] == "ok"
    assert results["gemini"]["status"] == "skip"  # test environment uses the fake provider only
    body = str(results).lower()
    assert "mongodb://" not in body and "private_key" not in body
    assert (await admin.post("/api/v1/admin/diagnostics/nope")).status_code == 404
