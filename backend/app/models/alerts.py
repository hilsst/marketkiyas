from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.matching import ProductGroup


class PriceAlert(Base):
    """Fiyat alarmı: grubun kullanıcının şubelerindeki en ucuz fiyatı eşiğe inince tetiklenir.

    target_price boşsa eşik "alarm kurulduğundaki fiyatın altı"dır (baseline_price).
    Tetiklenme okunurken hesaplanır (app/services/alerts.py); fiyat yeniden yükselirse alarm
    sıfırlanır ve bir sonraki düşüşte yine bildirir.
    """

    __tablename__ = "price_alerts"
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_price_alerts_user_group"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("product_groups.id", ondelete="CASCADE"))
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    baseline_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    triggered_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped["ProductGroup"] = relationship()
