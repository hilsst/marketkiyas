from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ListStatus, PlanType


class ListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    icon: str | None = Field(default=None, max_length=16)


class ListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    icon: str | None = Field(default=None, max_length=16)


class ItemCreate(BaseModel):
    group_id: int
    quantity: Decimal = Field(default=Decimal(1), gt=0, le=999)
    preferred_brand: str | None = Field(default=None, max_length=120)  # None = Farketmez
    note: str | None = Field(default=None, max_length=255)


class ItemUpdate(BaseModel):
    """Sadece gönderilen alanlar güncellenir. preferred_brand: null göndermek "Farketmez"e döndürür."""

    quantity: Decimal | None = Field(default=None, gt=0, le=999)
    preferred_brand: str | None = Field(default=None, max_length=120)
    is_checked: bool | None = None
    position: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=255)


class AssignedProduct(BaseModel):
    market_id: int | None
    product_id: int | None
    product_name: str | None
    brand: str | None
    unit_price: Decimal | None
    store_id: int | None
    store_name: str | None


class ItemOut(BaseModel):
    id: int
    group_id: int
    group_name: str
    image_url: str | None
    quantity: Decimal
    preferred_brand: str | None
    is_checked: bool
    position: int
    note: str | None
    assigned: AssignedProduct | None


class ShoppingGroup(BaseModel):
    """Alışveriş Modu: "BİM - 4 ürün". market_id None = planda bulunamayan kalemler."""

    market_id: int | None
    item_ids: list[int]
    checked_count: int


class ListSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str | None
    status: ListStatus
    applied_plan: PlanType | None
    planned_total: Decimal | None
    item_count: int
    checked_count: int
    created_at: datetime
    updated_at: datetime


class ListDetail(ListSummary):
    preference_total: Decimal | None
    expected_savings: Decimal | None
    applied_at: datetime | None
    completed_at: datetime | None
    items: list[ItemOut]
    shopping_groups: list[ShoppingGroup]  # plan uygulanmadıysa boş


class PlanLineOut(BaseModel):
    item_id: int
    group_id: int
    group_name: str
    quantity: Decimal
    product_id: int
    product_name: str
    brand: str | None
    market_id: int
    unit_price: Decimal
    store_id: int | None  # kullanıcı şube seçtiyse fiyatın geldiği şube
    line_total: Decimal


class MarketBreakdown(BaseModel):
    market_id: int
    total: Decimal
    item_ids: list[int]


class PlanOut(BaseModel):
    plan_type: PlanType
    total: Decimal
    lines: list[PlanLineOut]
    missing_item_ids: list[int]
    by_market: list[MarketBreakdown]


class MarketTotalOut(BaseModel):
    market_id: int
    total: Decimal
    found: int
    missing: int


class SingleMarketOut(BaseModel):
    available: bool
    warning: str | None  # "Hiçbir market tüm ürünleri eksiksiz bulundurmuyor"
    plan: PlanOut | None
    markets: list[MarketTotalOut]


class SavingsProjection(BaseModel):
    preference_total: Decimal  # kullanıcının kendi tercihleriyle
    opportunist_total: Decimal
    weekly: Decimal
    monthly: Decimal  # x4
    yearly: Decimal  # x52


class OptimizeOut(BaseModel):
    single_market: SingleMarketOut
    combination: PlanOut
    opportunist: PlanOut
    savings: SavingsProjection


class ApplyPlanRequest(BaseModel):
    plan_type: PlanType
