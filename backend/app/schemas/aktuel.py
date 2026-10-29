from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AktuelSourceOut(BaseModel):
    slug: str
    name: str
    url: str
    automatic: bool  # False: ürünler toplanmıyor, yalnızca marketin sitesine bağlantı
    item_count: int
    updated_at: datetime | None


class AktuelItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    market_slug: str
    period_key: str
    period_label: str
    starts_on: date | None
    ends_on: date | None
    upcoming: bool  # broşür henüz başlamadı ("Yakında")
    title: str
    brand: str | None
    quantity_text: str | None
    details: str | None
    price: Decimal
    old_price: Decimal | None
    image_url: str | None
    source_url: str | None


class AktuelOut(BaseModel):
    sources: list[AktuelSourceOut]
    items: list[AktuelItemOut]
