"""Ürün eşleştirme katmanı: farklı market/markalardaki aynı ürünü tek grupta toplar.

Örn. grup "Süt 1 L" -> [Sütaş Süt 1L @BİM, Pınar Süt 1L @A101, Pınar Süt 1L @Şok, ...]
Kullanıcı listeye ürünü değil GRUBU ekler; marka tercihi liste kaleminde tutulur.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.catalog import Category, Product
from app.models.enums import Unit, enum_values


class ProductGroup(TimestampMixin, Base):
    __tablename__ = "product_groups"
    __table_args__ = (
        Index(
            "ix_product_groups_normalized_name_trgm",
            "normalized_name",
            postgresql_using="gin",
            postgresql_ops={"normalized_name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))  # gösterim adı: "Süt 1 L"
    normalized_name: Mapped[str] = mapped_column(String(255))  # "sut 1000ml"
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[Unit | None] = mapped_column(
        Enum(Unit, native_enum=False, length=8, values_callable=enum_values)
    )
    image_url: Mapped[str | None] = mapped_column(String(1024))

    category: Mapped[Category | None] = relationship()
    members: Mapped[list["GroupMember"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("product_groups.id", ondelete="CASCADE"), index=True
    )
    # Bir ürün yalnızca tek bir gruba ait olabilir
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), unique=True
    )
    match_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))  # pg_trgm similarity 0..1
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped[ProductGroup] = relationship(back_populates="members")
    product: Mapped[Product] = relationship(back_populates="group_membership")
