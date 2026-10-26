from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GroupMember, PriceHistory, Product, ProductGroup
from app.schemas.products import GroupDetail, GroupProduct, GroupSummary, MarketPrice, PricePoint
from app.services.normalize import normalize_name

SEARCH_SIMILARITY_THRESHOLD = 0.2
SPARKLINE_POINTS = 30


def _priced(products: Sequence[Product]) -> list[Product]:
    return [p for p in products if p.is_available and p.current_price is not None]


def group_summary(group: ProductGroup) -> GroupSummary:
    products = _priced([m.product for m in group.members])
    by_market: dict[int, Decimal] = {}
    for p in products:
        if p.market_id not in by_market or p.current_price < by_market[p.market_id]:
            by_market[p.market_id] = p.current_price
    brands = sorted({p.brand for p in products if p.brand}, key=str.casefold)
    return GroupSummary(
        id=group.id,
        name=group.name,
        category_id=group.category_id,
        quantity=group.quantity,
        unit=group.unit,
        image_url=group.image_url,
        min_price=min(by_market.values(), default=None),
        market_prices=[MarketPrice(market_id=m, min_price=v) for m, v in sorted(by_market.items())],
        brands=brands,
    )


def _with_members():
    return selectinload(ProductGroup.members).selectinload(GroupMember.product)


async def search_groups(
    db: AsyncSession, q: str | None, category_id: int | None, limit: int
) -> list[GroupSummary]:
    stmt = select(ProductGroup).options(_with_members())
    if category_id is not None:
        stmt = stmt.where(ProductGroup.category_id == category_id)
    if q:
        needle = normalize_name(q)
        similarity = func.word_similarity(needle, ProductGroup.normalized_name)
        stmt = stmt.where(
            or_(
                ProductGroup.normalized_name.contains(needle),
                similarity >= SEARCH_SIMILARITY_THRESHOLD,
            )
        ).order_by(similarity.desc(), ProductGroup.name)
    else:
        stmt = stmt.order_by(ProductGroup.name)
    groups = (await db.scalars(stmt.limit(limit))).all()
    return [group_summary(g) for g in groups]


async def get_group_detail(db: AsyncSession, group_id: int) -> GroupDetail | None:
    group = await db.scalar(
        select(ProductGroup).where(ProductGroup.id == group_id).options(_with_members())
    )
    if group is None:
        return None

    products = [m.product for m in group.members]
    history: dict[int, list[PricePoint]] = defaultdict(list)
    if products:
        # Her ürün için son N fiyat noktası
        ranked = (
            select(
                PriceHistory.product_id,
                PriceHistory.price,
                PriceHistory.recorded_at,
                func.row_number()
                .over(partition_by=PriceHistory.product_id, order_by=PriceHistory.recorded_at.desc())
                .label("rn"),
            )
            .where(PriceHistory.product_id.in_([p.id for p in products]))
            .subquery()
        )
        rows = await db.execute(
            select(ranked.c.product_id, ranked.c.price, ranked.c.recorded_at)
            .where(ranked.c.rn <= SPARKLINE_POINTS)
            .order_by(ranked.c.product_id, ranked.c.recorded_at)
        )
        for product_id, price, recorded_at in rows:
            history[product_id].append(PricePoint(price=price, recorded_at=recorded_at))

    return GroupDetail(
        **group_summary(group).model_dump(),
        products=[
            GroupProduct(
                id=p.id,
                name=p.name,
                brand=p.brand,
                market_id=p.market_id,
                price=p.current_price,
                is_available=p.is_available,
                image_url=p.image_url,
                price_history=history[p.id],
            )
            for p in sorted(products, key=lambda p: (p.current_price is None, p.current_price, p.id))
        ],
    )
