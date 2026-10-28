from collections.abc import Sequence

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models import Category, Market, ProductGroup
from app.schemas.catalog import CategoryOut, MarketOut

router = APIRouter(tags=["catalog"])


@router.get("/markets", response_model=list[MarketOut])
async def list_markets(db: DbSession) -> Sequence[Market]:
    return (await db.scalars(select(Market).where(Market.is_active).order_by(Market.id))).all()


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: DbSession) -> Sequence[Category]:
    """Üst kategoriler sabit sırada; alt kategoriler en çok ürünü olandan aza ("Süt", "Peynir" önce)."""
    group_count = (
        select(func.count())
        .select_from(ProductGroup)
        .where(ProductGroup.subcategory_id == Category.id)
        .scalar_subquery()
    )
    return (
        await db.scalars(select(Category).order_by(Category.sort_order, group_count.desc(), Category.id))
    ).all()
