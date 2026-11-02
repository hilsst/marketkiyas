from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.models import AnalyticsEvent
from app.services import analytics
from tests.test_meals import kitchen  # noqa: F401  (fixture)

DEVICE = "0f8c6a2e-1111-4a5b-9c3d-abcdef012345"


async def _events(db):
    db.expire_all()
    return (await db.scalars(select(AnalyticsEvent).order_by(AnalyticsEvent.id))).all()


async def test_funnel_steps_recorded_by_server(client, db, kitchen):  # noqa: F811
    h = {"X-Device-Id": DEVICE}
    reg = await client.post("/api/auth/register", headers=h, json={"email": "misafir@example.com", "password": "gizli-sifre-123"})
    h["Authorization"] = f"Bearer {reg.json()['access_token']}"
    user_id = reg.json()["user"]["id"]

    plan = (await client.post("/api/meal-plans", headers=h, json={
        "period": "daily", "servings": 2, "meal_slots": ["kahvalti"], "courses": ["ana"],
    })).json()
    out = (await client.post(f"/api/meal-plans/{plan['id']}/to-list", headers=h, json={})).json()
    lid = out["list"]["id"]
    assert (await client.post(f"/api/lists/{lid}/apply", headers=h, json={"plan_type": "combination"})).status_code == 200
    assert (await client.post(f"/api/lists/{lid}/complete", headers=h)).status_code == 200
    # Başarısız istek olay yazmaz (tamamlanmış liste tekrar tamamlanamaz)
    assert (await client.post(f"/api/lists/{lid}/complete", headers=h)).status_code == 409

    events = await _events(db)
    assert [e.name for e in events] == ["signed_up", "plan_created", "plan_to_list", "shopping_started", "shopping_completed"]
    assert all(e.source == "server" and e.device_id == DEVICE for e in events)
    assert events[0].user_id is None  # kayıt anında token yok; cihaz kimliği bağlar
    assert all(e.user_id == user_id for e in events[1:])
    assert events[2].props == {"plan_id": plan["id"]}
    assert events[3].props == {"list_id": lid}


async def test_no_identity_no_event_and_bad_device_ignored(client, db):
    r = await client.post("/api/auth/register", headers={"X-Device-Id": "bad id!"},
                          json={"email": "b@example.com", "password": "gizli-sifre-123"})
    assert r.status_code == 201
    # Geçersiz cihaz kimliği yok sayılır; token da yok, olay yazılmaz
    assert await _events(db) == []


async def test_client_event_batch(client, db):
    now = datetime.now(timezone.utc)
    r = await client.post("/api/events", headers={"X-Device-Id": DEVICE}, json={"events": [
        {"name": "app_open", "at": (now - timedelta(minutes=3)).isoformat(), "props": {"cold": True}},
        {"name": "screen_view", "props": {"screen": "/meals", "nested": {"x": 1}, "Bad Key": 1, "long": "a" * 500}},
        {"name": "app_open", "at": (now + timedelta(days=3)).isoformat()},  # saati ileride telefon
    ]})
    assert r.status_code == 202, r.text
    assert r.json() == {"accepted": 3}
    events = await _events(db)
    assert [e.name for e in events] == ["app_open", "screen_view", "app_open"]
    assert all(e.source == "app" and e.device_id == DEVICE and e.user_id is None for e in events)
    assert events[0].occurred_at < now - timedelta(minutes=2)
    assert events[1].props == {"screen": "/meals", "long": "a" * 200}
    assert abs((events[2].occurred_at - now).total_seconds()) < 60


async def test_client_events_validation(client, auth_headers):
    ok = {"events": [{"name": "app_open"}]}
    # Cihaz kimliği de oturum da yok
    assert (await client.post("/api/events", json=ok)).status_code == 422
    # Oturum varsa cihaz kimliği gerekmez
    assert (await client.post("/api/events", headers=auth_headers, json=ok)).status_code == 202
    # Sunucunun kaydettiği huni adımı telefondan gelemez (çift sayım olmasın)
    bad = {"device_id": DEVICE, "events": [{"name": "plan_created"}]}
    assert (await client.post("/api/events", json=bad)).status_code == 422
    assert (await client.post("/api/events", json={"device_id": DEVICE, "events": [{"name": "Ekran Açıldı"}]})).status_code == 422
    too_many = {"device_id": DEVICE, "events": [{"name": "tap"}] * 51}
    assert (await client.post("/api/events", json=too_many)).status_code == 422


async def _add(db, actor, name, at, user_id=None):
    db.add(AnalyticsEvent(name=name, source="server", device_id=actor, user_id=user_id, occurred_at=at, props={}))


