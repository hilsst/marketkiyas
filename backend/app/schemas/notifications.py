from datetime import datetime

from pydantic import BaseModel, Field


class PushTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=255)
    platform: str = Field(default="", max_length=16)


class NotificationSettingsOut(BaseModel):
    weekly_menu_enabled: bool
    weekly_menu_weekday: int  # 0 = Pazartesi
    weekly_menu_hour: int


class NotificationSettingsUpdate(BaseModel):
    weekly_menu_enabled: bool | None = None
    weekly_menu_weekday: int | None = Field(default=None, ge=0, le=6)
    weekly_menu_hour: int | None = Field(default=None, ge=0, le=23)


class NotificationOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    plan_id: int | None
    week_start: str
    created_at: datetime
    read: bool


class UnreadCount(BaseModel):
    unread: int
