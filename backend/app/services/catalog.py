from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import case, func, literal, or_, select
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
from app.services.geo import haversine_km
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
        subcategory_id=group.subcategory_id,
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


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _strict_match(q: str):
    """Aranan her kelime ürün adında geçmeli (yalnız ilk iki harfin tutması yetmez).
    Döner: (where koşulu, sıra: 0 = hepsi tam kelime ... büyük = kelime ortasında geçen).
    Kelime sırası: tam kelime < kelime başı < içinde geçen. 'kiyma' -> 'Dana Kıyma' bulur, 'Kibrit'i bulmaz."""
    tokens = [t for t in normalize_name(q).split() if t]
    name = ProductGroup.normalized_name
    padded = func.concat(" ", name, " ")
    conds, ranks = [], []
    for tok in tokens:
        esc = _like_escape(tok)
        exact = padded.like(f"% {esc} %", escape="\\")
        prefix = padded.like(f"% {esc}%", escape="\\")
        # Kelime ortasında eşleşme yalnız 4+ harfli aramada ("sut" 3 harf: "pasut" gibi gürültü olmasın)
        inside = name.like(f"%{esc}%", escape="\\") if len(tok) >= 4 else literal(False)
        conds.append(or_(prefix, inside))
        ranks.append(case((exact, 0), (prefix, 1), else_=2))
    if not conds:
        return None, literal(0)
    total = ranks[0]
    for r in ranks[1:]:
        total = total + r
    return _and(conds), total


def _and(conds):
    out = conds[0]
    for c in conds[1:]:
        out = out & c
    return out


async def _nearest_offers(
    db: AsyncSession, groups: Sequence[ProductGroup], resolver: PriceResolver, lat: float, lon: float
) -> dict[int, tuple[float, Decimal, str, int]]:
    """group_id -> (km, fiyat, şube adı, market_id): kullanıcının seçili şubeleri arasında grubu satan en yakın şube
    (eşit uzaklıkta ucuz olan). Konumu bilinmeyen şubeler hesaba katılmaz."""
    if not resolver.uses_stores:
        return {}
    product_group = {m.product_id: g.id for g in groups for m in g.members}
    if not product_group:
        return {}
    rows = await db.execute(
        select(StorePrice.product_id, StorePrice.price, Store.name, Store.market_id, Store.latitude, Store.longitude)
        .join(Store, Store.id == StorePrice.store_id)
        .where(
            StorePrice.product_id.in_(product_group),
            StorePrice.store_id.in_(resolver.store_ids),
            StorePrice.updated_at >= datetime.now(timezone.utc) - PRICE_MAX_AGE,
            Store.latitude.is_not(None),
            Store.longitude.is_not(None),
        )
    )
    best: dict[int, tuple[float, Decimal, str, int]] = {}
    for product_id, price, store_name, market_id, s_lat, s_lon in rows:
        km = round(haversine_km(lat, lon, float(s_lat), float(s_lon)), 2)
        gid = product_group[product_id]
        cand = (km, price, store_name, market_id)
        if gid not in best or cand[:2] < best[gid][:2]:
            best[gid] = cand
    return best


def _with_nearest(summary: GroupSummary, nearest: dict[int, tuple[float, Decimal, str, int]]) -> GroupSummary:
    if (n := nearest.get(summary.id)) is not None:
        summary.nearest_distance_km, summary.nearest_price = n[0], n[1]
        summary.nearest_store_name, summary.nearest_market_id = n[2], n[3]
    return summary


def _near_key(summary: GroupSummary) -> tuple[bool, float]:
    return summary.nearest_distance_km is None, summary.nearest_distance_km or 0.0


def _with_members():
    return selectinload(ProductGroup.members).selectinload(GroupMember.product)


async def _resolver_for(db: AsyncSession, user_id: int | None, groups: Sequence[ProductGroup]) -> PriceResolver:
    return await build_resolver(db, user_id, [m.product_id for g in groups for m in g.members])


