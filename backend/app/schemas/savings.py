from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import PlanType


class SavingsRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    list_id: int | None  # liste silindiyse null; kayıt kasada kalır
    list_name: str
    plan_type: PlanType
    preference_total: Decimal
    optimized_total: Decimal
    saved_amount: Decimal
    item_count: int
    created_at: datetime


class SavingsVault(BaseModel):
    total_saved: Decimal
    record_count: int
    records: list[SavingsRecordOut]


class CompleteResponse(BaseModel):
    list_id: int
    saved_amount: Decimal  # kasaya eklenen; Fırsatçı uygulanmadıysa ya da bu hafta zaten eklendiyse 0
    shopping_savings: Decimal = Decimal("0.00")  # bu alışverişte ortalama fiyatlara göre kazanılan (kutlama)
    vault_total: Decimal
    note: str | None = None  # tasarruf neden eklenmedi (kullanıcıya gösterilir)
