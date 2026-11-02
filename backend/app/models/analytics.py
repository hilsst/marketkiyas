from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalyticsEvent(Base):
    """Huni ölçümü için tek bir olay (ör. plan_created, plan_to_list, shopping_completed).

    Kişi, cihaza özgü rastgele bir kimlikle (device_id) izlenir; misafir de sayılır. Hesap açılınca
    aynı cihazın olayları user_id de taşır. Hesap silinince kişinin olayları ve cihazındaki olaylar da silinir (services/analytics.erase_user_events)."""

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(8))  # "app" (telefon) ya da "server"
    device_id: Mapped[str | None] = mapped_column(String(64))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    props: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    __table_args__ = (
        Index("ix_analytics_events_name_occurred_at", "name", "occurred_at"),
        Index("ix_analytics_events_device_id", "device_id"),
        Index("ix_analytics_events_user_id", "user_id"),
        Index("ix_analytics_events_occurred_at", "occurred_at"),
    )
