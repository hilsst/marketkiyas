"""Faz 1: misafir başlangıç, fiyat güveni ("son güncelleme", "bu fiyat yanlış") ve indirimden menü."""

from datetime import timedelta
from decimal import Decimal as D

from sqlalchemy import select, update

from app.api.routes import auth as auth_routes
from app.models import PriceHistory, PriceReport, Product, ShoppingList, User
from app.services.guests import purge_empty_guests
from tests.test_features import milk  # noqa: F401  (fixture)
from tests.test_meals import kitchen  # noqa: F401  (fixture)


async def _guest(client):
    r = await client.post("/api/auth/guest")
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["is_guest"] is True and body["user"]["email"] is None
    return {"Authorization": f"Bearer {body['access_token']}"}, body


async def test_guest_can_plan_and_list_but_not_share(client):
    headers, body = await _guest(client)
    # Misafir anahtarı uzun ömürlü: şifresi olmadığı için anahtar biterse verisi kaybolur
    assert body["expires_in"] >= 300 * 24 * 3600
    me = (await client.get("/api/auth/me", headers=headers)).json()
    assert me["is_guest"] is True and me["has_password"] is False

    lid = (await client.post("/api/lists", json={"name": "Ev"}, headers=headers)).json()["id"]
    r = await client.post(f"/api/lists/{lid}/share", headers=headers)
    assert r.status_code == 403 and "hesap" in r.json()["detail"]
    assert (await client.post("/api/lists/join", json={"code": "ABCDEFGH"}, headers=headers)).status_code == 403
    assert (await client.post("/api/family", json={"name": "Ailem"}, headers=headers)).status_code == 403
    # Ana sayfa aileyi sorar: misafire boş döner, hata vermez
    fam = await client.get("/api/family", headers=headers)
    assert fam.status_code == 200 and fam.json() == {"family": None, "invites": []}
    plans = await client.post("/api/meal-plans", json={"period": "daily"}, headers=headers)
    assert plans.status_code == 201


async def test_upgrade_keeps_data(client):
    headers, _ = await _guest(client)
    lid = (await client.post("/api/lists", json={"name": "Haftalık"}, headers=headers)).json()["id"]

    r = await client.post(
        "/api/auth/upgrade", headers=headers,
        json={"email": "Misafir@Example.com", "password": "gizli-sifre-123", "full_name": "Ayşe"},
    )
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["is_guest"] is False and user["email"] == "misafir@example.com" and user["full_name"] == "Ayşe"
    new = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert [l["id"] for l in (await client.get("/api/lists", headers=new)).json()] == [lid]
    # Artık paylaşabilir ve e-postasıyla giriş yapabilir
    assert (await client.post(f"/api/lists/{lid}/share", headers=new)).status_code == 200
    login = await client.post("/api/auth/login", json={"email": "misafir@example.com", "password": "gizli-sifre-123"})
    assert login.status_code == 200
    # Gerçek hesap ikinci kez yükseltilemez
    again = await client.post("/api/auth/upgrade", headers=new, json={"email": "x@example.com", "password": "gizli-sifre-123"})
    assert again.status_code == 409


async def test_upgrade_with_taken_email(client, auth_headers):
    headers, _ = await _guest(client)
    r = await client.post(
        "/api/auth/upgrade", headers=headers, json={"email": "kemal@example.com", "password": "gizli-sifre-123"}
    )
    assert r.status_code == 409 and "giriş" in r.json()["detail"]


async def test_guest_rate_limit(client, monkeypatch):
    monkeypatch.setattr(auth_routes.settings, "guest_per_ip_per_hour", 2)
    auth_routes._guest_starts.clear()
    assert (await client.post("/api/auth/guest")).status_code == 201
    assert (await client.post("/api/auth/guest")).status_code == 201
    assert (await client.post("/api/auth/guest")).status_code == 429
    auth_routes._guest_starts.clear()


