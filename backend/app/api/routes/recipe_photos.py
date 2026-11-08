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
from app.services import recipe_photos as svc

router = APIRouter(tags=["recipe-photos"])


class PhotoOut(BaseModel):
    id: int
    recipe_id: int
    recipe_name: str | None = None
    status: str
    credit: str
    reject_reason: str | None = None


class RejectBody(BaseModel):
    reason: str | None = None


def _out(p: RecipePhoto, recipe_name: str | None = None) -> PhotoOut:
    return PhotoOut(id=p.id, recipe_id=p.recipe_id, recipe_name=recipe_name, status=p.status,
                    credit=svc.credit_text(p.credit_name), reject_reason=p.reject_reason)


def _is_admin(user) -> bool:
    return bool(user and user.email and user.email.lower() in settings.admin_email_list)


@router.post("/recipes/{recipe_id}/photos", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def upload_recipe_photo(recipe_id: int, user: AccountUser, db: DbSession, file: Annotated[UploadFile, File()],
                              share_name: Annotated[bool, Form()] = False):
    """Yalnız üyeler. Fotoğraf otomatik düzeltilir ve yönetici onayına düşer; onaylanana kadar kimse görmez."""
    recipe = await meals_svc.get_recipe(db, recipe_id)
    data = await file.read(MAX_BYTES + 1)
    return _out(await svc.upload_photo(db, user, recipe, data, share_name), recipe.name)


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


@router.post("/admin/recipe-photos/{photo_id}/approve", response_model=PhotoOut)
async def admin_approve(photo_id: int, _: AdminUser, db: DbSession):
    return _out(await svc.review_photo(db, photo_id, True))


@router.post("/admin/recipe-photos/{photo_id}/reject", response_model=PhotoOut)
async def admin_reject(photo_id: int, body: RejectBody, _: AdminUser, db: DbSession):
    return _out(await svc.review_photo(db, photo_id, False, body.reason))