async def search_groups(
    db: AsyncSession,
    q: str | None,
    category_id: int | None,
    limit: int,
    user_id: int | None = None,
    sort: str = "name",
    subcategory_id: int | None = None,
    strict: bool = False,
    lat: float | None = None,
    lon: float | None = None,
) -> list[GroupSummary]:
    """Kullanıcı şube seçtiyse fiyatlar o şubelerden; şubelerinde hiç satılmayan gruplar listelenmez.

    sort="popular" (arama yokken): en çok marka/markette bulunan temel ürünler önce ("Tam Yağlı Süt 1 L"
    "%100 Fıstık Ezmesi"nden önce gelsin), eşitse kısa ad önce.

    strict=True (kullanıcının yazdığı arama): aranan her kelime ürün adında geçmeli, benzerlik (pg_trgm) kullanılmaz.
    Sıra: tam kelime > kelime başı > kelime içi; aynı kademede (lat/lon varsa) seçili şubelerden en yakın şubesi
    en yakın olan ürün önce, sonra ada göre. Fiyata göre sıralama yapılmaz.
    strict=False (tarif malzemesi eşleştirme) eski bulanık eşleşmeyi korur."""
    stmt = select(ProductGroup).options(_with_members())
    if subcategory_id is not None:
        stmt = stmt.where(ProductGroup.subcategory_id == subcategory_id)
    if category_id is not None:
        stmt = stmt.where(ProductGroup.category_id == category_id)
    rank = None
    if q and strict:
        cond, rank_expr = _strict_match(q)
        if cond is None:
            return []  # yalnız noktalama yazıldı ("%"): aranacak kelime yok
        rank = rank_expr.label("match_rank")
        stmt = select(ProductGroup, rank).options(_with_members()).where(cond)
        if subcategory_id is not None:
            stmt = stmt.where(ProductGroup.subcategory_id == subcategory_id)
        if category_id is not None:
            stmt = stmt.where(ProductGroup.category_id == category_id)
        stmt = stmt.order_by(rank_expr, func.length(ProductGroup.name), ProductGroup.name)
    elif q:
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
    elif sort == "popular":
        members = (
            select(func.count())
            .select_from(GroupMember)
            .where(GroupMember.group_id == ProductGroup.id)
            .scalar_subquery()
        )
        stmt = stmt.order_by(members.desc(), func.length(ProductGroup.name), ProductGroup.name)
    else:
        stmt = stmt.order_by(ProductGroup.name)
    # Şube seçen kullanıcıda fiyatsız gruplar sonradan elenir, yakınlık sıralaması da sonradan yapılır;
    # liste kısa kalmasın diye fazla çekilir
    wide = limit * 3 if (user_id or rank is not None) else limit
    if rank is not None:
        fetched = (await db.execute(stmt.limit(wide))).unique().all()
        groups = [g for g, _ in fetched]
        ranks = {g.id: r for g, r in fetched}
    else:
        groups = (await db.scalars(stmt.limit(wide))).all()
        ranks = {}
    resolver = await _resolver_for(db, user_id, groups)
    campaigns = await campaign_prices(db, [m.product_id for g in groups for m in g.members])
    summaries = [group_summary(g, resolver, campaigns) for g in groups]
    if resolver.uses_stores:
        summaries = [s for s in summaries if s.min_price is not None]
    if rank is not None and lat is not None and lon is not None:
        nearest = await _nearest_offers(db, groups, resolver, lat, lon)
        summaries = [_with_nearest(s, nearest) for s in summaries]
        # sort kararlı: aynı kademede ve uzaklıkta SQL'deki (kısa ad, ad) sırası korunur
        summaries.sort(key=lambda s: (ranks.get(s.id, 0), *_near_key(s)))
    return summaries[:limit]


