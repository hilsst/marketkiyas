"""Boş misafir hesaplarını temizleme.

Uygulama her yeni kurulumda bir misafir açar; kaldırılan ya da hiç kullanılmayan kurulumlar veritabanında
boş kullanıcı bırakır. Hiç liste, plan ya da dolap kaydı olmayan ve belli bir süredir dokunulmamış
misafirler silinir. İçinde verisi olan misafire dokunulmaz (kullanıcı geri dönebilir)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MealPlan, PantryItem, ShoppingList, User


async def purge_empty_guests(db: AsyncSession, older_than: timedelta = timedelta(days=30)) -> int:
    cutoff = datetime.now(timezone.utc) - older_than
    empty = (
        select(User.id)
        .where(
            User.is_guest.is_(True),
            User.updated_at < cutoff,
            ~exists().where(ShoppingList.user_id == User.id),
            ~exists().where(MealPlan.user_id == User.id),
            ~exists().where(PantryItem.user_id == User.id),
        )
    )
    result = await db.execute(delete(User).where(User.id.in_(empty)))
    await db.commit()
    return result.rowcount or 0
