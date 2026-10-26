from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession, OptionalUser
from app.api.routes.stores import MarketFiyati
from app.schemas.products import BarcodeResult, DealOut, GroupDetail, GroupSummary
from app.services import barcode, catalog
from app.services.marketfiyati.client import MarketFiyatiError

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[GroupSummary])
async def search_products(
    db: DbSession,
    user: OptionalUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[GroupSummary]:
    """Ürün grubu araması (pg_trgm). Her grup için market bazında en ucuz fiyat ve markalar döner.

    Giriş yapmış ve şube seçmiş kullanıcıya yalnızca seçtiği şubelerin fiyatları gösterilir."""
    return await catalog.search_groups(db, q, category_id, limit, user.id if user else None)


@router.get("/deals", response_model=list[DealOut])
async def list_deals(
    db: DbSession, user: OptionalUser, limit: Annotated[int, Query(ge=1, le=100)] = 40
) -> list[DealOut]:
    """Fırsatlar: son 30 güne göre ucuzlayan ya da kampanyadaki ürünler (en az %5)."""
    return await catalog.deals(db, user.id if user else None, limit)


@router.get("/barcode/{code}", response_model=BarcodeResult)
async def find_by_barcode(
    code: str,
    db: DbSession,
    user: OptionalUser,
    client: MarketFiyati,
    lat: Annotated[float | None, Query(ge=35, le=43)] = None,
    lon: Annotated[float | None, Query(ge=25, le=45)] = None,
) -> BarcodeResult:
    """Okutulan barkodun ürün grubu. Veritabanında yoksa marketfiyati.org.tr'de aranır."""
    cleaned = barcode.clean_barcode(code)
    if cleaned is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Barkod 8-14 haneli bir sayı olmalı")
    try:
        group_id = await barcode.find_group_id(
            db, client, cleaned, user_id=user.id if user else None, latitude=lat, longitude=lon
        )
    except MarketFiyatiError:
        group_id = await barcode.local_group_id(db, cleaned)
        if group_id is None:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Fiyat kaynağına şu an ulaşılamıyor, biraz sonra tekrar deneyin"
            ) from None
    if group_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu barkodla ürün bulunamadı")
    return BarcodeResult(barcode=cleaned, group_id=group_id)


@router.get("/{group_id}", response_model=GroupDetail)
async def get_product_group(group_id: int, db: DbSession, user: OptionalUser) -> GroupDetail:
    detail = await catalog.get_group_detail(db, group_id, user.id if user else None)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün grubu bulunamadı")
    return detail
