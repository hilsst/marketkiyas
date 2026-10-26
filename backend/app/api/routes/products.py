from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession, OptionalUser
from app.schemas.products import GroupDetail, GroupSummary
from app.services import catalog

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[GroupSummary])
async def search_products(
    db: DbSession,
    user: OptionalUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[GroupSummary]:
    """Ürün grubu araması (pg_trgm). Her grup için market bazında en ucuz fiyat ve markalar döner.

    Giriş yapmış ve şube seçmiş kullanıcıya yalnızca seçtiği şubelerin fiyatları gösterilir."""
    return await catalog.search_groups(db, q, category_id, limit, user.id if user else None)


@router.get("/{group_id}", response_model=GroupDetail)
async def get_product_group(group_id: int, db: DbSession, user: OptionalUser) -> GroupDetail:
    detail = await catalog.get_group_detail(db, group_id, user.id if user else None)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün grubu bulunamadı")
    return detail
