"""Bildirimler: cihaz push anahtarları, kullanıcının bildirim tercihleri ve gönderilen bildirimler.

Haftalık menü bildirimi: kullanıcının seçtiği gün/saatte ("Bu haftanın menüsü hazır: 1.240 TL") bir kez
oluşturulur. Uygulama içi kayıt her zaman yazılır; push yalnız cihaz anahtarı varsa ve gönderim açıksa gider.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PushToken(Base):
    __tablename__ = "push_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True)  # Expo push anahtarı: ExponentPushToken[...]
    platform: Mapped[str] = mapped_column(String(16), default="", server_default="")  # android / ios
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    weekly_menu_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Haftanın günü (0 = Pazartesi) ve saat; hep Europe/Istanbul saatiyle
    weekly_menu_weekday: Mapped[int] = mapped_column(Integer, default=6, server_default="6")  # Pazar: hafta öncesi
    weekly_menu_hour: Mapped[int] = mapped_column(Integer, default=10, server_default="10")


class Notification(Base):
    __tablename__ = "notifications"
    # Aynı kullanıcıya aynı hafta için aynı türden ikinci bildirim yazılmaz (iş birden çok kez çalışsa da)
    __table_args__ = (UniqueConstraint("user_id", "kind", "week_start", name="uq_notifications_user_kind_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # weekly_menu
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(255))
    data: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")  # JSON: {"plan_id": 12}
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("meal_plans.id", ondelete="SET NULL"))
    week_start: Mapped[date] = mapped_column(Date)  # bildirimin ait olduğu haftanın Pazartesi'si
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
