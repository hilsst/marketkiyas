"""Haftalık menü bildirimi: kullanıcının seçtiği gün/saatte (varsayılan Pazar 10:00, İstanbul saati) gelecek
haftanın menüsü indirimler gözetilerek hazırlanır ve bildirim olarak yazılır.

- Uygulama içi bildirim her zaman yazılır; push yalnız `expo_push_enabled` açıksa ve cihaz anahtarı varsa gider.
- İş birden çok kez (ya da gecikmeli) çalışsa da kullanıcı başına hafta başına tek bildirim olur
  (benzersiz kısıt + ön kontrol). Saat geçtiyse aynı gün içinde yakalanır.
- Menü kullanıcının son planının ayarlarıyla (mutfak, kişi sayısı, diyet, alerji) kurulur; plan yoksa varsayılanlarla.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import MealPlan, Notification, NotificationSettings, PushToken, User
from app.models.meals import MealSlot, PlanPeriod
from app.schemas.notifications import NotificationOut, NotificationSettingsOut, NotificationSettingsUpdate, PushTokenIn
from app.services import meals

log = logging.getLogger("marketkiyas.notifications")

TZ = ZoneInfo("Europe/Istanbul")
KIND = "weekly_menu"
Sender = Callable[[list[str], str, str, dict], Awaitable[None]]


# --- Tercihler ve cihaz anahtarları ---------------------------------------------------------


async def get_settings(db: AsyncSession, user: User) -> NotificationSettings:
    row = await db.get(NotificationSettings, user.id)
    if row is None:
        row = NotificationSettings(user_id=user.id, weekly_menu_enabled=True, weekly_menu_weekday=6, weekly_menu_hour=10)
        db.add(row)
        await db.flush()
    return row


def settings_out(row: NotificationSettings) -> NotificationSettingsOut:
    return NotificationSettingsOut(
        weekly_menu_enabled=row.weekly_menu_enabled, weekly_menu_weekday=row.weekly_menu_weekday,
        weekly_menu_hour=row.weekly_menu_hour,
    )


async def update_settings(db: AsyncSession, user: User, body: NotificationSettingsUpdate) -> NotificationSettingsOut:
    row = await get_settings(db, user)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    await db.commit()
    return settings_out(row)


async def register_token(db: AsyncSession, user: User, body: PushTokenIn) -> None:
    """Aynı cihaz anahtarı başka hesapta kayıtlıysa o hesaptan alınır (cihazda hesap değişti)."""
    existing = await db.scalar(select(PushToken).where(PushToken.token == body.token))
    if existing is None:
        db.add(PushToken(user_id=user.id, token=body.token, platform=body.platform))
    else:
        existing.user_id = user.id
        existing.platform = body.platform or existing.platform
    await db.commit()


async def remove_token(db: AsyncSession, user: User, token: str) -> None:
    row = await db.scalar(select(PushToken).where(PushToken.token == token, PushToken.user_id == user.id))
    if row is not None:
        await db.delete(row)
        await db.commit()


# --- Bildirim listesi -----------------------------------------------------------------------


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id, kind=n.kind, title=n.title, body=n.body, plan_id=n.plan_id, week_start=n.week_start.isoformat(),
        created_at=n.created_at, read=n.read_at is not None,
    )


async def list_notifications(db: AsyncSession, user: User, limit: int = 50) -> list[NotificationOut]:
    rows = (await db.scalars(
        select(Notification).where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    )).all()
    return [_out(n) for n in rows]


async def unread_count(db: AsyncSession, user: User) -> int:
    return await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ) or 0


async def mark_read(db: AsyncSession, user: User, notification_id: int | None = None) -> None:
    query = select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    if notification_id is not None:
        query = query.where(Notification.id == notification_id)
    now = datetime.now(timezone.utc)
    for n in (await db.scalars(query)).all():
        n.read_at = now
    await db.commit()


# --- Haftalık menü --------------------------------------------------------------------------


def target_week(local_now: datetime) -> date:
    """Menünün başladığı Pazartesi: bugün Pazartesi ise bugün, değilse gelecek Pazartesi."""
    today = local_now.date()
    return today + timedelta(days=(7 - today.weekday()) % 7)


def is_due(local_now: datetime, prefs: NotificationSettings) -> bool:
    return (
        prefs.weekly_menu_enabled
        and local_now.weekday() == prefs.weekly_menu_weekday
        and local_now.hour >= prefs.weekly_menu_hour
    )


def _money(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", ".") + " TL"


async def _last_plan(db: AsyncSession, user_id: int) -> MealPlan | None:
    return await db.scalar(
        select(MealPlan).where(MealPlan.user_id == user_id)
        .options(selectinload(MealPlan.cuisine), selectinload(MealPlan.entries))
        .order_by(MealPlan.created_at.desc(), MealPlan.id.desc()).limit(1)
    )


async def build_menu(db: AsyncSession, user: User, start: date) -> tuple[MealPlan, Decimal, int]:
    """(plan, alışveriş tutarı, indirimli malzeme sayısı). Son planın tercihleri, indirimler gözetilerek."""
    last = await _last_plan(db, user.id)
    kwargs: dict = dict(
        period=PlanPeriod.WEEKLY, cuisine_slugs=[], servings=4, slots=[MealSlot.LUNCH, MealSlot.DINNER],
        courses=list(meals.COURSE_ORDER), diets=[], avoid=[],
    )
    if last is not None:
        kwargs.update(
            cuisine_slugs=last.cuisine_slugs, servings=last.servings, slots=last.slots, courses=last.course_list,
            diets=last.diet_list, avoid=last.avoid_list, have=last.have_list,
        )
    plan, _ = await meals.create_plan(
        db, user, start=start, name=f"Haftalık menü {start.strftime('%d.%m')}", days=7, low_waste=True,
        from_deals=True, **kwargs,
    )
    detail = await meals.to_detail(db, plan, user.id)
    # Broşür ipuçları sepet fiyatına girmediği için "indirimde" sayısına katılmaz
    return plan, detail.cost.purchase_total, sum(1 for d in detail.deals if d.source == "katalog")


async def create_weekly(db: AsyncSession, user: User, week_start: date) -> Notification | None:
    """Kullanıcının bu haftaki menü bildirimini yazar; zaten varsa None.

    Önce benzersiz kısıtla yer tutulur (iki worker aynı anda çalışsa da yalnız biri devam eder), sonra plan
    kurulur. Plan kurulamazsa yer bırakılır ki sonraki tur yeniden denesin; plan asla bildirimsiz kalmaz."""
    reserved = await db.scalar(
        pg_insert(Notification).values(
            user_id=user.id, kind=KIND, title="Haftalık menünüz hazırlanıyor", body="", week_start=week_start, data="{}",
        ).on_conflict_do_nothing(constraint="uq_notifications_user_kind_week").returning(Notification.id)
    )
    await db.commit()
    if reserved is None:
        return None
    try:
        plan, total, deal_count = await build_menu(db, user, week_start)
    except Exception:
        await db.rollback()
        await db.execute(delete(Notification).where(Notification.id == reserved))
        await db.commit()
        raise
    note = await db.get(Notification, reserved)
    note.title = "Haftalık menünüz hazır 🍲"
    note.body = f"Bu haftanın menüsü hazır: {_money(total)}"
    if deal_count:
        note.body += f" · {deal_count} malzeme indirimde"
    note.plan_id = plan.id
    note.data = json.dumps({"plan_id": plan.id})
    await db.flush()
    return note


async def expo_send(tokens: list[str], title: str, body: str, data: dict) -> None:
    messages = [{"to": t, "title": title, "body": body, "data": data, "sound": "default"} for t in tokens]
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(settings.expo_push_url, json=messages)
        response.raise_for_status()


async def send_weekly_menus(
    db: AsyncSession, now: datetime | None = None, sender: Sender | None = None
) -> dict[str, int]:
    """Zamanı gelen kullanıcılar için menü kurar, bildirim yazar ve (açıksa) push gönderir.
    Bir kullanıcıdaki hata diğerlerini durdurmaz."""
    local = (now or datetime.now(timezone.utc)).astimezone(TZ)
    week = target_week(local)
    stats = {"checked": 0, "created": 0, "pushed": 0, "failed": 0}
    sender = sender or (expo_send if settings.expo_push_enabled else None)
    # Zamanı gelenler tek sorguda seçilir (satırı olmayan ama cihaz anahtarı olan kullanıcıda varsayılanlar: Pazar 10)
    weekday = func.coalesce(NotificationSettings.weekly_menu_weekday, 6)
    hour = func.coalesce(NotificationSettings.weekly_menu_hour, 10)
    enabled = func.coalesce(NotificationSettings.weekly_menu_enabled, True)
    has_token = select(PushToken.id).where(PushToken.user_id == User.id).exists()
    already = select(Notification.id).where(
        Notification.user_id == User.id, Notification.kind == KIND, Notification.week_start == week
    ).exists()
    query = (
        select(User.id).outerjoin(NotificationSettings, NotificationSettings.user_id == User.id)
        .where(
            User.is_active, enabled, weekday == local.weekday(), hour <= local.hour, ~already,
            (NotificationSettings.user_id.is_not(None)) | has_token,
        ).order_by(User.id)
    )
    user_ids = list((await db.scalars(query)).all())
    for user_id in user_ids:
        user = await db.get(User, user_id)
        stats["checked"] += 1
        try:
            note = await create_weekly(db, user, week)  # plan kurulurken kendi commit'ini yapar
            await db.commit()
        except Exception:
            await db.rollback()
            log.exception("haftalık menü kurulamadı: kullanıcı %s", user_id)
            stats["failed"] += 1
            continue
        if note is None:
            continue
        stats["created"] += 1
        tokens = list((await db.scalars(select(PushToken.token).where(PushToken.user_id == user_id))).all())
        if sender and tokens:
            try:
                await sender(tokens, note.title, note.body, {"plan_id": note.plan_id, "kind": KIND})
                note.pushed_at = datetime.now(timezone.utc)
                await db.commit()
                stats["pushed"] += 1
            except Exception:
                await db.rollback()
                log.exception("push gönderilemedi: kullanıcı %s", user_id)
    return stats
