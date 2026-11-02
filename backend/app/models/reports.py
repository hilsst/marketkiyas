from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceReport(Base):
    """"Bu fiyat yanlış" bildirimi: kullanıcı kasada ya da rafta farklı fiyat gördü.

    Fiyat kaynağı (marketfiyati) düzeltilemez; bildirimler hangi ürünlerin fiyatına güvenilmediğini
    gösterir. Aynı ürün için çok bildirim gelirse fiyat elle incelenir (status: open / checked)."""

    __tablename__ = "price_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("product_groups.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id", ondelete="SET NULL"))
    shown_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # uygulamanın gösterdiği
    reported_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # kullanıcının gördüğü
    note: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(16), default="open", server_default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
