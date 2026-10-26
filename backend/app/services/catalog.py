from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GroupMember, PriceHistory, Product, ProductGroup, Store, StorePrice
from app.schemas.products import (
    DealOut,
    GroupDetail,
    GroupProduct,
    GroupSummary,
    MarketPrice,
    PricePoint,
    ProductStorePrice,
)
from app.services.normalize import normalize_name
from app.services.pricing import PRICE_MAX_AGE, PriceResolver, build_resolver

SEARCH_SIMILARITY_THRESHOLD = 0.2
SPARKLINE_POINTS = 30


def _priced(products: Sequence[Product], resolver: PriceResolver) -> list[tuple[Product, Decimal]]:
    priced = []
    for p in products:
        resolved = resolver.price(p)
        if resolved is not None:
            priced.append((p, resolved.price))
    return priced


async def campaign_prices(db: AsyncSession, product_ids: Sequence[int]) -> dict[int, Decimal]:
    """Son fiyat kaydı kampanyalı olan ürünlerin indirim öncesi fiyatı."""
    if not product_ids:
        return {}
    latest = (
        select(PriceHistory.product_id, PriceHistory.regular_price, PriceHistory.is_campaign)
        .where(PriceHistory.product_id.in_(product_ids))
        .order_by(PriceHistory.product_id, PriceHistory.recorded_at.desc(), PriceHistory.id.desc())
        .ext(distinct_on(PriceHistory.product_id))
    )
    return {
        product_id: regular
        for product_id, regular, is_campaign in await db.execute(latest)
        if is_campaign and regular is not None
    }


def _regular(product: Product, price: Decimal, resolver: PriceResolver, campaigns: dict[int, Decimal]) -> Decimal | None:
    # Kampanya bilgisi zincir fiyatına aittir; şube fiyatı kullanılıyorsa gösterilmez
    regular = campaigns.get(product.id)
    if resolver.uses_stores or regular is None or regular <= price:
        return None
    return regular


def group_summary(
    group: ProductGroup, resolver: PriceResolver, campaigns: dict[int, Decimal] | None = None
) -> GroupSummary:
    campaigns = campaigns or {}
    priced = _priced([m.product for m in group.members], resolver)
    by_market: dict[int, tuple[Decimal, Decimal | None]] = {}
    for p, price in priced:
        if p.market_id not in by_market or price < by_market[p.market_id][0]:
            by_market[p.market_id] = (price, _regular(p, price, resolver, campaigns))
    brands = sorted({p.brand for p, _ in priced if p.brand}, key=str.casefold)
    return GroupSummary(
        id=group.id,
        name=group.name,
        category_id=group.category_id,
        quantity=group.quantity,
        unit=group.unit,
        image_url=group.image_url,
        min_price=min((price for price, _ in by_market.values()), default=None),
        market_prices=[
            MarketPrice(market_id=m, min_price=price, regular_price=regular)
            for m, (price, regular) in sorted(by_market.items())
        ],
        brands=brands,
    )


def _with_members():
    return selectinload(ProductGroup.members).selectinload(GroupMember.product)


async def _resolver_for(db: AsyncSession, user_id: int | None, groups: Sequence[ProductGroup]) -> PriceResolver:
    return await build_resolver(db, user_id, [m.product_id for g in groups for m in g.members])


async def search_groups(
    db: AsyncSession, q: str | None, category_id: int | None, limit: int, user_id: int | None = None
) -> list[GroupSummary]:
    """Kullanıcı şube seçtiyse fiyatlar o şubelerden; şubelerinde hiç satılmayan gruplar listelenmez."""
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
        ).order_by(
            similarity.desc(),
            # "süt" araması "Laktozsuz Süt"ten önce "Süt"ü getirsin
            func.similarity(ProductGroup.normalized_name, needle).desc(),
            ProductGroup.name,
        )
    else:
        stmt = stmt.order_by(ProductGroup.name)
    groups = (await db.scalars(stmt.limit(limit))).all()
    resolver = await _resolver_for(db, user_id, groups)
    campaigns = await campaign_prices(db, [m.product_id for g in groups for m in g.members])
    summaries = [group_summary(g, resolver, campaigns) for g in groups]
    if resolver.uses_stores:
        summaries = [s for s in summaries if s.min_price is not None]
    return summaries


