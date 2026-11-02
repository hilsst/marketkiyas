from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.notifications import (
    NotificationOut,
    NotificationSettingsOut,
    NotificationSettingsUpdate,
    PushTokenIn,
    UnreadCount,
)
from app.services import notifications as svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(user: CurrentUser, db: DbSession) -> list[NotificationOut]:
    return await svc.list_notifications(db, user)


@router.get("/unread", response_model=UnreadCount)
async def unread(user: CurrentUser, db: DbSession) -> UnreadCount:
    return UnreadCount(unread=await svc.unread_count(db, user))


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(user: CurrentUser, db: DbSession) -> Response:
    await svc.mark_read(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_one(notification_id: int, user: CurrentUser, db: DbSession) -> Response:
    await svc.mark_read(db, user, notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/settings", response_model=NotificationSettingsOut)
async def get_settings(user: CurrentUser, db: DbSession) -> NotificationSettingsOut:
    row = await svc.get_settings(db, user)
    await db.commit()
    return svc.settings_out(row)


@router.patch("/settings", response_model=NotificationSettingsOut)
async def update_settings(body: NotificationSettingsUpdate, user: CurrentUser, db: DbSession) -> NotificationSettingsOut:
    """Haftalık menü bildirimi: açık/kapalı, gün (0 = Pazartesi) ve saat (İstanbul saati)."""
    return await svc.update_settings(db, user, body)


@router.put("/push-token", status_code=status.HTTP_204_NO_CONTENT)
async def register_push_token(body: PushTokenIn, user: CurrentUser, db: DbSession) -> Response:
    await svc.register_token(db, user, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/push-token", status_code=status.HTTP_204_NO_CONTENT)
async def remove_push_token(token: str, user: CurrentUser, db: DbSession) -> Response:
    await svc.remove_token(db, user, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
