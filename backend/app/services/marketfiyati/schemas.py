"""marketfiyati.org.tr yanıtlarının ayrıştırılması.

Resmi bir şema yayınlanmadığı için alanlar savunmacı okunur: eksik/bilinmeyen alanlar atlanır,
tek bir bozuk kayıt tüm senkronizasyonu düşürmez.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ".")).quantize(Decimal("0.000001"))
    except InvalidOperation:
        return None


def _price(value: Any) -> Decimal | None:
    d = _decimal(value)
    return d.quantize(Decimal("0.01")) if d is not None and d > 0 else None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class Depot:
    """Bir market şubesi."""

    id: str
    name: str
    market_name: str
    latitude: Decimal | None
    longitude: Decimal | None

    @classmethod
    def from_nearest(cls, raw: dict) -> "Depot | None":
        # /nearest yanıtı: {"id", "sellerName", "marketName", "location": {"lat", "lon"}} ya da düz lat/lon
        depot_id = _str(raw.get("id") or raw.get("depotId"))
        market = _str(raw.get("marketName") or raw.get("marketAdi"))
        if not depot_id or not market:
            return None
        location = raw.get("location") or {}
        return cls(
            id=depot_id,
            name=_str(raw.get("sellerName") or raw.get("depotName") or raw.get("name")) or depot_id,
            market_name=market,
            latitude=_decimal(location.get("lat", raw.get("latitude"))),
            longitude=_decimal(location.get("lon", raw.get("longitude"))),
        )


@dataclass(frozen=True)
class DepotPrice:
    depot: Depot
    price: Decimal
    unit_price: str | None


@dataclass(frozen=True)
class SearchProduct:
    id: str
    title: str
    brand: str | None
    image_url: str | None
    volume_or_weight: str | None  # "1 L", "500 g"
    categories: tuple[str, ...]
    prices: tuple[DepotPrice, ...]

    @classmethod
    def from_raw(cls, raw: dict) -> "SearchProduct | None":
        product_id = _str(raw.get("id"))
        title = _str(raw.get("title"))
        if not product_id or not title:
            return None
        prices = []
        for entry in raw.get("productDepotInfoList") or []:
            price = _price(entry.get("price"))
            depot_id = _str(entry.get("depotId"))
            market = _str(entry.get("marketAdi"))
            if price is None or not depot_id or not market:
                continue
            depot = Depot(
                id=depot_id,
                name=_str(entry.get("depotName")) or depot_id,
                market_name=market,
                latitude=_decimal(entry.get("latitude")),
                longitude=_decimal(entry.get("longitude")),
            )
            prices.append(DepotPrice(depot, price, _str(entry.get("unitPrice"))))
        return cls(
            id=product_id,
            title=title,
            brand=_str(raw.get("brand")),
            image_url=_str(raw.get("imageUrl")),
            volume_or_weight=_str(raw.get("refinedVolumeOrWeight")),
            categories=tuple(c for c in (raw.get("categories") or []) if isinstance(c, str)),
            prices=tuple(prices),
        )


@dataclass(frozen=True)
class SearchPage:
    total: int
    products: list[SearchProduct]

    @classmethod
    def from_raw(cls, raw: dict) -> "SearchPage":
        products = [p for p in (SearchProduct.from_raw(r) for r in raw.get("content") or []) if p]
        return cls(total=int(raw.get("numberOfFound") or 0), products=products)
