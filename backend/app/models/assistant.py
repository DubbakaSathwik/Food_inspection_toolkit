from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.common import LongStr, OutModel, StrictModel


class ChatIn(StrictModel):
    message: LongStr = Field(min_length=1)
    web: bool = False
    inspection_id: str | None = Field(None, pattern=r"^CS-\d{4}-\d{4,6}$")


class Source(OutModel):
    title: str
    url: str


class ChatMessageOut(OutModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    web: bool = False
    inspection_id: str | None = None
    sources: list[Source] = []
    provider: str | None = None
    created_at: datetime


class ChatReplyOut(OutModel):
    user: ChatMessageOut
    assistant: ChatMessageOut
