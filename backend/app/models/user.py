from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.savings import SavingsRecord
    from app.models.shopping import ShoppingList


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    shopping_lists: Mapped[list["ShoppingList"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    savings_records: Mapped[list["SavingsRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
