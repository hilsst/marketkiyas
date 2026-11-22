from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AccountUser, AdminUser, DbSession, OptionalUser
from app.core.config import settings
from app.models import Recipe, RecipePhoto
from app.models.recipe_photo import PHOTO_APPROVED, PHOTO_PENDING
from app.services import meals as meals_svc
from app.services.photo_enhance import MAX_BYTES
from app.services import instagram as ig_svc
from app.services import recipe_photos as svc

router = APIRouter(tags=["recipe-photos"])


class PhotoOut(BaseModel):
    id: int
    recipe_id: int
    recipe_name: str | None = None
    status: str
    credit: str
    reject_reason: str | None = None
    ig_consent: bool = False
    ig_status: str | None = None
    ig_permalink: str | None = None
    ig_error: str | None = None
    # Reddedilen/silinen ama Instagram'da yayında kalmış: profilden elle kaldırılmalı
    ig_needs_removal: bool = False


class InstagramPublishBody(BaseModel):
    caption: str | None = None


class InstagramResolveBody(BaseModel):
    published: bool
    permalink: str | None = None


class RejectBody(BaseModel):
    reason: str | None = None


def _out(p: RecipePhoto, recipe_name: str | None = None) -> PhotoOut:
    return PhotoOut(id=p.id, recipe_id=p.recipe_id, recipe_name=recipe_name, status=p.status,
                    credit=svc.credit_text(p.credit_name), reject_reason=p.reject_reason,
                    ig_consent=p.ig_consent, ig_status=p.ig_status, ig_permalink=p.ig_permalink, ig_error=p.ig_error,
                    ig_needs_removal=p.ig_status == "published" and p.status != PHOTO_APPROVED)


def _is_admin(user) -> bool:
    return bool(user and user.email and user.email.lower() in settings.admin_email_list)


@router.post("/recipes/{recipe_id}/photos", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def upload_recipe_photo(recipe_id: int, user: AccountUser, db: DbSession, file: Annotated[UploadFile, File()],
                              share_name: Annotated[bool, Form()] = False,
                              instagram_consent: Annotated[bool, Form()] = False):
    """Yalnız üyeler. Fotoğraf otomatik düzeltilir ve yönetici onayına düşer; onaylanana kadar kimse görmez."""
    recipe = await meals_svc.get_recipe(db, recipe_id)
    data = await file.read(MAX_BYTES + 1)
    return _out(await svc.upload_photo(db, user, recipe, data, share_name, instagram_consent), recipe.name)


@router.get("/recipes/{recipe_id}/photos/mine", response_model=list[PhotoOut])
async def my_photos(recipe_id: int, user: AccountUser, db: DbSession):
    rows = (await db.scalars(select(RecipePhoto).where(RecipePhoto.recipe_id == recipe_id, RecipePhoto.user_id == user.id)
                             .order_by(RecipePhoto.id.desc()))).all()
    return [_out(p) for p in rows]


@router.delete("/recipe-photos/{photo_id}", status_code=204)
async def delete_my_photo(photo_id: int, user: AccountUser, db: DbSession) -> Response:
    photo = await db.get(RecipePhoto, photo_id)
    if photo is None or (photo.user_id != user.id and not _is_admin(user)):
        raise HTTPException(404, "Fotoğraf bulunamadı")
    await svc.delete_photo(db, photo)
    return Response(status_code=204)


@router.get("/recipe-photos/{photo_id}/image")
async def photo_image(photo_id: int, db: DbSession, user: OptionalUser, original: Annotated[bool, Query()] = False):
    """Onaylı fotoğraf herkese açık; bekleyen/reddedilen yalnız sahibi ve yöneticiye. Ham dosya yalnız yöneticiye."""
    photo = await db.get(RecipePhoto, photo_id)
    admin = _is_admin(user)
    if photo is None or (photo.status != PHOTO_APPROVED and not admin and not (user and user.id == photo.user_id)):
        raise HTTPException(404, "Fotoğraf bulunamadı")
    if original and not admin:
        raise HTTPException(404, "Fotoğraf bulunamadı")
    path = svc.original_path(photo_id) if original else svc.enhanced_path(photo_id)
    if not path.exists():
        raise HTTPException(404, "Fotoğraf bulunamadı")
    cache = "public, max-age=86400" if photo.status == PHOTO_APPROVED and not original else "private, no-store"
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": cache})


@router.get("/admin/recipe-photos", response_model=list[PhotoOut])
async def admin_list(_: AdminUser, db: DbSession, status_: Annotated[str, Query(alias="status")] = PHOTO_PENDING,
                     limit: Annotated[int, Query(ge=1, le=100)] = 50):
    rows = (await db.execute(select(RecipePhoto, Recipe.name).join(Recipe, Recipe.id == RecipePhoto.recipe_id)
                             .where(RecipePhoto.status == status_).order_by(RecipePhoto.id).limit(limit))).all()
    return [_out(p, name) for p, name in rows]


@router.get("/admin/instagram/status")
async def admin_instagram_status(_: AdminUser):
    return await ig_svc.account_status()


@router.get("/admin/instagram/caption/{photo_id}")
async def admin_instagram_caption(photo_id: int, _: AdminUser, db: DbSession):
    """Yayın öncesi önerilen altyazı (yönetici düzenleyebilir)"""
    row = (await db.execute(select(RecipePhoto, Recipe.name).join(Recipe, Recipe.id == RecipePhoto.recipe_id)
                            .where(RecipePhoto.id == photo_id))).first()
    if row is None:
        raise HTTPException(404, "Fotoğraf bulunamadı")
    return {"caption": ig_svc.build_caption(row[1], row[0].credit_name)}


@router.post("/admin/recipe-photos/{photo_id}/instagram", response_model=PhotoOut)
async def admin_instagram_publish(photo_id: int, body: InstagramPublishBody, admin: AdminUser, db: DbSession):
    """Onaylı + yükleyenin izin verdiği fotoğrafı Instagram'da yayınlar. Otomatik yayın yok: her seferinde yönetici basar."""
    return _out(await ig_svc.publish_photo(db, photo_id, admin.id, body.caption))


@router.post("/admin/recipe-photos/{photo_id}/instagram/resolve", response_model=PhotoOut)
async def admin_instagram_resolve(photo_id: int, body: InstagramResolveBody, admin: AdminUser, db: DbSession):
    """Belirsiz kalan yayını elle çöz: 'yayınlandı' işaretle ya da sıfırlayıp yeniden denemeye aç"""
    return _out(await ig_svc.resolve_unconfirmed(db, photo_id, admin.id, body.published, body.permalink))


@router.post("/admin/recipe-photos/{photo_id}/approve", response_model=PhotoOut)
async def admin_approve(photo_id: int, _: AdminUser, db: DbSession):
    return _out(await svc.review_photo(db, photo_id, True))


@router.post("/admin/recipe-photos/{photo_id}/reject", response_model=PhotoOut)
async def admin_reject(photo_id: int, body: RejectBody, _: AdminUser, db: DbSession):
    return _out(await svc.review_photo(db, photo_id, False, body.reason))
