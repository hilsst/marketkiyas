"""Üye fotoğrafları: yükleme (düzelt + sakla, onaya düşer), yönetici onayı, tarifte gösterim.

Görünürlük: yalnız 'approved' fotoğraf tarife yansır (Recipe.photo_id/photo_credit, en son onaylanan).
Dosyalar sunucu diskinde (backend/media). Üretimde bu klasör kalıcı bir volume olmalı."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Recipe, RecipePhoto, User
from app.models.recipe_photo import PHOTO_APPROVED, PHOTO_PENDING, PHOTO_REJECTED
from app.services.photo_enhance import enhance_photo

MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
ENHANCED_DIR = MEDIA_ROOT / "recipe-photos"
ORIGINAL_DIR = MEDIA_ROOT / "recipe-photos-original"
MAX_PER_DAY = 5
MAX_PENDING = 10


def enhanced_path(photo_id: int) -> Path:
    return ENHANCED_DIR / f"{photo_id}.jpg"


def original_path(photo_id: int) -> Path:
    return ORIGINAL_DIR / f"{photo_id}.jpg"


def credit_text(name: str | None) -> str:
    return f"{name} tarafından eklendi" if name else "Bir kullanıcı tarafından eklendi"


async def upload_photo(db: AsyncSession, user: User, recipe: Recipe, data: bytes, share_name: bool) -> RecipePhoto:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    recent = (await db.scalar(select(func.count()).select_from(RecipePhoto)
              .where(RecipePhoto.user_id == user.id, RecipePhoto.created_at >= since))) or 0
    if recent >= MAX_PER_DAY:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Günde en fazla 5 fotoğraf ekleyebilirsin")
    pending = (await db.scalar(select(func.count()).select_from(RecipePhoto)
               .where(RecipePhoto.user_id == user.id, RecipePhoto.status == PHOTO_PENDING))) or 0
    if pending >= MAX_PENDING:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Onay bekleyen fotoğrafların çok; önce onaylanmalarını bekle")
    enhanced = await asyncio.to_thread(enhance_photo, data)
    name = None
    if share_name and user.full_name and user.full_name.strip():
        name = user.full_name.strip().split()[0][:60]
    photo = RecipePhoto(recipe_id=recipe.id, user_id=user.id, credit_name=name, status=PHOTO_PENDING)
    db.add(photo)
    await db.flush()
    ENHANCED_DIR.mkdir(parents=True, exist_ok=True)
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    enhanced_path(photo.id).write_bytes(enhanced)
    original_path(photo.id).write_bytes(data)
    await db.commit()
    return photo


async def _sync_recipe(db: AsyncSession, recipe_id: int) -> None:
    """Tarifte gösterilecek fotoğraf = en son onaylanan (yoksa boş: varsayılan görsele döner)"""
    recipe = await db.get(Recipe, recipe_id)
    if recipe is None:
        return
    latest = await db.scalar(select(RecipePhoto).where(RecipePhoto.recipe_id == recipe_id, RecipePhoto.status == PHOTO_APPROVED)
                             .order_by(RecipePhoto.reviewed_at.desc(), RecipePhoto.id.desc()).limit(1))
    recipe.photo_id = latest.id if latest else None
    recipe.photo_credit = credit_text(latest.credit_name) if latest else None


async def review_photo(db: AsyncSession, photo_id: int, approve: bool, reason: str | None = None) -> RecipePhoto:
    photo = await db.get(RecipePhoto, photo_id)
    if photo is None:
        raise HTTPException(404, "Fotoğraf bulunamadı")
    photo.status = PHOTO_APPROVED if approve else PHOTO_REJECTED
    photo.reject_reason = None if approve else (reason or "")[:200] or None
    photo.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    await _sync_recipe(db, photo.recipe_id)
    await db.commit()
    return photo


async def delete_photo(db: AsyncSession, photo: RecipePhoto) -> None:
    recipe_id = photo.recipe_id
    await db.delete(photo)
    await db.flush()
    for p in (enhanced_path(photo.id), original_path(photo.id)):
        p.unlink(missing_ok=True)
    await _sync_recipe(db, recipe_id)
    await db.commit()
