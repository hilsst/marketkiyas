from datetime import date

from fastapi import APIRouter
from sqlalchemy import func, or_, select

from app.api.deps import DbSession
from app.models import AktuelItem
from app.schemas.aktuel import AktuelItemOut, AktuelOut, AktuelSourceOut
from app.services.aktuel import AKTUEL_SOURCES

router = APIRouter(tags=["aktuel"])


@router.get("/aktuel", response_model=AktuelOut)
async def list_aktuel(db: DbSession, market: str | None = None) -> AktuelOut:
    """Marketlerin aktüel ürünleri. Sıra: başlamış broşürler en yeniden eskiye, sonra "Yakında"lar
    en yakın tarihten. Süresi biten indirim broşürleri (ends_on geçmiş) gösterilmez."""
    today = date.today()
    counts = {
        slug: (count, updated)
        for slug, count, updated in await db.execute(
            select(AktuelItem.market_slug, func.count(), func.max(AktuelItem.seen_at))
            .where(or_(AktuelItem.ends_on.is_(None), AktuelItem.ends_on >= today))
            .group_by(AktuelItem.market_slug)
        )
    }
    sources = [
        AktuelSourceOut(
            slug=s.slug,
            name=s.name,
            url=s.url,
            automatic=s.automatic,
            item_count=counts.get(s.slug, (0, None))[0],
            updated_at=counts.get(s.slug, (0, None))[1],
        )
        for s in AKTUEL_SOURCES
    ]

    query = select(AktuelItem).where(or_(AktuelItem.ends_on.is_(None), AktuelItem.ends_on >= today))
    if market:
        query = query.where(AktuelItem.market_slug == market)
    rows = (await db.scalars(query.order_by(AktuelItem.id))).all()

    def upcoming(item: AktuelItem) -> bool:
        return item.starts_on is not None and item.starts_on > today

    def order(item: AktuelItem):
        started = item.starts_on or today
        return (1, started.toordinal()) if upcoming(item) else (0, -started.toordinal())

    fields = [f for f in AktuelItemOut.model_fields if f != "upcoming"]
    items = [
        AktuelItemOut(**{f: getattr(item, f) for f in fields}, upcoming=upcoming(item))
        for item in sorted(rows, key=order)
    ]
    return AktuelOut(sources=sources, items=items)
