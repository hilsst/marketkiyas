from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

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
    subcategory_id: int | None = None  # alt kategori ("Peynir")
    quantity: Decimal | None
    unit: Unit | None
    image_url: str | None
    min_price: Decimal | None
    market_prices: list[MarketPrice]  # her marketteki en ucuz fiyat
    brands: list[str]  # sağa kaydırınca kilitlenebilecek markalar
    # Konum gönderildiyse kullanıcının seçili şubeleri arasında bu ürünü satan EN YAKIN şube ve oradaki fiyat
    nearest_store_name: str | None = None
    nearest_market_id: int | None = None
    nearest_distance_km: float | None = None
    nearest_price: Decimal | None = None


class PricePoint(BaseModel):
    price: Decimal
    recorded_at: datetime


class ProductStorePrice(BaseModel):
    """Ürünün kullanıcının seçtiği bir şubedeki fiyatı."""

    store_id: int
    store_name: str
    price: Decimal
    updated_at: datetime | None = None  # fiyatın kaynakta güncellendiği an
    distance_km: float | None = None  # konum gönderildiyse kullanıcıya uzaklık


class GroupProduct(BaseModel):
    id: int
    name: str
    brand: str | None
    market_id: int
    price: Decimal | None
    regular_price: Decimal | None  # kampanyadaysa indirim öncesi fiyat
    store_id: int | None  # kullanıcının seçtiği şubelerden en ucuzu
    store_name: str | None = None
    is_available: bool  # kullanıcının şubelerinde (ya da genel olarak) satılıyor mu
    image_url: str | None
    price_history: list[PricePoint]  # sparkline
    # Gösterilen fiyatın kaynakta en son görüldüğü an ("Fiyat bugün 09:15 güncellendi" etiketi)
    price_updated_at: datetime | None = None
    store_prices: list[ProductStorePrice] = []  # seçili şubelerin hepsi; konum varsa yakından uzağa, yoksa ucuzdan pahalıya
    distance_km: float | None = None  # bu ürünü satan en yakın seçili şubeye uzaklık


class GroupDetail(GroupSummary):
    products: list[GroupProduct]


class DealOut(BaseModel):
    """Fırsatlar: son 30 günün en yüksek fiyatına (ya da kampanya öncesi fiyata) göre ucuzlayan ürün."""

    group_id: int
    group_name: str
    category_id: int | None
    image_url: str | None
    quantity: Decimal | None
    unit: Unit | None
    product_id: int
    product_name: str
    brand: str | None
    market_id: int
    store_id: int | None
    price: Decimal
    previous_price: Decimal
    discount_percent: int
    is_campaign: bool  # kaynak "kampanyalı" dedi (aktüel/indirim)


class PriceReportCreate(BaseModel):
    """"Bu fiyat yanlış": hangi ürün/şube, kullanıcının gördüğü fiyat (bilmiyorsa boş) ve not."""

    product_id: int
    store_id: int | None = None
    reported_price: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    note: str | None = Field(default=None, max_length=300)


class PriceReportOut(BaseModel):
    id: int
    shown_price: Decimal | None
    reported_price: Decimal | None
    detail: str


class BarcodeResult(BaseModel):
    barcode: str
    group_id: int
