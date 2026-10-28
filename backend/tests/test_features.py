"""Rakip analizinden gelen özellikler: ortak liste, fiyat alarmı, fırsatlar, barkod."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest
from sqlalchemy import select, update

from app.api.routes.products import get_barcode_client
from app.main import app
from app.models import GroupMember, Market, PriceHistory, Product, ProductGroup, Unit
from app.services.normalize import normalize_name
from tests.marketfiyati_fake import FakeMarketFiyati, load


@pytest.fixture
async def milk(db):
    markets = {m.slug: m.id for m in (await db.scalars(select(Market))).all()}
    g = ProductGroup(name="Süt 1 L", normalized_name=normalize_name("Süt 1 L"), unit=Unit.ML, quantity=1000)
    db.add(g)
    await db.flush()
    ids = {}
    for market, brand, price in (("bim", "Sütaş", "40.00"), ("a101", "Pınar", "42.00")):
        p = Product(
            market_id=markets[market],
            external_id=f"{market}-milk",
            name=f"{brand} Süt 1 L",
            normalized_name=normalize_name(f"{brand} Süt 1 L"),
            brand=brand,
            current_price=D(price),
        )
        db.add(p)
        await db.flush()
        db.add(GroupMember(group_id=g.id, product_id=p.id))
        db.add(PriceHistory(product_id=p.id, price=D(price)))
        ids[market] = p.id
    await db.commit()
    return g.id, ids


async def _register(client, email):
    r = await client.post("/api/auth/register", json={"email": email, "password": "gizli-sifre-123", "full_name": email[:4].title()})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _set_price(db, product_id, price):
    await db.execute(update(Product).where(Product.id == product_id).values(current_price=D(price)))
    db.add(PriceHistory(product_id=product_id, price=D(price)))
    await db.commit()


# --- Ortak liste ----------------------------------------------------------------------------


async def test_shared_list(client, auth_headers, milk):
    group_id, _ = milk
    owner = auth_headers
    lid = (await client.post("/api/lists", json={"name": "Ev"}, headers=owner)).json()["id"]
    code = (await client.post(f"/api/lists/{lid}/share", headers=owner)).json()["share_code"]
    assert len(code) == 8
    # Kod sabittir
    assert (await client.post(f"/api/lists/{lid}/share", headers=owner)).json()["share_code"] == code

    ayse = await _register(client, "ayse@example.com")
    assert (await client.get(f"/api/lists/{lid}", headers=ayse)).status_code == 404
    assert (await client.post("/api/lists/join", json={"code": "YANLIS99"}, headers=ayse)).status_code == 404
    r = await client.post("/api/lists/join", json={"code": code.lower()}, headers=ayse)
    assert r.status_code == 200
    assert [m["name"] for m in r.json()["members"]] == ["Ayse"]
    # İkinci katılma üyeliği çoğaltmaz
    await client.post("/api/lists/join", json={"code": code}, headers=ayse)

    r = await client.post(f"/api/lists/{lid}/items", json={"group_id": group_id}, headers=ayse)
    assert r.json()["items"][0]["added_by_name"] == "Ayse"
    owner_view = (await client.get("/api/lists", headers=owner)).json()
    assert owner_view[0]["item_count"] == 1 and owner_view[0]["member_count"] == 1
    assert [s["name"] for s in (await client.get("/api/lists", headers=ayse)).json()] == ["Ev"]
    assert (await client.get(f"/api/lists/{lid}/optimize", headers=ayse)).status_code == 200

    # Üye listeyi silemez, ayrılabilir
    assert (await client.delete(f"/api/lists/{lid}", headers=ayse)).status_code == 403
    ayse_id = r.json()["members"][0]["user_id"]
    owner_id = r.json()["owner_id"]
    assert (await client.delete(f"/api/lists/{lid}/members/{owner_id}", headers=ayse)).status_code == 403
    assert (await client.delete(f"/api/lists/{lid}/members/{ayse_id}", headers=ayse)).status_code == 204
    assert (await client.get(f"/api/lists/{lid}", headers=ayse)).status_code == 404
    assert (await client.get(f"/api/lists/{lid}", headers=owner)).json()["members"] == []


# --- Fiyat alarmı ---------------------------------------------------------------------------


async def test_price_alert_triggers_on_drop(client, auth_headers, db, milk):
    group_id, ids = milk
    h = auth_headers
    r = await client.post("/api/alerts", json={"group_id": group_id}, headers=h)
    assert r.status_code == 201
    alert = r.json()[0]
    assert D(alert["baseline_price"]) == D("40.00") and not alert["triggered"]
    assert (await client.get("/api/alerts/unread", headers=h)).json() == {"unread": 0}

    await _set_price(db, ids["a101"], "38.50")
    alert = (await client.get("/api/alerts", headers=h)).json()[0]
    assert alert["triggered"] and alert["unread"]
    assert D(alert["current_price"]) == D("38.50")
    assert (await client.get("/api/alerts/unread", headers=h)).json() == {"unread": 1}

    assert (await client.post("/api/alerts/seen", headers=h)).status_code == 204
    alert = (await client.get("/api/alerts", headers=h)).json()[0]
    assert alert["triggered"] and not alert["unread"]

    # Fiyat geri yükselir, sonra yeniden düşer: yeniden bildirir
    await _set_price(db, ids["a101"], "45.00")
    assert not (await client.get("/api/alerts", headers=h)).json()[0]["triggered"]
    await _set_price(db, ids["a101"], "39.00")
    assert (await client.get("/api/alerts/unread", headers=h)).json() == {"unread": 1}

    # Hedef fiyat: 35 TL'nin altı
    r = await client.post("/api/alerts", json={"group_id": group_id, "target_price": "35"}, headers=h)
    assert len(r.json()) == 1 and not r.json()[0]["triggered"]
    assert (await client.delete(f"/api/alerts/{r.json()[0]['id']}", headers=h)).status_code == 204
    assert (await client.get("/api/alerts", headers=h)).json() == []
    assert (await client.post("/api/alerts", json={"group_id": 99999}, headers=h)).status_code == 404


async def test_price_alert_follows_chosen_product(client, auth_headers, db, milk):
    # Kemal: daha pahalı ama tam istenen marka (A101 Pınar 42.00) takip edilebilmeli
    group_id, ids = milk
    h = auth_headers
    r = await client.post("/api/alerts", json={"group_id": group_id, "product_id": ids["a101"]}, headers=h)
    alert = r.json()[0]
    assert alert["product_id"] == ids["a101"] and alert["brand"] == "Pınar"
    assert D(alert["baseline_price"]) == D("42.00") and D(alert["current_price"]) == D("42.00")

    await _set_price(db, ids["bim"], "30.00")  # başka markanın düşüşü tetiklemez
    alert = (await client.get("/api/alerts", headers=h)).json()[0]
    assert not alert["triggered"] and D(alert["current_price"]) == D("42.00")
    await _set_price(db, ids["a101"], "41.00")
    alert = (await client.get("/api/alerts", headers=h)).json()[0]
    assert alert["triggered"] and D(alert["current_price"]) == D("41.00")

    r = await client.post("/api/alerts", json={"group_id": group_id, "product_id": 99999}, headers=h)
    assert r.status_code == 422


# --- Fırsatlar ------------------------------------------------------------------------------


async def test_deals(client, db, milk):
    group_id, ids = milk
    assert (await client.get("/api/products/deals")).json() == []

    await _set_price(db, ids["bim"], "39.00")  # %2.5: fırsat sayılmaz
    assert (await client.get("/api/products/deals")).json() == []

    await _set_price(db, ids["a101"], "33.60")  # 42 -> 33.60: %20
    deals = (await client.get("/api/products/deals")).json()
    assert len(deals) == 1
    assert deals[0]["group_id"] == group_id and deals[0]["product_id"] == ids["a101"]
    assert D(deals[0]["previous_price"]) == D("42.00") and deals[0]["discount_percent"] == 20

    # 30 günden eski yüksek fiyat sayılmaz
    old = datetime.now(timezone.utc) - timedelta(days=40)
    await db.execute(update(PriceHistory).where(PriceHistory.product_id == ids["a101"]).values(recorded_at=old))
    await db.commit()
    assert (await client.get("/api/products/deals")).json() == []


# --- Barkod ---------------------------------------------------------------------------------


@pytest.fixture
def fake():
    fake = FakeMarketFiyati()

    async def _client():
        async with fake.client() as c:
            yield c

    app.dependency_overrides[get_barcode_client] = _client
    yield fake


async def test_barcode_lookup(client, db, milk, fake):
    group_id, ids = milk
    assert (await client.get("/api/products/barcode/abc")).status_code == 422

    # Ürün id'si barkodsa veritabanından bulunur, kaynağa gidilmez
    await db.execute(update(Product).where(Product.id == ids["bim"]).values(external_id="8690000000123"))
    await db.commit()
    assert (await client.get("/api/products/barcode/8690000000123")).json()["group_id"] == group_id
    assert fake.requests == []

    assert (await client.get("/api/products/barcode/86900001")).status_code == 404
    assert [json.loads(r.content)["identityType"] for r in fake.requests] == ["barcode"]

    fake.identity = {"numberOfFound": 1, "content": [load("marketfiyati_search_sut.json")["content"][0]]}
    r = await client.get("/api/products/barcode/8690504000017", params={"lat": 40.98, "lon": 29.02})
    assert r.status_code == 200
    found = r.json()["group_id"]
    body = json.loads(fake.requests[-1].content)
    assert body["identity"] == "8690504000017" and body["latitude"] == 40.98

    # İkinci okutma veritabanından
    before = len(fake.requests)
    assert (await client.get("/api/products/barcode/8690504000017")).json()["group_id"] == found
    assert len(fake.requests) == before

    fake.fail_with = 503
    assert (await client.get("/api/products/barcode/8690504000099")).status_code == 503
