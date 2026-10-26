from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.models import PriceAlert
from app.schemas.alerts import AlertCount, AlertCreate, AlertOut
from app.services import alerts as svc

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(user: CurrentUser, db: DbSession) -> list[AlertOut]:
    """Alarmlar sayfası: her alarmın güncel fiyatı ve tetiklenip tetiklenmediği."""
    return await svc.evaluate(db, user)


@router.get("/unread", response_model=AlertCount)
async def unread_count(user: CurrentUser, db: DbSession) -> AlertCount:
    """Alt menüdeki 🔔 rozeti: fiyatı düşen ve henüz görülmemiş alarm sayısı."""
    return AlertCount(unread=sum(1 for a in await svc.evaluate(db, user) if a.unread))


@router.post("", response_model=list[AlertOut], status_code=status.HTTP_201_CREATED)
async def create_alert(body: AlertCreate, user: CurrentUser, db: DbSession) -> list[AlertOut]:
    """"Fiyat düşünce haber ver". target_price boşsa şu anki fiyatın altına inince tetiklenir."""
    await svc.upsert(db, user, body)
    return await svc.evaluate(db, user)


@router.post("/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_seen(user: CurrentUser, db: DbSession) -> Response:
    await svc.mark_seen(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: int, user: CurrentUser, db: DbSession) -> Response:
    alert = await db.get(PriceAlert, alert_id)
    if alert is None or alert.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alarm bulunamadı")
    await db.delete(alert)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