async def test_purge_only_empty_old_guests(client, db):
    auth_routes._guest_starts.clear()
    keep_headers, _ = await _guest(client)
    await client.post("/api/lists", json={"name": "Ev"}, headers=keep_headers)
    await _guest(client)  # boş
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "gizli-sifre-123"})

    assert await purge_empty_guests(db) == 0  # henüz eski değil
    await db.execute(update(User).values(updated_at=User.updated_at - timedelta(days=40)))
    await db.commit()
    assert await purge_empty_guests(db) == 1
    users = (await db.scalars(select(User))).all()
    assert len(users) == 2 and sum(u.is_guest for u in users) == 1
    assert len((await db.scalars(select(ShoppingList))).all()) == 1


# --- Fiyat güveni ---------------------------------------------------------------------------


async def test_price_updated_at_and_report(client, db, milk):  # noqa: F811
    group_id, ids = milk
    detail = (await client.get(f"/api/products/{group_id}")).json()
    # Şube seçilmemiş: son fiyat kaydının zamanı
    assert all(p["price_updated_at"] for p in detail["products"])

    auth_routes._guest_starts.clear()
    headers, _ = await _guest(client)
    url = f"/api/products/{group_id}/price-reports"
    r = await client.post(url, headers=headers, json={"product_id": ids["bim"], "reported_price": "45.50", "note": "kasada"})
    assert r.status_code == 201
    # Gösterilen fiyat istemciden değil sunucudan gelir
    assert D(r.json()["shown_price"]) == D("40.00") and D(r.json()["reported_price"]) == D("45.50")
    # Aynı gün aynı ürün: yeni kayıt açmaz, öncekini günceller
    r = await client.post(url, headers=headers, json={"product_id": ids["bim"], "reported_price": "46.00"})
    assert r.status_code == 201
    reports = (await db.scalars(select(PriceReport))).all()
    assert len(reports) == 1 and reports[0].reported_price == D("46.00")

    # Başka gruptaki ürün bildirilemez; giriş zorunlu
    assert (await client.post("/api/products/999999/price-reports", headers=headers, json={"product_id": ids["bim"]})).status_code == 404
    assert (await client.post(url, json={"product_id": ids["bim"]})).status_code == 401


async def test_price_report_daily_limit(client, db, milk, monkeypatch):  # noqa: F811
    from app.services import reports

    group_id, ids = milk
    monkeypatch.setattr(reports, "MAX_PER_DAY", 1)
    auth_routes._guest_starts.clear()
    headers, _ = await _guest(client)
    url = f"/api/products/{group_id}/price-reports"
    assert (await client.post(url, headers=headers, json={"product_id": ids["bim"]})).status_code == 201
    assert (await client.post(url, headers=headers, json={"product_id": ids["a101"]})).status_code == 429


# --- İndirimden menü ------------------------------------------------------------------------


async def test_deal_ingredients_and_prefer(client, db, kitchen):  # noqa: F811
    _, ids = kitchen
    assert (await client.get("/api/deal-menu/ingredients")).json() == []
    # Mercimek 80 TL'den 60 TL'ye indi (%25); sabun da indirimde ama malzeme değil
    for gid, before in ((ids["mercimek"], "80.00"), (ids["sabun"], "90.00")):
        pid = await db.scalar(
            select(Product.id).where(Product.external_id.like(f"m{gid}-%")).order_by(Product.current_price).limit(1)
        )
        db.add(PriceHistory(product_id=pid, price=D(before)))
    await db.commit()

    items = (await client.get("/api/deal-menu/ingredients")).json()
    names = [i["name"].lower() for i in items]
    assert any("mercimek" in n for n in names)
    assert not any("sabun" in i["product_name"].lower() for i in items)
    lentil = next(i for i in items if "mercimek" in i["name"].lower())
    assert lentil["source"] == "deal" and lentil["discount_percent"] == 25 and lentil["recipe_count"] >= 1

    auth_routes._guest_starts.clear()
    headers, _ = await _guest(client)
    r = await client.post("/api/meal-plans", headers=headers, json={"period": "weekly", "prefer": [lentil["name"]]})
    assert r.status_code == 201