async def test_report_funnel_retention_and_gate(db):
    now = datetime(2026, 12, 31, 12, tzinfo=timezone.utc)
    d0 = now - timedelta(days=40)
    # a: tam huni, 2 farklı haftada plan, 4. haftada geri geliyor
    for name, day in [("app_open", 0), ("plan_created", 0), ("plan_to_list", 0), ("shopping_started", 1),
                      ("shopping_completed", 1), ("plan_created", 8), ("app_open", 24)]:
        await _add(db, "device-aaaa", name, d0 + timedelta(days=day))
    # b: plan kurdu, listeye taşımadan alışverişe başladı (sıralı huniye girmez), geri gelmedi
    for name, day in [("app_open", 0), ("plan_created", 0), ("shopping_started", 0)]:
        await _add(db, "device-bbbb", name, d0 + timedelta(days=day, hours=1))
    # c: listeyi plandan ÖNCE taşımış görünüyor (sıra bozuk), 4. hafta dışı (30. gün) gelmiş
    for name, day in [("plan_to_list", 0), ("plan_created", 1), ("app_open", 30)]:
        await _add(db, "device-cccc", name, d0 + timedelta(days=day))
    # d: yeni (5 gün önce), 4. hafta ve 14 gün kapısına henüz uygun değil; cihazsız kullanıcı
    from app.models import User
    u = User(email="d@example.com", password_hash="x")
    db.add(u)
    await db.flush()
    await _add(db, None, "plan_created", now - timedelta(days=5), user_id=u.id)
    await db.commit()

    r = await analytics.build_report(db, now - timedelta(days=60), now, now=now)
    assert r.active_actors == 4
    steps = {s.name: s for s in r.funnel}
    assert steps["plan_created"].actors == 4
    assert steps["plan_to_list"].actors == 1  # yalnız a (c'de sıra ters)
    assert steps["shopping_started"].actors == 1
    assert steps["shopping_completed"].actors == 1
    assert steps["plan_to_list"].rate_from_previous == 0.25
    assert r.week4_eligible == 3 and r.week4_returned == 1 and r.week4_rate == round(1 / 3, 4)
    assert r.gate_eligible == 3
    assert r.gate_two_week_planners == 1  # a: 0. ve 8. gün farklı haftalar
    assert r.gate_plan_to_list == 2  # a ve c
    assert r.event_counts["plan_created"] == 5
    text = analytics.format_report(r)
    assert "4. hafta geri dönüş: 1/3" in text and "hedef ≥ %50" in text


async def test_report_endpoint_requires_token(client, monkeypatch):
    assert (await client.get("/api/analytics/report")).status_code == 404
    monkeypatch.setattr(settings, "analytics_token", "gizli-rapor")
    assert (await client.get("/api/analytics/report", headers={"X-Analytics-Token": "yanlis"})).status_code == 404
    r = await client.get("/api/analytics/report", headers={"X-Analytics-Token": "gizli-rapor"}, params={"days": 7})
    assert r.status_code == 200
    assert [s["name"] for s in r.json()["funnel"]] == list(analytics.FUNNEL_STEPS)


async def test_deleted_account_erases_events(client, db, auth_headers):
    h = {**auth_headers, "X-Device-Id": DEVICE}
    await client.post("/api/events", headers=h, json={"events": [{"name": "app_open"}]})
    await client.post("/api/events", headers={"X-Device-Id": DEVICE}, json={"events": [{"name": "screen_view"}]})
    await client.post("/api/events", headers={"X-Device-Id": "other-device-1234"}, json={"events": [{"name": "app_open"}]})
    assert (await client.request("DELETE", "/api/auth/me", headers=h, json={"password": "gizli-sifre-123"})).status_code == 204
    events = await _events(db)
    assert [e.device_id for e in events] == ["other-device-1234"]


async def test_load_test_header_is_not_recorded(client, db):
    h = {"X-Device-Id": DEVICE, "X-Load-Test": "1"}
    assert (await client.post("/api/events", headers=h, json={"events": [{"name": "app_open"}]})).json() == {"accepted": 0}
    reg = await client.post("/api/auth/register", headers=h, json={"email": "y@example.com", "password": "gizli-sifre-123"})
    h["Authorization"] = f"Bearer {reg.json()['access_token']}"
    await client.post("/api/meal-plans", headers=h, json={"period": "daily"})
    assert await _events(db) == []


async def test_funnel_counts_step_after_earlier_unrelated_activity(db):
    now = datetime(2026, 12, 31, tzinfo=timezone.utc)
    t = now - timedelta(days=10)
    # Önce plansız bir listeyle alışveriş, sonra asıl huni
    for name, h in [("shopping_started", 0), ("shopping_completed", 1), ("plan_created", 5),
                    ("plan_to_list", 6), ("shopping_started", 7), ("shopping_completed", 8)]:
        await _add(db, "device-eeee", name, t + timedelta(hours=h))
    await db.commit()
    r = await analytics.build_report(db, now - timedelta(days=30), now, now=now)
    assert [s.actors for s in r.funnel] == [1, 1, 1, 1]
