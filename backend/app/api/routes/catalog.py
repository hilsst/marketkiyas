from collections.abc import Sequence

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Category, Market
from app.schemas.catalog import CategoryOut, MarketOut

router = APIRouter(tags=["catalog"])


@router.get("/markets", response_model=list[MarketOut])
async def list_markets(db: DbSession) -> Sequence[Market]:
    return (await db.scalars(select(Market).where(Market.is_active).order_by(Market.id))).all()


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: DbSession) -> Sequence[Category]:
    return (await db.scalars(select(Category).order_by(Category.sort_order, Category.id))).all()
