"""Market şubeleri (marketfiyati.org.tr "depot") ve şube bazlı fiyatlar.

Kullanıcı çevresindeki şubeleri seçer; optimizasyon yalnızca bu şubelerin fiyatlarıyla çalışır.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.catalog import Market, Product


class Store(TimestampMixin, Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True)  # marketfiyati depotId
    name: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    market: Mapped["Market"] = relationship()


class StorePrice(Base):
    """Bir ürünün bir şubedeki güncel fiyatı. Geçmiş, ürün bazında price_history'de tutulur."""

    __tablename__ = "store_prices"
    __table_args__ = (Index("ix_store_prices_store_id", "store_id"),)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[str | None] = mapped_column(String(64))  # kaynakta "12,50 ₺/L" gibi metin
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["Product"] = relationship()
    store: Mapped[Store] = relationship()


class UserStore(Base):
    """Kullanıcının "çevremdeki marketler" seçimi."""

    __tablename__ = "user_stores"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    store: Mapped[Store] = relationship()
