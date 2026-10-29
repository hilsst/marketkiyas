from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.api.routes.stores import get_marketfiyati_client, get_store_sync
from app.main import app
from app.models import Store
from app.services.marketfiyati.ingest import sync_area
from tests.marketfiyati_fake import FakeMarketFiyati

MODA = {"lat": 40.987, "lon": 29.027}


@pytest.fixture
def fake():
    return FakeMarketFiyati()


@pytest.fixture
def synced_stores():
    return []


@pytest.fixture(autouse=True)
def overrides(fake, synced_stores):
    async def _client():
        async with fake.client() as c:
            yield c

    async def _sync(store_ids):
        synced_stores.append(store_ids)

    app.dependency_overrides[get_marketfiyati_client] = _client
    app.dependency_overrides[get_store_sync] = lambda: _sync
    yield


async def test_nearby_stores_and_selection(client, auth_headers, synced_stores):
    r = await client.get("/api/stores/nearby", params=MODA, headers=auth_headers)
    assert r.status_code == 200
    stores = r.json()
    # 'Uzak Şube' 5 km dışında
    assert [s["name"] for s in stores] == ["Moda Şubesi", "Bahariye"]
    assert stores[0]["market_slug"] == "bim" and stores[0]["distance_km"] < 1
    assert not any(s["selected"] for s in stores)

    ids = [s["id"] for s in stores]
    r = await client.put("/api/me/stores", json={"store_ids": ids}, headers=auth_headers)
    assert {s["id"] for s in r.json()} == set(ids)
    assert synced_stores == [sorted(ids)]  # yeni şubeler arka planda senkronize edilir

    # Aynı seçim tekrar: yeni şube yok, senkronizasyon tetiklenmez
    await client.put("/api/me/stores", json={"store_ids": ids[:1]}, headers=auth_headers)
    assert len(synced_stores) == 1
    mine = (await client.get("/api/me/stores", headers=auth_headers)).json()
    assert [s["id"] for s in mine] == ids[:1]

    nearby = (await client.get("/api/stores/nearby", params=MODA, headers=auth_headers)).json()
    assert [s["selected"] for s in nearby] == [True, False]


async def test_nearby_falls_back_to_saved_stores_when_source_down(client, auth_headers, fake):
    await client.get("/api/stores/nearby", params=MODA, headers=auth_headers)
    fake.fail_with = 400
    r = await client.get("/api/stores/nearby", params=MODA, headers=auth_headers)
    assert r.status_code == 200
    assert {s["name"] for s in r.json()} == {"Moda Şubesi", "Bahariye"}


async def test_select_unknown_store(client, auth_headers):
    r = await client.put("/api/me/stores", json={"store_ids": [999]}, headers=auth_headers)
    assert r.status_code == 404


async def test_prices_follow_selected_stores(client, auth_headers, db, fake):
    async with fake.client() as c:
        await sync_area(db, c, latitude=40.987, longitude=29.027, distance_km=5, keywords=["süt"])
    group = (await client.get("/api/products", params={"q": "süt 1 l"})).json()[0]
    assert group["name"] == "Süt 1 L"
    assert D(group["min_price"]) == D("32.75")  # şube seçilmemiş: tüm şubeler

    # Kullanıcı sadece A101 Kadıköy Rıhtım'ı seçer
    rihtim = await db.scalar(select(Store.id).where(Store.external_id == "a101-7790"))
    await client.put("/api/me/stores", json={"store_ids": [rihtim]}, headers=auth_headers)

    group = (await client.get("/api/products", params={"q": "süt 1 l"}, headers=auth_headers)).json()[0]
    assert D(group["min_price"]) == D("35.25")
    assert group["brands"] == ["Pınar"]  # Sütaş bu şubede yok
    # Laktozsuz süt seçili şubede satılmıyor -> listelenmez
    names = [g["name"] for g in (await client.get("/api/products", params={"q": "süt"}, headers=auth_headers)).json()]
    assert "Laktozsuz Süt 1 L" not in names

    # Ürün detayı şube adını ve seçili şubelerdeki fiyatları gösterir
    detail = (await client.get(f"/api/products/{group['id']}", headers=auth_headers)).json()
    pinar = next(p for p in detail["products"] if p["price"] is not None)
    assert pinar["store_name"] == "Kadıköy Rıhtım"
    assert [{k: v for k, v in sp.items() if k != "updated_at"} for sp in pinar["store_prices"]] == [
        {"store_id": rihtim, "store_name": "Kadıköy Rıhtım", "price": "35.25"}
    ]
    assert pinar["store_prices"][0]["updated_at"]

    # Optimizasyon da seçili şubeyi kullanır ve şubeyi atar
    lid = (await client.post("/api/lists", json={"name": "L"}, headers=auth_headers)).json()["id"]
    await client.post(f"/api/lists/{lid}/items", json={"group_id": group["id"]}, headers=auth_headers)
    opt = (await client.get(f"/api/lists/{lid}/optimize", headers=auth_headers)).json()
    line = opt["opportunist"]["lines"][0]
    assert D(line["unit_price"]) == D("35.25") and line["store_id"] == rihtim
    assert [m["market_id"] for m in opt["single_market"]["markets"]] == [line["market_id"]]  # sadece A101

    detail = (await client.post(f"/api/lists/{lid}/apply", json={"plan_type": "opportunist"}, headers=auth_headers)).json()
    assert detail["items"][0]["assigned"]["store_name"] == "Kadıköy Rıhtım"
