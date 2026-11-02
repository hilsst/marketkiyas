from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.services.analytics import EVENT_NAME_RE, SERVER_EVENT_NAMES


class ClientEvent(BaseModel):
    name: str = Field(max_length=64)
    at: datetime | None = None  # telefonda olayın olduğu an; yoksa sunucuya geldiği an
    props: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not EVENT_NAME_RE.match(v):
            raise ValueError("olay adı küçük harf, rakam ve _ olmalı")
        if v in SERVER_EVENT_NAMES:
            raise ValueError("bu olayı sunucu kaydeder")
        return v


class EventBatch(BaseModel):
    device_id: str | None = Field(default=None, max_length=64)
    events: list[ClientEvent] = Field(min_length=1, max_length=50)


class EventBatchOut(BaseModel):
    accepted: int