async def get_group_detail(db: AsyncSession, group_id: int, user_id: int | None = None) -> GroupDetail | None:
    group = await db.scalar(
        select(ProductGroup).where(ProductGroup.id == group_id).options(_with_members())
    )
    if group is None:
        return None

    products = [m.product for m in group.members]
    resolver = await _resolver_for(db, user_id, [group])
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

    store_prices: dict[int, list[ProductStorePrice]] = defaultdict(list)
    if resolver.uses_stores and products:
        rows = await db.execute(
            select(StorePrice.product_id, StorePrice.store_id, Store.name, StorePrice.price)
            .join(Store, Store.id == StorePrice.store_id)
            .where(
                StorePrice.product_id.in_([p.id for p in products]),
                StorePrice.store_id.in_(resolver.store_ids),
                StorePrice.updated_at >= datetime.now(timezone.utc) - PRICE_MAX_AGE,
            )
            .order_by(StorePrice.price, StorePrice.store_id)
        )
        for product_id, store_id, store_name, price in rows:
            store_prices[product_id].append(ProductStorePrice(store_id=store_id, store_name=store_name, price=price))
    store_names = {sp.store_id: sp.store_name for sps in store_prices.values() for sp in sps}

    prices = {p.id: resolver.price(p) for p in products}
    campaigns = await campaign_prices(db, [p.id for p in products])
    rows = [
        GroupProduct(
            id=p.id,
            name=p.name,
            brand=p.brand,
            market_id=p.market_id,
            price=prices[p.id].price if prices[p.id] else None,
            regular_price=_regular(p, prices[p.id].price, resolver, campaigns) if prices[p.id] else None,
            store_id=prices[p.id].store_id if prices[p.id] else None,
            store_name=store_names.get(prices[p.id].store_id) if prices[p.id] else None,
            is_available=prices[p.id] is not None,
            image_url=p.image_url,
            price_history=history[p.id],
            store_prices=store_prices[p.id],
        )
        for p in products
    ]
    rows.sort(key=lambda r: (r.price is None, r.price or 0, r.id))
    return GroupDetail(**group_summary(group, resolver, campaigns).model_dump(), products=rows)


DEAL_WINDOW = timedelta(days=30)
DEAL_MIN_DISCOUNT = Decimal("0.05")


async def deals(db: AsyncSession, user_id: int | None = None, limit: int = 40) -> list[DealOut]:
    """Fırsatlar: fiyatı son 30 günün en yüksek fiyatından ya da kampanya öncesi fiyatından en az %5
    düşük olan ürünler, grup başına en iyisi, indirim oranına göre.

    Önceki fiyat zincir geneli fiyat geçmişinden gelir; gösterilen fiyat kullanıcının şubelerindeki
    fiyattır (şube seçtiyse). Şubelerinde satılmayan ürünler listelenmez.
    """
    since = datetime.now(timezone.utc) - DEAL_WINDOW
    previous = dict(
        (
            await db.execute(
                select(PriceHistory.product_id, func.max(PriceHistory.price))
                .where(PriceHistory.recorded_at >= since)
                .group_by(PriceHistory.product_id)
            )
        ).all()
    )
    campaign_ids = set(
        await db.scalars(
            select(PriceHistory.product_id).where(
                PriceHistory.recorded_at >= since,
                PriceHistory.is_campaign,
                PriceHistory.regular_price > PriceHistory.price,
            )
        )
    )
    products = (
        await db.scalars(
            select(Product)
            .join(GroupMember, GroupMember.product_id == Product.id)
            .where(Product.id.in_(set(previous) | campaign_ids), Product.current_price.is_not(None))
            .options(selectinload(Product.group_membership).selectinload(GroupMember.group))
        )
    ).all()
    resolver = await build_resolver(db, user_id, [p.id for p in products])
    campaigns = await campaign_prices(db, [p.id for p in products])

    best: dict[int, DealOut] = {}
    for p in products:
        resolved = resolver.price(p)
        if resolved is None:
            continue
        regular = campaigns.get(p.id)
        before = max(previous.get(p.id) or Decimal(0), regular or Decimal(0))
        if before <= 0 or resolved.price > before * (1 - DEAL_MIN_DISCOUNT):
            continue
        group = p.group_membership.group
        deal = DealOut(
            group_id=group.id,
            group_name=group.name,
            category_id=group.category_id,
            image_url=p.image_url or group.image_url,
            quantity=group.quantity,
            unit=group.unit,
            product_id=p.id,
            product_name=p.name,
            brand=p.brand,
            market_id=p.market_id,
            store_id=resolved.store_id,
            price=resolved.price,
            previous_price=before,
            discount_percent=int((1 - resolved.price / before) * 100),
            is_campaign=regular is not None and regular > resolved.price,
        )
        current = best.get(group.id)
        if current is None or (deal.discount_percent, -deal.price) > (current.discount_percent, -current.price):
            best[group.id] = deal
    return sorted(best.values(), key=lambda d: (-d.discount_percent, d.price, d.group_id))[:limit]
