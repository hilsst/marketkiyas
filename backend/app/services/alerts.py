"""Fiyat alarmları: tetiklenme okunurken, kullanıcının o anki fiyatlarıyla hesaplanır."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GroupMember, PriceAlert, ProductGroup, User
from app.schemas.alerts import AlertCreate, AlertOut
from app.services.catalog import group_summary
from app.services.pricing import build_resolver


def _threshold(alert: PriceAlert) -> Decimal | None:
    if alert.target_price is not None:
        return alert.target_price
    if alert.baseline_price is not None:
        return alert.baseline_price - Decimal("0.01")
    return None


async def _load(db: AsyncSession, user: User) -> list[PriceAlert]:
    return list(
        await db.scalars(
            select(PriceAlert)
            .where(PriceAlert.user_id == user.id)
            .options(
                selectinload(PriceAlert.group)
                .selectinload(ProductGroup.members)
                .selectinload(GroupMember.product)
            )
            .order_by(PriceAlert.created_at.desc(), PriceAlert.id.desc())
        )
    )


async def evaluate(db: AsyncSession, user: User) -> list[AlertOut]:
    """Alarmların güncel fiyatını hesaplar; eşiğin altına inenleri tetikler, yeniden yükselenleri sıfırlar."""
    alerts = await _load(db, user)
    resolver = await build_resolver(db, user.id, [m.product_id for a in alerts for m in a.group.members])
    now = datetime.now(timezone.utc)
    out = []
    for alert in alerts:
        summary = group_summary(alert.group, resolver)
        current = summary.min_price
        cheapest = min(summary.market_prices, key=lambda m: m.min_price, default=None)
        threshold = _threshold(alert)
        hit = current is not None and threshold is not None and current <= threshold
        if hit and alert.triggered_at is None:
            alert.triggered_at, alert.triggered_price, alert.seen_at = now, current, None
        elif not hit and alert.triggered_at is not None:
            alert.triggered_at = alert.triggered_price = None
        if alert.baseline_price is None and current is not None:
            alert.baseline_price = current  # alarm fiyat yokken kurulduysa ilk görülen fiyat
        out.append(
            AlertOut(
                id=alert.id,
                group_id=alert.group_id,
                group_name=alert.group.name,
                category_id=alert.group.category_id,
                image_url=alert.group.image_url,
                quantity=alert.group.quantity,
                unit=alert.group.unit,
                target_price=alert.target_price,
                baseline_price=alert.baseline_price,
                current_price=current,
                current_market_id=cheapest.market_id if cheapest else None,
                triggered=hit,
                triggered_at=alert.triggered_at,
                unread=hit and alert.seen_at is None,
                created_at=alert.created_at,
            )
        )
    await db.commit()
    return out


async def upsert(db: AsyncSession, user: User, body: AlertCreate) -> None:
    """Aynı ürüne ikinci alarm açılmaz; hedef fiyat güncellenir ve alarm yeniden kurulur."""
    group = await db.scalar(
        select(ProductGroup)
        .where(ProductGroup.id == body.group_id)
        .options(selectinload(ProductGroup.members).selectinload(GroupMember.product))
    )
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün grubu bulunamadı")
    resolver = await build_resolver(db, user.id, [m.product_id for m in group.members])
    current = group_summary(group, resolver).min_price

    alert = await db.scalar(
        select(PriceAlert).where(PriceAlert.user_id == user.id, PriceAlert.group_id == group.id)
    )
    if alert is None:
        alert = PriceAlert(user_id=user.id, group_id=group.id)
        db.add(alert)
    alert.target_price = body.target_price
    alert.baseline_price = current
    alert.triggered_at = alert.triggered_price = alert.seen_at = None
    await db.commit()


async def mark_seen(db: AsyncSession, user: User) -> None:
    now = datetime.now(timezone.utc)
    for alert in await _load(db, user):
        if alert.triggered_at is not None and alert.seen_at is None:
            alert.seen_at = now
    await db.commit()
