from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.models import GroupMember, Market, PriceHistory, Product, ProductGroup, Unit
from app.services.normalize import normalize_name
from app.services.optimizer import NO_COMPLETE_MARKET_WARNING


@pytest.fixture
async def catalog(db):
    markets = {m.slug: m.id for m in (await db.scalars(select(Market))).all()}

    async def group(name, products, unit=None, qty=None):
        g = ProductGroup(name=name, normalized_name=normalize_name(name), unit=unit, quantity=qty)
        db.add(g)
        await db.flush()
        for i, (market, brand, price) in enumerate(products):
            p = Product(
                market_id=markets[market],
                external_id=f"{g.id}-{i}",
                name=f"{brand or ''} {name}".strip(),
                normalized_name=normalize_name(f"{brand or ''} {name}"),
                brand=brand,
                current_price=D(price),
            )
            db.add(p)
            await db.flush()
            db.add(GroupMember(group_id=g.id, product_id=p.id))
            db.add(PriceHistory(product_id=p.id, price=D(price)))
        return g.id

    ids = {
        "milk": await group(
            "Süt 1 L",
            [("bim", "Sütaş", "32.50"), ("a101", "Pınar", "34.90"), ("sok", "Pınar", "33.00")],
            Unit.ML,
            1000,
        ),
        "bread": await group("Ekmek", [("bim", None, "10.00"), ("a101", None, "9.50"), ("sok", None, "10.50")]),
        "eggs": await group("Yumurta 30'lu", [("bim", "Köy", "80.00"), ("a101", "Köy", "85.00")]),
        "tea": await group("Çay 1 kg", [("sok", "Çaykur", "120.00")]),
    }
    await db.commit()
    return markets, ids


async def test_product_search(client, catalog):
    markets, ids = catalog
    r = await client.get("/api/products", params={"q": "süt"})
    assert r.status_code == 200
    body = r.json()
    assert body[0]["id"] == ids["milk"]
    assert body[0]["brands"] == ["Pınar", "Sütaş"]
    assert D(body[0]["min_price"]) == D("32.50")
    assert {p["market_id"] for p in body[0]["market_prices"]} == {markets["bim"], markets["a101"], markets["sok"]}

    detail = (await client.get(f"/api/products/{ids['milk']}")).json()
    assert len(detail["products"]) == 3
    assert len(detail["products"][0]["price_history"]) == 1
    assert (await client.get("/api/products/99999")).status_code == 404


async def test_full_shopping_flow(client, auth_headers, catalog):
    markets, ids = catalog
    h = auth_headers
    lst = (await client.post("/api/lists", json={"name": "Haftalık"}, headers=h)).json()
    lid = lst["id"]

    await client.post(f"/api/lists/{lid}/items", json={"group_id": ids["milk"], "quantity": 2}, headers=h)
    r = await client.post(f"/api/lists/{lid}/items", json={"group_id": ids["bread"]}, headers=h)
    milk_item = r.json()["items"][0]["id"]

    # Sağa kaydırıp Pınar'ı kilitle
    r = await client.patch(f"/api/lists/{lid}/items/{milk_item}", json={"preferred_brand": "pınar"}, headers=h)
    assert r.json()["items"][0]["preferred_brand"] == "Pınar"

    opt = (await client.get(f"/api/lists/{lid}/optimize", headers=h)).json()
    assert opt["single_market"]["available"] is True
    assert D(opt["combination"]["total"]) == D("75.50")
    assert D(opt["opportunist"]["total"]) == D("74.50")
    assert D(opt["savings"]["weekly"]) == D("1.00")
    assert D(opt["savings"]["yearly"]) == D("52.00")

    # Listeye Uygula -> market bazlı gruplama
    detail = (await client.post(f"/api/lists/{lid}/apply", json={"plan_type": "opportunist"}, headers=h)).json()
    assert detail["status"] == "shopping"
    groups = {g["market_id"]: g["item_ids"] for g in detail["shopping_groups"]}
    assert groups == {markets["bim"]: [milk_item], markets["a101"]: [detail["items"][1]["id"]]}

    # Alışveriş Modu: alındı işareti, sıra korunur
    r = await client.patch(f"/api/lists/{lid}/items/{milk_item}", json={"is_checked": True}, headers=h)
    items = r.json()["items"]
    assert items[0]["id"] == milk_item and items[0]["is_checked"] is True
    assert r.json()["status"] == "shopping"  # işaretlemek planı bozmaz

    done = (await client.post(f"/api/lists/{lid}/complete", json={}, headers=h)).json()
    assert D(done["saved_amount"]) == D("1.00")
    assert (await client.post(f"/api/lists/{lid}/complete", headers=h)).status_code == 409

    # Liste silinse de kasa kalır
    assert (await client.delete(f"/api/lists/{lid}", headers=h)).status_code == 204
    vault = (await client.get("/api/savings", headers=h)).json()
    assert D(vault["total_saved"]) == D("1.00")
    assert vault["records"][0]["list_id"] is None
    assert vault["records"][0]["list_name"] == "Haftalık"


