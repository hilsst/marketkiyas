"""Fiyat çözümleme: kullanıcı şube seçtiyse yalnızca o şubelerin güncel fiyatları kullanılır,
seçmediyse ürünün zincir genelindeki en düşük fiyatı (products.current_price)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Market, Product, Store, StorePrice, UserStore

# Bundan eski şube fiyatları "güncel değil" sayılır ve kullanılmaz
PRICE_MAX_AGE = timedelta(days=7)


@dataclass(frozen=True)
class ResolvedPrice:
    price: Decimal
    store_id: int | None  # None = zincir geneli fiyat


class PriceResolver:
    def __init__(self, store_ids: list[int], store_prices: dict[int, ResolvedPrice]) -> None:
        self.store_ids = store_ids
        self._store_prices = store_prices

    @property
    def uses_stores(self) -> bool:
        return bool(self.store_ids)

    def price(self, product: Product) -> ResolvedPrice | None:
        if not product.is_available:
            return None
        if self.uses_stores:
            return self._store_prices.get(product.id)
        if product.current_price is None:
            return None
        return ResolvedPrice(product.current_price, None)


async def selected_store_ids(db: AsyncSession, user_id: int | None) -> list[int]:
    if user_id is None:
        return []
    rows = await db.scalars(
        select(UserStore.store_id)
        .join(Store, Store.id == UserStore.store_id)
        .where(UserStore.user_id == user_id, Store.is_active)
        .order_by(UserStore.store_id)
    )
    return list(rows)


async def build_resolver(db: AsyncSession, user_id: int | None, product_ids: Iterable[int]) -> PriceResolver:
    store_ids = await selected_store_ids(db, user_id)
    product_ids = list(set(product_ids))
    prices: dict[int, ResolvedPrice] = {}
    if store_ids and product_ids:
        rows = await db.execute(
            select(StorePrice.product_id, StorePrice.price, StorePrice.store_id).where(
                StorePrice.product_id.in_(product_ids),
                StorePrice.store_id.in_(store_ids),
                StorePrice.updated_at >= datetime.now(timezone.utc) - PRICE_MAX_AGE,
            )
        )
        for product_id, price, store_id in rows:
            current = prices.get(product_id)
            if current is None or (price, store_id) < (current.price, current.store_id):
                prices[product_id] = ResolvedPrice(price, store_id)
    return PriceResolver(store_ids, prices)


async def candidate_market_ids(db: AsyncSession, resolver: PriceResolver) -> list[int]:
    """Tek Market sekmesinde değerlendirilecek zincirler: seçili şubelerin zincirleri ya da tümü."""
    stmt = select(Market.id).where(Market.is_active).order_by(Market.id)
    if resolver.uses_stores:
        stmt = stmt.where(Market.id.in_(select(Store.market_id).where(Store.id.in_(resolver.store_ids))))
    return list(await db.scalars(stmt))
