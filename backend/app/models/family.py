from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Family(Base):
    """Aile: üyeler birbirinin bütün listelerini görür ve düzenler (liste başına kod gerekmez).
    Kodla liste paylaşımı (ListMember) aile dışındakiler için ayrıca sürer."""

    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
    members: Mapped[list["FamilyMember"]] = relationship(
        back_populates="family", cascade="all, delete-orphan", order_by="FamilyMember.joined_at"
    )
    invites: Mapped[list["FamilyInvite"]] = relationship(back_populates="family", cascade="all, delete-orphan")


class FamilyMember(Base):
    """Bir kullanıcı aynı anda tek ailede olur (user_id tekil). Kurucu da bir üyedir."""

    __tablename__ = "family_members"

    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, unique=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    family: Mapped[Family] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class FamilyInvite(Base):
    """E-postayla davet: davet edilen kişi uygulamada kartı görüp kabul eder (hesabı sonradan açılsa da)."""

    __tablename__ = "family_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    invited_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    family: Mapped[Family] = relationship(back_populates="invites")
    invited_by: Mapped["User | None"] = relationship(foreign_keys=[invited_by_id])