async def test_non_opportunist_plan_adds_nothing_to_vault(client, auth_headers, catalog):
    _, ids = catalog
    h = auth_headers
    lid = (await client.post("/api/lists", json={"name": "L"}, headers=h)).json()["id"]
    r = await client.post(f"/api/lists/{lid}/items", json={"group_id": ids["milk"], "preferred_brand": "Pınar"}, headers=h)
    assert r.status_code == 201
    await client.post(f"/api/lists/{lid}/apply", json={"plan_type": "combination"}, headers=h)
    done = (await client.post(f"/api/lists/{lid}/complete", headers=h)).json()
    assert D(done["saved_amount"]) == 0
    assert (await client.get("/api/savings", headers=h)).json()["record_count"] == 0


async def test_single_market_unavailable_warning(client, auth_headers, catalog):
    _, ids = catalog
    h = auth_headers
    lid = (await client.post("/api/lists", json={"name": "L"}, headers=h)).json()["id"]
    for g in ("eggs", "tea"):  # yumurta Şok'ta yok, çay sadece Şok'ta
        await client.post(f"/api/lists/{lid}/items", json={"group_id": ids[g]}, headers=h)

    opt = (await client.get(f"/api/lists/{lid}/optimize", headers=h)).json()
    assert opt["single_market"]["available"] is False
    assert opt["single_market"]["warning"] == NO_COMPLETE_MARKET_WARNING

    r = await client.post(f"/api/lists/{lid}/apply", json={"plan_type": "single_market"}, headers=h)
    assert r.status_code == 409
    assert r.json()["detail"] == NO_COMPLETE_MARKET_WARNING


async def test_editing_items_resets_applied_plan(client, auth_headers, catalog):
    _, ids = catalog
    h = auth_headers
    lid = (await client.post("/api/lists", json={"name": "L"}, headers=h)).json()["id"]
    await client.post(f"/api/lists/{lid}/items", json={"group_id": ids["milk"]}, headers=h)
    await client.post(f"/api/lists/{lid}/apply", json={"plan_type": "opportunist"}, headers=h)
    r = await client.post(f"/api/lists/{lid}/items", json={"group_id": ids["bread"]}, headers=h)
    body = r.json()
    assert body["applied_plan"] is None and body["status"] == "active"
    assert body["shopping_groups"] == []
    assert all(i["assigned"] is None for i in body["items"])


async def test_validation_and_ownership(client, auth_headers, catalog):
    _, ids = catalog
    lid = (await client.post("/api/lists", json={"name": "L"}, headers=auth_headers)).json()["id"]
    r = await client.post(
        f"/api/lists/{lid}/items", json={"group_id": ids["milk"], "preferred_brand": "Torku"}, headers=auth_headers
    )
    assert r.status_code == 422
    r = await client.post(f"/api/lists/{lid}/items", json={"group_id": 99999}, headers=auth_headers)
    assert r.status_code == 404

    other = await client.post("/api/auth/register", json={"email": "baska@example.com", "password": "baska-sifre-1"})
    other_h = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get(f"/api/lists/{lid}", headers=other_h)).status_code == 404
    assert (await client.get("/api/lists", headers=other_h)).json() == []
    assert (await client.get("/api/lists")).status_code == 401
