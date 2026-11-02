from fastapi import APIRouter

from app.api.deps import DbSession, OptionalUser
from app.schemas.meals import DealIngredientOut
from app.services import deal_menu

router = APIRouter(prefix="/deal-menu", tags=["meals"])


@router.get("/ingredients", response_model=list[DealIngredientOut])
async def deal_ingredients(db: DbSession, user: OptionalUser) -> list[DealIngredientOut]:
    """İndirimden menü giriş ekranı: şu an indirimde olan tarif malzemeleri (en çok indirimliden).
    Seçilenler plan oluştururken `prefer` olarak gönderilir."""
    return await deal_menu.deal_ingredients(db, user.id if user else None)
