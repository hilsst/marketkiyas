from decimal import Decimal

from pydantic import BaseModel, Field


class StoreOut(BaseModel):
    id: int
    name: str
    market_id: int
    market_slug: str
    market_name: str
    latitude: Decimal | None
    longitude: Decimal | None
    distance_km: float | None  # sorgu konumuna uzaklık
    selected: bool


class SelectStoresRequest(BaseModel):
    store_ids: list[int] = Field(max_length=50)
