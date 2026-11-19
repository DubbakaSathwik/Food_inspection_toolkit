"""Ask AI (F19): one saved history per inspector; internet research only when requested (BR-07)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.auth import require_inspector
from app.errors import AppError
from app.models.assistant import ChatIn, ChatMessageOut, ChatReplyOut
from app.models.common import OkOut, Page
from app.principal import Principal
from app.repositories import chat, reference, rules, usage
from app.repositories import inspections as insp_repo
from app.repositories import settings as settings_repo
from app.services.ai import chain
from app.services.ai.base import ProviderError
from app.services.ai.prompts import ASSISTANT_SYSTEM

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
Insp = Annotated[Principal, Depends(require_inspector)]


async def _context(p: Principal, inspection_id: str | None) -> str:
    if not inspection_id:
        return ""
    insp = await insp_repo.get(p, inspection_id)  # owner-only
    fields = insp.get("fields") or {}
    lines = [
        f"Current inspection {insp['_id']} (category: {insp.get('category') or 'unknown'}, status: {insp['status']})."
    ]
    for k, f in fields.items():
        if f.get("value"):
            lines.append(f"- {k}: {str(f['value'])[:200]}")
    for f in (insp.get("findings") or [])[:12]:
        lines.append(
            f"Finding [{f['severity']}] {f['title']}: {f['status_label']} — {f['detail'][:200]}"
        )
    ref_id = (((insp.get("analysis") or {}).get("reference")) or {}).get("record_id")
    if ref_id:
        rec = await reference.get(ref_id)
        lines.append(
            f"Matched DEMO reference record {ref_id}: {rec.get('brand')} {rec.get('product_name')}, "
            f"manufacturer {(rec.get('manufacturer') or {}).get('name')}, licence {(rec.get('licence') or {}).get('number')}."
        )
    for r in (await rules.active_for_category(insp.get("category")))[:20]:
        lines.append(f"Demo rule {r['code']} ({r['reference']}): {r['requirement'][:160]}")
    return "\n".join(lines)


@router.get("/messages", response_model=Page[ChatMessageOut])
async def history(
    p: Insp,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:
    items, total = await chat.history(p, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/messages", response_model=ChatReplyOut)
async def ask(request: Request, p: Insp, body: ChatIn) -> dict[str, Any]:
    cfg = await settings_repo.load()
    if body.web and not cfg["ai"].get("web_research_enabled", True):
        raise AppError(400, "web_disabled", "Internet research is turned off by the administrator.")
    context = await _context(p, body.inspection_id)
    await usage.consume_ai(p.uid, cfg["limits"]["ai_daily_limit_per_user"])
    previous = [{"role": m["role"], "text": m["text"]} for m in await chat.recent(p, 10)]
    user_msg = await chat.add(p, "user", body.message, body.web, body.inspection_id)
    system = ASSISTANT_SYSTEM + (
        "\n\nContext (inspector's own data):\n" + context if context else ""
    )
    try:
        res = await chain.run_chat(
            system, [*previous, {"role": "user", "text": body.message}], body.web
        )
        reply = await chat.add(
            p, "assistant", res.text, res.web_used, body.inspection_id, res.sources, res.provider
        )
    except ProviderError as e:
        reply = await chat.add(p, "assistant", f"Sorry — {e}", False, body.inspection_id, [], None)
    return {"user": user_msg, "assistant": reply}


@router.delete("/messages", response_model=OkOut)
async def clear(p: Insp) -> dict[str, Any]:
    await chat.clear(p)
    return {"ok": True}
