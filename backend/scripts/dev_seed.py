"""Local development data through the real API (emulator + fake AI only). Never for production.

`uv run python -m scripts.dev_seed` with the API on :8000 and the Auth emulator on :9099."""

from __future__ import annotations

import io
import json
import os

import httpx
from PIL import Image, ImageDraw, ImageFilter

API = os.environ.get("SEED_API", "http://localhost:8000")
if not API.startswith(("http://localhost", "http://127.0.0.1")):
    raise SystemExit(
        "dev_seed only runs against a LOCAL API (it creates demo accounts and data). Never use it on a real deployment."
    )
EMU = os.environ.get("SEED_EMULATOR", "http://127.0.0.1:9099")


def token(email: str, name: str) -> str:
    id_token = json.dumps(
        {"sub": f"sub-{email}", "email": email, "email_verified": True, "name": name}
    )
    r = httpx.post(
        f"{EMU}/identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=demo-api-key",
        json={
            "postBody": f"id_token={id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnSecureToken": True,
        },
    )
    r.raise_for_status()
    return str(r.json()["idToken"])


def client(email: str, name: str) -> httpx.Client:
    return httpx.Client(
        base_url=API, headers={"Authorization": f"Bearer {token(email, name)}"}, timeout=60
    )


def pack(title: str, color: tuple[int, int, int], blur: bool = False) -> bytes:
    img = Image.new("RGB", (1000, 760), (236, 232, 220))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        (330, 90, 670, 690), 18, fill=(250, 247, 238), outline=(150, 160, 130), width=3
    )
    d.rectangle((330, 90, 670, 230), fill=color)
    for i, line in enumerate(
        [
            title,
            "Harvest Lane · Nut & Seed Mix",
            "FSSAI 10012022001234",
            "Net wt 500 g  MRP 245.00",
            "Batch HL-0926-B",
            "Mfd 12/09/2026",
        ]
    ):
        d.text((350, 250 + i * 34), line, fill=(30, 30, 25))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(6))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def new_inspection(c: httpx.Client, photos: list[tuple[str, bool]]) -> str:
    iid = c.post("/api/v1/inspections").raise_for_status().json()["id"]
    c.put(f"/api/v1/inspections/{iid}/category", json={"category": "staples"}).raise_for_status()
    for label, blur in photos:
        c.post(
            f"/api/v1/inspections/{iid}/photos",
            files={
                "file": ("p.jpg", pack("Whole Grain Muesli", (86, 112, 58), blur), "image/jpeg")
            },
            data={"label": label},
        ).raise_for_status()
    return str(iid)


def main() -> None:
    admin = client("admin@example.com", "Asha Admin")
    if admin.get("/api/v1/me").raise_for_status().json()["claims_stale"]:
        admin = client("admin@example.com", "Asha Admin")  # fresh token carries the new role claim
    insp = client("inspector@example.com", "Ravi Inspector")
    me = insp.get("/api/v1/me").json()
    if me["status"] != "active":
        admin.post(
            f"/api/v1/admin/users/{me['uid']}/approve", json={"role": "inspector"}
        ).raise_for_status()
        insp = client("inspector@example.com", "Ravi Inspector")
    client("pending.person@example.com", "Priya Pending").get("/api/v1/me")

    # 1) completed inspection with report + proposal
    a = new_inspection(insp, [("front", False), ("back", False)])
    insp.post(f"/api/v1/inspections/{a}/extract").raise_for_status()
    insp.post(f"/api/v1/inspections/{a}/fields/confirm", json={"keys": []}).raise_for_status()
    insp.post(f"/api/v1/inspections/{a}/analyze").raise_for_status()
    insp.put(
        f"/api/v1/inspections/{a}/decision",
        json={
            "classification": "not_verified",
            "remarks": "Allergen declaration not visible on pack.",
        },
    ).raise_for_status()
    insp.post(
        f"/api/v1/inspections/{a}/report",
        json={"signature_name": "Ravi Inspector", "confirm_reviewed": True},
    ).raise_for_status()
    insp.post(
        "/api/v1/proposals",
        json={
            "inspection_id": a,
            "product": {
                "product_name": "Whole Grain Muesli 1 kg",
                "brand": "Harvest Lane",
                "category": "staples",
                "net_quantity": "1 kg",
                "fssai_licence": "10012022001234",
            },
            "remarks": "1 kg pack not in reference database.",
        },
    )
    # 2) analysed (awaiting review)
    b = new_inspection(insp, [("front", False), ("back", False), ("side", True)])
    insp.post(f"/api/v1/inspections/{b}/extract").raise_for_status()
    insp.post(f"/api/v1/inspections/{b}/fields/confirm", json={"keys": []}).raise_for_status()
    insp.post(f"/api/v1/inspections/{b}/analyze").raise_for_status()
    # 3) extracted (fields not checked)
    cid = new_inspection(insp, [("front", False), ("back", False)])
    insp.post(f"/api/v1/inspections/{cid}/extract").raise_for_status()
    # 4) draft with a blurry photo
    d = new_inspection(insp, [("front", False), ("back", False), ("side", True)])
    insp.post(
        "/api/v1/assistant/messages",
        json={"message": "Which declarations are mandatory on a muesli pack?"},
    )
    print("seeded", {"completed": a, "analysed": b, "extracted": cid, "draft": d})


if __name__ == "__main__":
    main()
