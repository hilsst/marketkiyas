"""Market, kategori, ürün ve fiyat geçmişi tabloları (scraper'ların yazdığı katman)."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import Unit, enum_values

if TYPE_CHECKING:
    from app.models.matching import GroupMember, ProductGroup

Money = Numeric(10, 2)


class Market(TimestampMixin, Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True)  # bim, a101, sok, file
    name: Mapped[str] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(16))  # UI rozet rengi
    logo_url: Mapped[str | None] = mapped_column(String(512))
    website: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    products: Mapped[list["Product"]] = relationship(back_populates="market")


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str | None] = mapped_column(String(16))  # emoji
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id")


class Product(TimestampMixin, Base):
    """Bir marketin rafındaki tekil ürün (market bazlı SKU)."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("market_id", "external_id", name="uq_products_market_external"),
        # pg_trgm fuzzy matching için GIN index
        Index(
            "ix_products_normalized_name_trgm",
            "normalized_name",
            postgresql_using="gin",
            postgresql_ops={"normalized_name": "gin_trgm_ops"},
        ),
        Index("ix_products_brand_lower", text("lower(brand)")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(128))  # marketin kendi ürün kodu
    name: Mapped[str] = mapped_column(String(255))  # ham isim: "Pınar Süt 1 L"
    normalized_name: Mapped[str] = mapped_column(String(255))  # "pinar sut 1000ml"
    brand: Mapped[str | None] = mapped_column(String(120))

    # Normalize edilmiş miktar: 1L -> (1000, ml)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[Unit | None] = mapped_column(
        Enum(Unit, native_enum=False, length=8, values_callable=enum_values)
    )

    current_price: Mapped[Decimal | None] = mapped_column(Money)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    image_url: Mapped[str | None] = mapped_column(String(1024))
    product_url: Mapped[str | None] = mapped_column(String(1024))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    market: Mapped[Market] = relationship(back_populates="products")
    category: Mapped[Category | None] = relationship()
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="PriceHistory.recorded_at"
    )
    group_membership: Mapped["GroupMember | None"] = relationship(
        back_populates="product", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def group(self) -> "ProductGroup | None":
        return self.group_membership.group if self.group_membership else None


class PriceHistory(Base):
    """Her scrape'te fiyat değiştiyse bir satır. Sparkline grafikleri buradan beslenir."""

    __tablename__ = "price_history"
    __table_args__ = (Index("ix_price_history_product_recorded", "product_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    price: Mapped[Decimal] = mapped_column(Money)
    regular_price: Mapped[Decimal | None] = mapped_column(Money)  # indirim öncesi fiyat
    is_campaign: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product: Mapped[Product] = relationship(back_populates="price_history")
