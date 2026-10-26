from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ListStatus, PlanType, enum_values

if TYPE_CHECKING:
    from app.models.catalog import Market, Product
    from app.models.matching import ProductGroup
    from app.models.stores import Store
    from app.models.user import User


class ShoppingList(TimestampMixin, Base):
    __tablename__ = "shopping_lists"
    __table_args__ = (Index("ix_shopping_lists_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[ListStatus] = mapped_column(
        Enum(ListStatus, native_enum=False, length=16, values_callable=enum_values),
        default=ListStatus.ACTIVE,
        server_default=ListStatus.ACTIVE.value,
    )
    # "Listeye Uygula" ile seçilen plan; null ise henüz plan uygulanmadı
    applied_plan: Mapped[PlanType | None] = mapped_column(
        Enum(PlanType, native_enum=False, length=16, values_callable=enum_values)
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Plan uygulandığı andaki tutarlar; "Alışverişi Bitir"de kasaya bunlar yazılır
    planned_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    preference_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    expected_savings: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="shopping_lists")
    items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="ShoppingListItem.position",
    )


class ShoppingListItem(TimestampMixin, Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), index=True
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("product_groups.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=1, server_default="1")

    # Marka tercihi: NULL = "Farketmez (En Ucuzu Al)", dolu = kilitli marka (ör. "Pınar")
    preferred_brand: Mapped[str | None] = mapped_column(String(120))
    # Ürün kilidi ("Marka Değiştir"de belirli bir marketteki ürünü seçmek): yalnızca o ürün alınır.
    # Doluysa preferred_brand da o ürünün markasıdır.
    preferred_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )

    # Plan uygulandığında doldurulur -> Alışveriş Modu'nda market bazlı gruplama
    assigned_market_id: Mapped[int | None] = mapped_column(
        ForeignKey("markets.id", ondelete="SET NULL")
    )
    assigned_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    assigned_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # Kullanıcı şube seçtiyse fiyatın geldiği şube ("BİM - Moda şubesi")
    assigned_store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id", ondelete="SET NULL"))

    # Alışveriş Modu: alındı -> gri + üstü çizili, sırası korunur
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    note: Mapped[str | None] = mapped_column(String(255))

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")
    group: Mapped["ProductGroup"] = relationship()
    assigned_market: Mapped["Market | None"] = relationship()
    assigned_product: Mapped["Product | None"] = relationship(foreign_keys=[assigned_product_id])
    preferred_product: Mapped["Product | None"] = relationship(foreign_keys=[preferred_product_id])
    assigned_store: Mapped["Store | None"] = relationship()
