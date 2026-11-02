import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.deps import DbSession, OptionalUser
from app.core.config import settings
from app.schemas.analytics import EventBatch, EventBatchOut
from app.services import analytics as svc

router = APIRouter(tags=["analytics"])


@router.post("/events", response_model=EventBatchOut, status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(
    body: EventBatch, db: DbSession, user: OptionalUser,
    x_device_id: Annotated[str | None, Header()] = None,
    x_load_test: Annotated[str | None, Header()] = None,
) -> EventBatchOut:
    """Uygulamanın topladığı olaylar (açılış, ekran görüntüleme…), en çok 50'lik paketler halinde.
    Misafir de gönderebilir; kişi cihaz kimliğiyle tanınır. X-Load-Test başlığı olan (yük testi) istekler
    kaydedilmez, canlı huni sayıları bozulmasın."""
    if x_load_test:
        return EventBatchOut(accepted=0)
    device_id = svc.clean_device_id(body.device_id) or svc.clean_device_id(x_device_id)
    if device_id is None and user is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cihaz kimliği gerekli")
    accepted = await svc.record_client_events(
        db, device_id=device_id, user_id=user.id if user else None,
        events=[(e.name, e.at, e.props) for e in body.events],
    )
    return EventBatchOut(accepted=accepted)


@router.get("/analytics/report", include_in_schema=False)
async def analytics_report(
    db: DbSession,
    x_analytics_token: Annotated[str | None, Header()] = None,
    days: Annotated[int, Query(ge=1, le=365)] = 28,
) -> dict[str, Any]:
    """Huni ve geri dönüş raporu. Yalnız ANALYTICS_TOKEN ayarlıysa ve başlıkta doğru verilirse açılır."""
    if not settings.analytics_token or not secrets.compare_digest(x_analytics_token or "", settings.analytics_token):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
    until = datetime.now(timezone.utc)
    return (await svc.build_report(db, until - timedelta(days=days), until)).as_dict()
