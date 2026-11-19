from __future__ import annotations

from app.db import get_db
from tests.conftest import User
from tests.test_inspections import _to_analysed


async def test_chat_history_web_toggle_and_isolation(inspector: User, inspector_b: User) -> None:
    r = await inspector.post(
        "/api/v1/assistant/messages", json={"message": "What must a muesli label show?"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assistant"]["web"] is False and body["assistant"]["sources"] == []
    r = await inspector.post(
        "/api/v1/assistant/messages", json={"message": "Search FSSAI site", "web": True}
    )
    assert r.json()["assistant"]["web"] is True and r.json()["assistant"]["sources"]
    hist = (await inspector.get("/api/v1/assistant/messages")).json()
    assert hist["total"] == 4 and [m["role"] for m in hist["items"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert (await inspector_b.get("/api/v1/assistant/messages")).json()["total"] == 0
    iid = await _to_analysed(inspector)
    r = await inspector_b.post(
        "/api/v1/assistant/messages", json={"message": "x", "inspection_id": iid}
    )
    assert r.status_code == 404  # cannot use another inspector's inspection as context
    r = await inspector.post(
        "/api/v1/assistant/messages", json={"message": "Explain findings", "inspection_id": iid}
    )
    assert r.status_code == 200
    assert (await inspector.delete("/api/v1/assistant/messages")).status_code == 200
    assert (await inspector.get("/api/v1/assistant/messages")).json()["total"] == 0


async def test_web_research_can_be_disabled(inspector: User) -> None:
    await get_db()["settings"].update_one(
        {"_id": "global"}, {"$set": {"ai.web_research_enabled": False}}, upsert=True
    )
    try:
        r = await inspector.post("/api/v1/assistant/messages", json={"message": "x", "web": True})
        assert r.status_code == 400 and r.json()["error"]["code"] == "web_disabled"
    finally:
        await get_db()["settings"].update_one(
            {"_id": "global"}, {"$set": {"ai.web_research_enabled": True}}
        )
