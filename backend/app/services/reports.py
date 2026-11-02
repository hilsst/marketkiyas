""""Bu fiyat yanlış" bildirimleri."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GroupMember, PriceReport, Product, StorePrice, User
from app.schemas.products import PriceReportCreate, PriceReportOut

MAX_PER_DAY = 20  # kullanıcı başına günlük bildirim


async def report_price(db: AsyncSession, user: User, group_id: int, body: PriceReportCreate) -> PriceReportOut:
    product = await db.scalar(
        select(Product)
        .join(GroupMember, GroupMember.product_id == Product.id)
        .where(Product.id == body.product_id, GroupMember.group_id == group_id)
    )
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün bu grupta yok")
    # Gösterilen fiyat istemciden değil sunucunun kendi verisinden: şube fiyatı ya da zincir fiyatı
    shown: Decimal | None = product.current_price
    if body.store_id is not None:
        store_price = await db.scalar(
            select(StorePrice.price).where(StorePrice.product_id == product.id, StorePrice.store_id == body.store_id)
        )
        if store_price is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu şubede bu ürünün fiyatı yok")
        shown = store_price

    since = datetime.now(timezone.utc) - timedelta(days=1)
    recent = (await db.scalars(
        select(PriceReport).where(PriceReport.user_id == user.id, PriceReport.created_at > since)
    )).all()
    # Aynı gün aynı ürün/şube için ikinci bildirim yeni kayıt açmaz, öncekini günceller
    same = next((r for r in recent if r.product_id == product.id and r.store_id == body.store_id), None)
    if same is None and len(recent) >= MAX_PER_DAY:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Bugün için bildirim sınırına ulaştın, teşekkürler!")
    report = same or PriceReport(user_id=user.id, group_id=group_id, product_id=product.id, store_id=body.store_id)
    report.shown_price = shown
    report.reported_price = body.reported_price
    report.note = (body.note or "").strip() or None
    if same is None:
        db.add(report)
    await db.commit()
    await db.refresh(report)
    return PriceReportOut(
        id=report.id, shown_price=report.shown_price, reported_price=report.reported_price,
        detail="Teşekkürler! Bu fiyatı kontrol edeceğiz.",
    )


async def open_report_count(db: AsyncSession, product_id: int) -> int:
    return await db.scalar(
        select(func.count()).select_from(PriceReport).where(PriceReport.product_id == product_id, PriceReport.status == "open")
    ) or 0
