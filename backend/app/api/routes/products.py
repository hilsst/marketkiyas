from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.schemas.products import (
    BarcodeResult,
    DealOut,
    GroupDetail,
    GroupSummary,
    PriceReportCreate,
    PriceReportOut,
)
from app.services import barcode, catalog, reports, similar
from app.services.marketfiyati.client import MarketFiyatiClient, MarketFiyatiError

router = APIRouter(prefix="/products", tags=["products"])


async def get_barcode_client() -> AsyncIterator[MarketFiyatiClient]:
    """Kullanıcı rafta bekliyor: kısa zaman aşımı, tek tekrar."""
    async with MarketFiyatiClient(timeout=10, max_retries=1) as client:
        yield client


@router.get("", response_model=list[GroupSummary])
async def search_products(
    db: DbSession,
    user: OptionalUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    sort: Annotated[str, Query(pattern="^(name|popular)$")] = "name",
    subcategory_id: int | None = None,
    lat: Annotated[float | None, Query(ge=35, le=43)] = None,  # Türkiye sınırları; yakından uzağa sıralama için
    lon: Annotated[float | None, Query(ge=25, le=45)] = None,
) -> list[GroupSummary]:
    """Ürün grubu araması: aranan kelimeler ürün adında geçmeli (tam kelime > kelime başı > kelime içi, Türkçe
    harfler fark etmez). Her grup için market bazında en ucuz fiyat ve markalar döner.
    Konum (lat/lon) ve şube seçimi varsa sonuçlar en yakın şubesi en yakın olandan başlar (fiyata göre değil);
    nearest_* alanları o şubeyi ve oradaki fiyatı verir. Konum ya da şube yoksa ada göre sıralanır.

    Giriş yapmış ve şube seçmiş kullanıcıya yalnızca seçtiği şubelerin fiyatları gösterilir.
    Arama yokken sort=popular temel ürünleri öne alır."""
    return await catalog.search_groups(
        db, q, category_id, limit, user.id if user else None, sort, subcategory_id,
        strict=True, lat=lat, lon=lon,
    )


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
    client: Annotated[MarketFiyatiClient, Depends(get_barcode_client)],
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


@router.get("/{group_id}/similar", response_model=list[GroupSummary])
async def similar_products(
    group_id: int,
    db: DbSession,
    user: OptionalUser,
    client: Annotated[MarketFiyatiClient, Depends(get_barcode_client)],
    lat: Annotated[float | None, Query(ge=35, le=43)] = None,
    lon: Annotated[float | None, Query(ge=25, le=45)] = None,
) -> list[GroupSummary]:
    """Benzer ürünler (muadiller), kullanıcının şubelerindeki fiyatlarla. Kaynağa ulaşılamazsa boş liste."""
    try:
        result = await similar.similar_groups(
            db, client, group_id, user_id=user.id if user else None, latitude=lat, longitude=lon
        )
    except MarketFiyatiError:
        return []
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün grubu bulunamadı")
    return result


@router.get("/{group_id}", response_model=GroupDetail)
async def get_product_group(
    group_id: int,
    db: DbSession,
    user: OptionalUser,
    lat: Annotated[float | None, Query(ge=35, le=43)] = None,
    lon: Annotated[float | None, Query(ge=25, le=45)] = None,
) -> GroupDetail:
    """Konum varsa ürünler ve şube fiyatları en yakın şubeden uzağa dizilir; yoksa ucuzdan pahalıya."""
    detail = await catalog.get_group_detail(db, group_id, user.id if user else None, lat, lon)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün grubu bulunamadı")
    return detail


@router.post("/{group_id}/price-reports", response_model=PriceReportOut, status_code=status.HTTP_201_CREATED)
async def report_wrong_price(group_id: int, body: PriceReportCreate, user: CurrentUser, db: DbSession) -> PriceReportOut:
    """"Bu fiyat yanlış": kullanıcı rafta/kasada farklı fiyat gördü. Misafir de bildirebilir; günde 20."""
    return await reports.report_price(db, user, group_id, body)
