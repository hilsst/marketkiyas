from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.savings import SavingsRecord
    from app.models.shopping import ShoppingList


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # Google/Apple ile girende boş
    full_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)  # Google hesabının kalıcı kimliği
    apple_sub: Mapped[str | None] = mapped_column(String(255), unique=True)

    shopping_lists: Mapped[list["ShoppingList"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    savings_records: Mapped[list["SavingsRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None


class PasswordReset(Base):
    """Şifre sıfırlama kodu: e-postayla 6 haneli kod gider, yalnız özeti saklanır; 1 saat geçerli, 5 deneme."""

    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
