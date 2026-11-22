from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PHOTO_PENDING = "pending"
PHOTO_APPROVED = "approved"
PHOTO_REJECTED = "rejected"


class RecipePhoto(Base):
    """Üyenin yüklediği yemek fotoğrafı. Yönetici onaylayana kadar yalnız yönetici/sahibi görür.
    Dosyalar: media/recipe-photos/<id>.jpg (düzeltilmiş), media/recipe-photos-original/<id>.jpg (ham, yalnız yönetici)."""

    __tablename__ = "recipe_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Altyazı için ad (kullanıcı paylaşmayı seçtiyse ilk adı); boşsa "Bir kullanıcı"
    credit_name: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(16), default=PHOTO_PENDING, server_default=PHOTO_PENDING, index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Instagram'da yayın: yalnız yükleyen açıkça izin verdiyse (KVKK) ve yönetici elle yayınlarsa
    ig_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ig_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ig_status: Mapped[str | None] = mapped_column(String(16))  # None | publishing | published | failed
    ig_container_id: Mapped[str | None] = mapped_column(String(64))
    ig_media_id: Mapped[str | None] = mapped_column(String(64))
    ig_permalink: Mapped[str | None] = mapped_column(String(300))
    ig_error: Mapped[str | None] = mapped_column(Text)
    ig_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ig_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ig_published_by: Mapped[int | None] = mapped_column(Integer)  # yöneticinin user id'si
