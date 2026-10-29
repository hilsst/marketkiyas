"""Barkodla ürün bulma ("Barkod Okut"): önce veritabanı, yoksa marketfiyati.org.tr."""

import re

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import GroupMember, Product, Store
from app.services.marketfiyati.client import MarketFiyatiClient
from app.services.marketfiyati.ingest import Ingestor
from app.services.pricing import selected_store_ids

BARCODE_RE = re.compile(r"^\d{8,14}$")  # EAN-8, UPC-A, EAN-13, GTIN-14


def clean_barcode(code: str) -> str | None:
    code = re.sub(r"\s+", "", code or "")
    return code if BARCODE_RE.match(code) else None


async def local_group_id(db: AsyncSession, barcode: str) -> int | None:
    # marketfiyati bazı ürünlerde barkodu ürün id'si olarak kullanıyor; ikisine de bakılır
    return await db.scalar(
        select(GroupMember.group_id)
        .join(Product, Product.id == GroupMember.product_id)
        .where(or_(Product.barcode == barcode, Product.external_id == barcode))
        .order_by(Product.barcode.is_(None), GroupMember.group_id)
        .limit(1)
    )


async def find_group_id(
    db: AsyncSession,
    client: MarketFiyatiClient,
    barcode: str,
    *,
    user_id: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> int | None:
    """Barkodun ürün grubu. Veritabanında yoksa kullanıcının şubeleri (ya da verilen konum) çevresinde
    marketfiyati'da aranır, bulunan ürün kaydedilip barkodu işaretlenir."""
    if (group_id := await local_group_id(db, barcode)) is not None:
        return group_id

    depot_ids: list[str] = []
    store_ids = await selected_store_ids(db, user_id)
    if store_ids:
        stores = (
            await db.scalars(select(Store).where(Store.id.in_(store_ids), Store.latitude.is_not(None)))
        ).all()
        if stores:
            latitude = sum(float(s.latitude) for s in stores) / len(stores)
            longitude = sum(float(s.longitude) for s in stores) / len(stores)
            depot_ids = [s.external_id for s in stores]
    if not depot_ids and latitude is not None and longitude is not None:
        # Şubesiz arama konumu yok sayar (İstanbul fiyatı gelir): önce konumun çevresindeki şubeler
        depot_ids = await client.nearest_depot_ids(latitude, longitude, settings.default_search_distance_km)

    page = await client.search_by_barcode(
        barcode,
        latitude=latitude,
        longitude=longitude,
        distance_km=settings.default_search_distance_km,
        depot_ids=depot_ids,
    )
    if not page.products:
        return None
    ingestor = Ingestor(db)
    for product in page.products:
        await ingestor.ingest_product(product)
    await db.execute(
        update(Product)
        .where(Product.external_id.in_([p.id for p in page.products]))
        .values(barcode=barcode)
    )
    await db.commit()
    return await local_group_id(db, barcode)
