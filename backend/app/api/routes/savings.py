from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import SavingsRecord
from app.schemas.savings import SavingsRecordOut, SavingsVault
from app.services.lists import vault_total

router = APIRouter(prefix="/savings", tags=["savings"])


@router.get("", response_model=SavingsVault)
async def get_vault(user: CurrentUser, db: DbSession) -> SavingsVault:
    """Profil sayfasındaki Tasarruf Kasası."""
    records = (
        await db.scalars(
            select(SavingsRecord)
            .where(SavingsRecord.user_id == user.id)
            .order_by(SavingsRecord.created_at.desc(), SavingsRecord.id.desc())
        )
    ).all()
    return SavingsVault(
        total_saved=await vault_total(db, user),
        record_count=len(records),
        records=[SavingsRecordOut.model_validate(r) for r in records],
    )