async def search_groups_many(
    db: AsyncSession, queries: Sequence[str], limit: int, user_id: int | None = None
) -> dict[str, list[GroupSummary]]:
    """Her q için search_groups(q, None, limit, user_id) ile aynı sonuç, ama üyeler, şube fiyatları ve kampanya
    fiyatları tüm aramalar için tek seferde yüklenir (arama başına 5 yerine toplam ~5 sorgu + arama başına 1)."""
    ids_by_query: dict[str, list[int]] = {}
    for q in dict.fromkeys(queries):
        needle = normalize_name(q)
        similarity = func.word_similarity(needle, ProductGroup.normalized_name)
        stmt = (
            select(ProductGroup.id)
            .where(or_(ProductGroup.normalized_name.contains(needle), similarity >= SEARCH_SIMILARITY_THRESHOLD))
            .order_by(
                similarity.desc(),
                func.similarity(ProductGroup.normalized_name, needle).desc(),
                ProductGroup.name,
            )
            .limit(limit * 3 if user_id else limit)
        )
        ids_by_query[q] = list(await db.scalars(stmt))
    all_ids = {i for ids in ids_by_query.values() for i in ids}
    if not all_ids:
        return {q: [] for q in ids_by_query}
    groups = {
        g.id: g
        for g in await db.scalars(select(ProductGroup).where(ProductGroup.id.in_(all_ids)).options(_with_members()))
    }
    product_ids = [m.product_id for g in groups.values() for m in g.members]
    resolver = await build_resolver(db, user_id, product_ids)
    campaigns = await campaign_prices(db, product_ids)
    summaries = {i: group_summary(g, resolver, campaigns) for i, g in groups.items()}
    result: dict[str, list[GroupSummary]] = {}
    for q, ids in ids_by_query.items():
        found = [summaries[i] for i in ids if i in summaries]  # arada silinen grup atlanır
        if resolver.uses_stores:
            found = [s for s in found if s.min_price is not None]
        result[q] = found[:limit]
    return result


async def get_group_detail(
    db: AsyncSession, group_id: int, user_id: int | None = None, lat: float | None = None, lon: float | None = None
) -> GroupDetail | None:
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
            select(
                StorePrice.product_id, StorePrice.store_id, Store.name, StorePrice.price, StorePrice.updated_at,
                Store.latitude, Store.longitude,
            )
            .join(Store, Store.id == StorePrice.store_id)
            .where(
                StorePrice.product_id.in_([p.id for p in products]),
                StorePrice.store_id.in_(resolver.store_ids),
                StorePrice.updated_at >= datetime.now(timezone.utc) - PRICE_MAX_AGE,
            )
            .order_by(StorePrice.price, StorePrice.store_id)
        )
        for product_id, store_id, store_name, price, updated_at, s_lat, s_lon in rows:
            km = None
            if lat is not None and lon is not None and s_lat is not None and s_lon is not None:
                km = round(haversine_km(lat, lon, float(s_lat), float(s_lon)), 2)
            store_prices[product_id].append(
                ProductStorePrice(
                    store_id=store_id, store_name=store_name, price=price, updated_at=updated_at, distance_km=km
                )
            )
        for sps in store_prices.values():  # konum varsa yakından uzağa; konumsuz şube sona
            if any(sp.distance_km is not None for sp in sps):
                sps.sort(key=lambda sp: (sp.distance_km is None, sp.distance_km or 0.0, sp.price, sp.store_id))
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
            distance_km=min((sp.distance_km for sp in store_prices[p.id] if sp.distance_km is not None), default=None),
            price_updated_at=_updated_at(p, store_prices[p.id], history[p.id]),
        )
        for p in products
    ]
    if any(r.distance_km is not None for r in rows):
        rows.sort(key=lambda r: (r.price is None, r.distance_km is None, r.distance_km or 0.0, r.price or 0, r.id))
    else:
        rows.sort(key=lambda r: (r.price is None, r.price or 0, r.id))
    return GroupDetail(**group_summary(group, resolver, campaigns).model_dump(), products=rows)


def _updated_at(product: Product, stores: list[ProductStorePrice], history: list[PricePoint]) -> datetime | None:
    """Şube fiyatı varsa en yeni şube güncellemesi, yoksa ürünün kaynakta son görülmesi ya da son fiyat kaydı."""
    stamps = [sp.updated_at for sp in stores if sp.updated_at]
    if stamps:
        return max(stamps)
    return product.last_seen_at or (history[-1].recorded_at if history else None)


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
