import logging
import math
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Store, UserStore
from app.schemas.stores import SelectStoresRequest, StoreOut
from app.services.marketfiyati.client import MarketFiyatiClient, MarketFiyatiError
from app.services.marketfiyati.ingest import refresh_nearby_stores, sync_selected_stores

log = logging.getLogger(__name__)
router = APIRouter(tags=["stores"])


async def get_marketfiyati_client() -> AsyncIterator[MarketFiyatiClient]:
    async with MarketFiyatiClient() as client:
        yield client


MarketFiyati = Annotated[MarketFiyatiClient, Depends(get_marketfiyati_client)]
StoreSync = Callable[[list[int]], Awaitable[None]]


async def _sync_stores_in_background(store_ids: list[int]) -> None:
    """Yeni seçilen şubelerin fiyatlarını çeker; böylece kullanıcı ilk listede boş ekran görmez."""
    try:
        async with SessionLocal() as db, MarketFiyatiClient() as client:
            stats = await sync_selected_stores(db, client, store_ids=store_ids)
            log.info("şube senkronizasyonu bitti: %s", stats)
    except Exception:
        log.exception("şube senkronizasyonu başarısız: %s", store_ids)


def get_store_sync() -> StoreSync:
    return _sync_stores_in_background


def _distance_km(store: Store, lat: float | None, lon: float | None) -> float | None:
    if lat is None or lon is None or store.latitude is None or store.longitude is None:
        return None
    p1, p2 = math.radians(lat), math.radians(float(store.latitude))
    dp, dl = p2 - p1, math.radians(float(store.longitude) - lon)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(a)), 2)


def _store_out(store: Store, selected: set[int], lat: float | None = None, lon: float | None = None) -> StoreOut:
    return StoreOut(
        id=store.id,
        name=store.name,
        market_id=store.market_id,
        market_slug=store.market.slug,
        market_name=store.market.name,
        latitude=store.latitude,
        longitude=store.longitude,
        distance_km=_distance_km(store, lat, lon),
        selected=store.id in selected,
    )


async def _selected_ids(db: DbSession, user_id: int) -> set[int]:
    return set(await db.scalars(select(UserStore.store_id).where(UserStore.user_id == user_id)))


@router.get("/stores/nearby", response_model=list[StoreOut])
async def nearby_stores(
    user: CurrentUser,
    db: DbSession,
    client: MarketFiyati,
    lat: Annotated[float, Query(ge=35, le=43)],  # Türkiye sınırları
    lon: Annotated[float, Query(ge=25, le=45)],
    distance: Annotated[int, Query(ge=1, le=20)] = settings.default_search_distance_km,
) -> list[StoreOut]:
    """Konum çevresindeki market şubeleri (marketfiyati.org.tr). Kaynağa ulaşılamazsa kayıtlı şubeler döner."""
    try:
        store_ids = await refresh_nearby_stores(db, client, lat, lon, distance)
        stmt = select(Store).where(Store.id.in_(store_ids))
    except MarketFiyatiError:
        log.warning("marketfiyati'ya ulaşılamadı, kayıtlı şubeler kullanılıyor")
        deg = distance / 111  # ~ derece
        stmt = select(Store).where(
            Store.latitude.between(lat - deg, lat + deg), Store.longitude.between(lon - deg, lon + deg)
        )
    stores = (await db.scalars(stmt.where(Store.is_active).options(selectinload(Store.market)))).all()
    selected = await _selected_ids(db, user.id)
    out = [_store_out(s, selected, lat, lon) for s in stores]
    out = [s for s in out if s.distance_km is None or s.distance_km <= distance]
    return sorted(out, key=lambda s: (s.distance_km is None, s.distance_km or 0, s.id))


@router.get("/me/stores", response_model=list[StoreOut])
async def my_stores(user: CurrentUser, db: DbSession) -> list[StoreOut]:
    rows = await db.scalars(
        select(Store)
        .join(UserStore, UserStore.store_id == Store.id)
        .where(UserStore.user_id == user.id)
        .options(selectinload(Store.market))
        .order_by(Store.market_id, Store.name)
    )
    return [_store_out(s, {s.id}) for s in rows]


@router.put("/me/stores", response_model=list[StoreOut])
async def select_stores(
    body: SelectStoresRequest,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
    sync: Annotated[StoreSync, Depends(get_store_sync)],
) -> list[StoreOut]:
    """"Çevremdeki marketler" seçimini değiştirir. Yeni eklenen şubelerin fiyatları arka planda çekilir."""
    wanted = set(body.store_ids)
    existing = set(await db.scalars(select(Store.id).where(Store.id.in_(wanted))))
    if missing := wanted - existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Şube bulunamadı: {sorted(missing)}")

    before = await _selected_ids(db, user.id)
    await db.execute(delete(UserStore).where(UserStore.user_id == user.id))
    db.add_all(UserStore(user_id=user.id, store_id=sid) for sid in sorted(wanted))
    await db.commit()

    if added := sorted(wanted - before):
        background.add_task(sync, added)
    return await my_stores(user, db)
