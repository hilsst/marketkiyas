from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import Unit


class AlertCreate(BaseModel):
    group_id: int
    # Seçili ürün: daha pahalı olsa da tam istenen marka takip edilir; boşsa en ucuzu
    product_id: int | None = None
    # Boşsa "şu anki fiyatın altına inince" bildirilir
    target_price: Decimal | None = Field(default=None, gt=0, le=100000)


class AlertOut(BaseModel):
    id: int
    group_id: int
    group_name: str
    category_id: int | None
    image_url: str | None
    quantity: Decimal | None
    unit: Unit | None
    product_id: int | None  # takip edilen ürün; None = grubun en ucuzu
    product_name: str | None
    brand: str | None
    target_price: Decimal | None
    baseline_price: Decimal | None
    current_price: Decimal | None  # kullanıcının şubelerindeki en ucuz fiyat
    current_market_id: int | None
    triggered: bool  # fiyat eşiğin altında
    triggered_at: datetime | None
    unread: bool  # tetiklendi ama kullanıcı Alarmlar sayfasını henüz açmadı
    created_at: datetime


class AlertCount(BaseModel):
    unread: int
