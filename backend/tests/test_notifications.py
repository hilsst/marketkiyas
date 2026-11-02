"""Haftalık menü bildirimi: zamanlama, tek seferlik üretim, push, tercihler."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.models import MealPlan, Notification, PushToken, User
from app.services import notifications as svc
from app.services.notifications import TZ
from tests.test_meals import kitchen  # noqa: F401  (fixture)

# 1 Kasım 2026 Pazar 10:30 İstanbul (UTC+3) -> menü 2 Kasım Pazartesi'den başlar
SUNDAY_10_30 = datetime(2026, 11, 1, 7, 30, tzinfo=timezone.utc)
SUNDAY_09_00 = datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)
SATURDAY = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


class Capture:
    def __init__(self):
        self.calls = []

    async def __call__(self, tokens, title, body, data):
        self.calls.append((tokens, title, body, data))


def test_target_week_and_due():
    sunday = SUNDAY_10_30.astimezone(TZ)
    assert svc.target_week(sunday).isoformat() == "2026-11-02"
    monday = datetime(2026, 11, 2, 9, 0, tzinfo=TZ)
    assert svc.target_week(monday).isoformat() == "2026-11-02"
    assert svc.target_week(datetime(2026, 11, 4, 9, 0, tzinfo=TZ)).isoformat() == "2026-11-09"


async def _token(client, headers, token="ExponentPushToken[abc123]"):
    r = await client.put("/api/notifications/push-token", headers=headers, json={"token": token, "platform": "android"})
    assert r.status_code == 204


async def test_weekly_menu_created_once_and_pushed(client, db, auth_headers, kitchen):  # noqa: F811
    await _token(client, auth_headers)
    sender = Capture()

    assert (await svc.send_weekly_menus(db, SUNDAY_09_00, sender))["created"] == 0  # saat gelmedi
    assert (await svc.send_weekly_menus(db, SATURDAY, sender))["created"] == 0  # gün değil
    assert sender.calls == []

    stats = await svc.send_weekly_menus(db, SUNDAY_10_30, sender)
    assert stats == {"checked": 1, "created": 1, "pushed": 1, "failed": 0}, stats
    tokens, title, body, data = sender.calls[0]
    assert tokens == ["ExponentPushToken[abc123]"] and "menü" in title.lower()
    assert body.startswith("Bu haftanın menüsü hazır:") and " TL" in body

    # İş tekrar (ve sonraki saatlerde) çalışsa da ikinci bildirim yok
    again = await svc.send_weekly_menus(db, SUNDAY_10_30, sender)
    assert again["created"] == 0 and len(sender.calls) == 1

    notes = (await client.get("/api/notifications", headers=auth_headers)).json()
    assert len(notes) == 1 and notes[0]["read"] is False and notes[0]["week_start"] == "2026-11-02"
    plan = await db.get(MealPlan, notes[0]["plan_id"])
    assert plan.start_date.isoformat() == "2026-11-02" and plan.days == 7 and plan.from_deals
    assert data["plan_id"] == plan.id
    assert (await client.get(f"/api/meal-plans/{plan.id}", headers=auth_headers)).status_code == 200

    assert (await client.get("/api/notifications/unread", headers=auth_headers)).json() == {"unread": 1}
    assert (await client.post(f"/api/notifications/{notes[0]['id']}/read", headers=auth_headers)).status_code == 204
    assert (await client.get("/api/notifications/unread", headers=auth_headers)).json() == {"unread": 0}


async def test_next_week_gets_new_notification(client, db, auth_headers, kitchen):  # noqa: F811
    await _token(client, auth_headers)
    await svc.send_weekly_menus(db, SUNDAY_10_30, Capture())
    nxt = datetime(2026, 11, 8, 8, 0, tzinfo=timezone.utc)  # bir sonraki Pazar
    assert (await svc.send_weekly_menus(db, nxt, Capture()))["created"] == 1
    weeks = {n.week_start.isoformat() for n in (await db.scalars(select(Notification))).all()}
    assert weeks == {"2026-11-02", "2026-11-09"}


async def test_settings_disable_and_custom_day(client, db, auth_headers, kitchen):  # noqa: F811
    await _token(client, auth_headers)
    r = await client.get("/api/notifications/settings", headers=auth_headers)
    assert r.json() == {"weekly_menu_enabled": True, "weekly_menu_weekday": 6, "weekly_menu_hour": 10}

    await client.patch("/api/notifications/settings", headers=auth_headers, json={"weekly_menu_enabled": False})
    assert (await svc.send_weekly_menus(db, SUNDAY_10_30, Capture()))["created"] == 0

    # Cumartesi 12:00 (İstanbul 15:00) istendi
    r = await client.patch(
        "/api/notifications/settings", headers=auth_headers,
        json={"weekly_menu_enabled": True, "weekly_menu_weekday": 5, "weekly_menu_hour": 14},
    )
    assert r.json()["weekly_menu_weekday"] == 5
    assert (await svc.send_weekly_menus(db, SUNDAY_10_30, Capture()))["created"] == 0
    assert (await svc.send_weekly_menus(db, SATURDAY, Capture()))["created"] == 1
    bad = await client.patch("/api/notifications/settings", headers=auth_headers, json={"weekly_menu_hour": 24})
    assert bad.status_code == 422


async def test_in_app_only_without_sender_and_failed_push_keeps_notification(client, db, auth_headers, kitchen):  # noqa: F811
    await _token(client, auth_headers)

    async def broken(*_):
        raise RuntimeError("expo kapalı")

    stats = await svc.send_weekly_menus(db, SUNDAY_10_30, broken)
    assert stats["created"] == 1 and stats["pushed"] == 0
    note = await db.scalar(select(Notification))
    assert note is not None and note.pushed_at is None  # uygulama içinde yine görünür


async def test_push_token_moves_between_accounts(client, db, auth_headers):
    await _token(client, auth_headers)
    other = await client.post("/api/auth/register", json={"email": "baska@example.com", "password": "gizli-sifre-123"})
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    await _token(client, other_headers)  # aynı cihaz başka hesapla girdi
    rows = (await db.scalars(select(PushToken))).all()
    assert len(rows) == 1
    owner = await db.get(User, rows[0].user_id)
    assert owner.email == "baska@example.com"
    r = await client.delete("/api/notifications/push-token", headers=other_headers, params={"token": "ExponentPushToken[abc123]"})
    assert r.status_code == 204 and (await db.scalars(select(PushToken))).all() == []
