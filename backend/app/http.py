"""Shared HTTP helpers: rate limiter, upload reading, file responses, CSV/XLSX exports."""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator, Iterable
from typing import Any

from fastapi import UploadFile
from fastapi.responses import Response, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings
from app.errors import AppError

_s = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_s.rate_limit_default],
    enabled=_s.app_env != "test",
)
AI_LIMIT = _s.rate_limit_ai
WRITE_LIMIT = _s.rate_limit_write


async def read_upload(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await file.read(256 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise AppError(
                413, "file_too_large", f"Files must be at most {max_bytes // 1_048_576} MB."
            )
        chunks.append(chunk)
    return b"".join(chunks)


def file_response(
    it: AsyncIterator[bytes],
    info: dict[str, Any],
    filename: str | None = None,
    cache: str = "private, max-age=300",
    inline: bool = True,
) -> StreamingResponse:
    ctype = (info.get("metadata") or {}).get("content_type", "application/octet-stream")
    headers = {
        "Cache-Control": cache,
        "Content-Length": str(info.get("length", "")),
        "ETag": f'"{info["_id"]}"',
        "X-Content-Type-Options": "nosniff",
    }
    if filename:
        disp = "inline" if inline else "attachment"
        headers["Content-Disposition"] = f'{disp}; filename="{filename}"'
    return StreamingResponse(it, media_type=ctype, headers=headers)


def _safe_cell(v: Any) -> Any:
    """Prevent CSV/Excel formula injection."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def csv_response(rows: Iterable[list[Any]], header: list[str], filename: str) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow([_safe_cell(c) for c in r])
    return Response(
        buf.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def xlsx_response(rows: Iterable[list[Any]], header: list[str], filename: str) -> Response:
    from openpyxl import Workbook

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Export")
    ws.append(header)
    for r in rows:
        ws.append([_safe_cell(c) for c in r])
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
