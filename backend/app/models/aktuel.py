"""Marketlerin haftalık aktüel/broşür ürünleri (BİM Aktüel, Şok Haftanın Fırsatları...).

Raf fiyatlarından ayrı tutulur: aktüel ürünler çoğunlukla kalıcı ürün değildir (buzdolabı, çanta),
belli bir günden itibaren "stoklarla sınırlı" satılır ve her hafta yenisi gelir.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AktuelItem(Base):
    __tablename__ = "aktuel_items"
    __table_args__ = (
        UniqueConstraint("market_slug", "source_key", name="uq_aktuel_items_market_source"),
        Index("ix_aktuel_items_market_starts", "market_slug", "starts_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_slug: Mapped[str] = mapped_column(String(32))  # bim, sok...
    source_key: Mapped[str] = mapped_column(String(128))  # kaynaktaki kimlik: "1701:72418"
    period_key: Mapped[str] = mapped_column(String(64))  # aynı broşürdekiler: "1701"
    period_label: Mapped[str] = mapped_column(String(64))  # "28 Ekim Çarşamba", "24-30 Ekim"
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)  # boşsa "stoklarla sınırlı"
    title: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(120))
    quantity_text: Mapped[str | None] = mapped_column(String(64))  # "2,5 kg"
    details: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    source_url: Mapped[str | None] = mapped_column(String(1024))
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
