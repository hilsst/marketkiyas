"""Benzer ürünler ("Bunun yerine şunlar da var"): marketfiyati'nın /searchSmilarProduct ucu.

Sonuçlar ürün + şube kümesi başına bir süre bellekte tutulur: ürün sayfası her açıldığında
marketfiyati'ya gidilmez, kullanıcı sayısı artsa da istek sayısı sınırlı kalır.
"""

import time
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import GroupMember, Product, ProductGroup, Store
from app.schemas.products import GroupSummary
from app.services.catalog import _resolver_for, _with_members, campaign_prices, group_summary
from app.services.marketfiyati.client import MarketFiyatiClient
from app.services.marketfiyati.ingest import Ingestor
from app.services.pricing import selected_store_ids

CACHE_TTL_SECONDS = 6 * 3600
MAX_RESULTS = 12

# (marketfiyati ürün id'si, şube id'leri) -> (zaman, benzer ürünlerin marketfiyati id'leri)
_cache: dict[tuple[str, tuple[str, ...]], tuple[float, list[str]]] = {}


def is_marketfiyati_id(external_id: str) -> bool:
    # Zincir sitelerinden gelenler "sok:123", demo ürünleri "demo-..." biçimindedir
    return ":" not in external_id and not external_id.startswith("demo-")


async def _depot_ids(
    db: AsyncSession,
    client: MarketFiyatiClient,
    user_id: int | None,
    latitude: float | None,
    longitude: float | None,
) -> tuple[list[str], float | None, float | None]:
    store_ids = await selected_store_ids(db, user_id)
    if store_ids:
        stores = (
            await db.scalars(select(Store).where(Store.id.in_(store_ids), Store.latitude.is_not(None)))
        ).all()
        if stores:
            return (
                [s.external_id for s in stores],
                sum(float(s.latitude) for s in stores) / len(stores),
                sum(float(s.longitude) for s in stores) / len(stores),
            )
    if latitude is None or longitude is None:
        return [], None, None
    ids = await client.nearest_depot_ids(latitude, longitude, settings.default_search_distance_km)
    return ids, latitude, longitude


async def _similar_external_ids(
    db: AsyncSession, client: MarketFiyatiClient, product: Product, depot_ids: Sequence[str], lat: float, lon: float
) -> list[str]:
    key = (product.external_id, tuple(sorted(depot_ids)))
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    page = await client.similar_products(
        product.external_id,
        product.name,
        latitude=lat,
        longitude=lon,
        distance_km=settings.default_search_distance_km,
        depot_ids=depot_ids,
        size=MAX_RESULTS * 2,
    )
    ingestor = Ingestor(db)
    for found in page.products:
        await ingestor.ingest_product(found)
    await db.commit()
    ids = [p.id for p in page.products if p.id != product.external_id]
    _cache[key] = (time.monotonic(), ids)
    return ids


async def similar_groups(
    db: AsyncSession,
    client: MarketFiyatiClient,
    group_id: int,
    *,
    user_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[GroupSummary] | None:
    """Grubun ürünlerine benzeyen diğer gruplar, marketfiyati'nın sırasıyla. Grup yoksa None.

    Konum bilinmiyorsa (şube seçilmemiş, konum verilmemiş) boş döner: şubesiz arama başka şehrin
    fiyatlarını getirir."""
    group = await db.scalar(select(ProductGroup).where(ProductGroup.id == group_id).options(_with_members()))
    if group is None:
        return None
    source = next((m.product for m in group.members if is_marketfiyati_id(m.product.external_id)), None)
    if source is None:
        return []
    depot_ids, lat, lon = await _depot_ids(db, client, user_id, latitude, longitude)
    if not depot_ids:
        return []
    external_ids = await _similar_external_ids(db, client, source, depot_ids, lat, lon)
    if not external_ids:
        return []

    rows = await db.execute(
        select(Product.external_id, GroupMember.group_id)
        .join(GroupMember, GroupMember.product_id == Product.id)
        .where(Product.external_id.in_(external_ids), GroupMember.group_id != group_id)
    )
    rank = {ext: i for i, ext in enumerate(external_ids)}
    best: dict[int, int] = {}
    for ext, gid in rows:
        best[gid] = min(best.get(gid, len(rank)), rank[ext])
    ordered = sorted(best, key=best.__getitem__)[: MAX_RESULTS * 2]
    if not ordered:
        return []

    groups = {
        g.id: g
        for g in (
            await db.scalars(select(ProductGroup).where(ProductGroup.id.in_(ordered)).options(_with_members()))
        ).all()
    }
    resolver = await _resolver_for(db, user_id, list(groups.values()))
    campaigns = await campaign_prices(db, [m.product_id for g in groups.values() for m in g.members])
    summaries = [group_summary(groups[gid], resolver, campaigns) for gid in ordered if gid in groups]
    return [s for s in summaries if s.min_price is not None][:MAX_RESULTS]
