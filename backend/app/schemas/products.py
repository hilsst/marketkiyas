from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import Unit


class MarketPrice(BaseModel):
    market_id: int
    min_price: Decimal
    regular_price: Decimal | None = None  # kampanyadaysa indirim öncesi fiyat ("PROMO")


class GroupSummary(BaseModel):
    """Arama sonucu / liste eklerken seçilen ürün grubu."""

    id: int
    name: str
    category_id: int | None
    quantity: Decimal | None
    unit: Unit | None
    image_url: str | None
    min_price: Decimal | None
    market_prices: list[MarketPrice]  # her marketteki en ucuz fiyat
    brands: list[str]  # sağa kaydırınca kilitlenebilecek markalar


class PricePoint(BaseModel):
    price: Decimal
    recorded_at: datetime


class GroupProduct(BaseModel):
    id: int
    name: str
    brand: str | None
    market_id: int
    price: Decimal | None
    regular_price: Decimal | None  # kampanyadaysa indirim öncesi fiyat
    store_id: int | None  # kullanıcının seçtiği şubelerden en ucuzu
    is_available: bool  # kullanıcının şubelerinde (ya da genel olarak) satılıyor mu
    image_url: str | None
    price_history: list[PricePoint]  # sparkline


class GroupDetail(GroupSummary):
    products: list[GroupProduct]
