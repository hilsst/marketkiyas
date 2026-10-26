from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PlanType, enum_values

if TYPE_CHECKING:
    from app.models.user import User


class SavingsRecord(Base):
    """Tasarruf Kasası kaydı. "Alışverişi Bitir" anında yazılır, değiştirilmez.

    Liste silinse bile kasada kalır: list_id ON DELETE SET NULL, liste adı ise snapshot olarak tutulur.
    Haftalık/aylık(x4)/yıllık(x52) projeksiyonlar saved_amount'tan hesaplanır, saklanmaz.
    """

    __tablename__ = "savings_records"
    __table_args__ = (
        Index("ix_savings_records_user_created", "user_id", "created_at"),
        CheckConstraint("saved_amount >= 0", name="saved_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    list_id: Mapped[int | None] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="SET NULL")
    )
    list_name: Mapped[str] = mapped_column(String(120))
    plan_type: Mapped[PlanType] = mapped_column(
        Enum(PlanType, native_enum=False, length=16, values_callable=enum_values)
    )
    # Kullanıcının kendi tercihleriyle (kilitli markalar) ödeyeceği tutar
    preference_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    # Uygulanan planın toplamı (Fırsatçı)
    optimized_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    saved_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    item_count: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="savings_records")
