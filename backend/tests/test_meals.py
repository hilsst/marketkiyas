import random
from collections import Counter
from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.models import GroupMember, Market, Product, ProductGroup, Unit
from app.services.normalize import normalize_name


@pytest.fixture
async def kitchen(db):
    """Yemeklerin malzemelerinden bir kısmı katalogda; tavuk göğsü yok (eksik malzeme)."""
    markets = {m.slug: m.id for m in (await db.scalars(select(Market))).all()}

    async def group(name, unit, qty, products):
        g = ProductGroup(name=name, normalized_name=normalize_name(name), unit=unit, quantity=qty)
        db.add(g)
        await db.flush()
        for i, (market, price) in enumerate(products):
            p = Product(
                market_id=markets[market], external_id=f"m{g.id}-{i}", name=name,
                normalized_name=normalize_name(name), current_price=D(price),
            )
            db.add(p)
            await db.flush()
            db.add(GroupMember(group_id=g.id, product_id=p.id))
        return g.id

    ids = {
        "mercimek": await group("Kırmızı Mercimek 1 kg", Unit.G, 1000, [("bim", "60.00"), ("a101", "65.00")]),
        "mercimek_small": await group("Kırmızı Mercimek 500 g", Unit.G, 500, [("sok", "40.00")]),
        "sogan": await group("Kuru Soğan 1 kg", Unit.G, 1000, [("bim", "20.00")]),
        "havuc": await group("Havuç 1 kg", Unit.G, 1000, [("a101", "25.00")]),
        "patates": await group("Patates 1 kg", Unit.G, 1000, [("bim", "18.00")]),
        "tereyagi": await group("Tereyağı 250 g", Unit.G, 250, [("sok", "120.00")]),
        "un": await group("Buğday Unu 1 kg", Unit.G, 1000, [("bim", "30.00")]),
        "limon": await group("Limon 1 kg", Unit.G, 1000, [("bim", "40.00")]),
        "domates": await group("Domates 1 kg", Unit.G, 1000, [("bim", "35.00")]),
        "salca": await group("Domates Salçası 830 g", Unit.G, 830, [("a101", "70.00")]),
        "biber": await group("Sivri Biber 500 g", Unit.G, 500, [("sok", "30.00")]),
        "yumurta": await group("Yumurta 15'li", Unit.PIECE, 15, [("bim", "75.00")]),
        "zeytinyagi": await group("Zeytinyağı 1 L", Unit.ML, 1000, [("a101", "300.00")]),
        "tuz": await group("Sofra Tuzu 750 g", Unit.G, 750, [("bim", "12.00")]),
        # "pul biber" araması bununla eşleşmemeli; tavuk göğsü "Piliç Göğüs" adıyla da bulunur
        "pilic": await group("Piliç Göğüs Fileto 1 kg", Unit.G, 1000, [("a101", "220.00")]),
    }
    await db.commit()
    return markets, ids


async def _recipes(client, **params):
    return {r["slug"]: r for r in (await client.get("/api/recipes", params=params)).json()}


async def test_cuisines_and_seeded_recipes(client):
    cuisines = (await client.get("/api/cuisines")).json()
    assert cuisines == [
        {"slug": "anadolu", "name": "Anadolu (Türk) Mutfağı", "icon": "🇹🇷", "is_default": True, "recipe_count": 5}
    ]
    recipes = await _recipes(client)
    assert set(recipes) == {"mercimek-corbasi", "kuru-fasulye", "karniyarik", "menemen", "tavuk-sote"}
    assert set(await _recipes(client, slot="kahvalti")) == {"menemen"}
    assert "karniyarik" not in await _recipes(client, slot="ogle")
    assert await _recipes(client, cuisine="italyan") == {}


async def test_recipe_detail_cost_scales_with_servings(client, kitchen):
    _, ids = kitchen
    soup = (await _recipes(client))["mercimek-corbasi"]
    detail = (await client.get(f"/api/recipes/{soup['id']}")).json()
    assert detail["servings"] == 4 and len(detail["steps"]) >= 5
    assert {"Kırmızı mercimek", "Tuz"} <= {i["name"] for i in detail["ingredients"]}
    cost = detail["cost"]
    # Tuz ve pul biber evde var sayılır
    assert set(cost["pantry"]) == {"Tuz", "Pul biber"}
    lines = {line["name"]: line for line in cost["lines"]}
    # 200 g mercimek: 500 g paket (40 TL) 1 kg paketten (60 TL) ucuza karşılar
    assert lines["Kırmızı mercimek"]["match"]["group_id"] == ids["mercimek_small"]
    assert D(lines["Kırmızı mercimek"]["purchase_cost"]) == D("40.00")
    assert D(lines["Kırmızı mercimek"]["used_cost"]) == D("16.00")
    assert cost["missing_count"] == 0

    double = (await client.get(f"/api/recipes/{soup['id']}", params={"servings": 8})).json()["cost"]
    lines8 = {line["name"]: line for line in double["lines"]}
    assert D(lines8["Kırmızı mercimek"]["needed_quantity"]) == 400
    assert D(double["used_total"]) == 2 * D(cost["used_total"])


async def test_weekly_plan_spreads_dishes(client, auth_headers, kitchen):
    r = await client.post(
        "/api/meal-plans", headers=auth_headers,
        json={"period": "weekly", "servings": 2, "meal_slots": ["aksam", "ogle"], "start_date": "2026-11-02"},
    )
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["cuisine"] == "anadolu" and plan["days"] == 7
    assert plan["meal_slots"] == ["ogle", "aksam"]
    assert plan["name"] == "Haftalık yemek planı · 2 Kasım"
    entries = plan["entries"]
    assert len(entries) == 14
    assert entries[0]["date"] == "2026-11-02" and entries[-1]["date"] == "2026-11-08"
    for day in range(7):
        today = [e for e in entries if e["day_index"] == day]
        assert [e["slot"] for e in today] == ["ogle", "aksam"]
        assert len({e["recipe"]["id"] for e in today}) == 2  # aynı gün aynı yemek yok
    assert all(e["recipe"]["slug"] != "karniyarik" for e in entries if e["slot"] == "ogle")
    # 4 uygun yemek 14 öğüne dengeli dağılır
    counts = {}
    for e in entries:
        counts[e["recipe"]["slug"]] = counts.get(e["recipe"]["slug"], 0) + 1
    assert set(counts) == {"mercimek-corbasi", "kuru-fasulye", "karniyarik", "tavuk-sote"}
    assert max(counts.values()) - min(counts.values()) <= 2

    cost = plan["cost"]
    assert cost["portions"] == 28
    lines = {line["name"]: line for line in cost["lines"]}
    # Kuru fasulye katalogda yok; tavuk göğsü "Piliç Göğüs" olarak bulunur
    assert lines["Kuru fasulye"]["match"] is None and lines["Kuru fasulye"]["purchase_cost"] is None
    assert lines["Tavuk göğsü"]["match"]["name"] == "Piliç Göğüs Fileto 1 kg"
    assert cost["missing_count"] >= 2
    # Domates salçası değil, domates seçilir
    assert lines["Domates"]["match"]["name"] == "Domates 1 kg"
    assert D(cost["purchase_total"]) >= D(cost["used_total"]) > 0
    assert D(cost["per_serving"]) == (D(cost["used_total"]) / 28).quantize(D("0.01"))

    summaries = (await client.get("/api/meal-plans", headers=auth_headers)).json()
    assert [s["id"] for s in summaries] == [plan["id"]]


async def test_daily_breakfast_plan_and_pantry(client, auth_headers, kitchen):
    _, ids = kitchen
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers, json={"period": "daily", "servings": 4, "meal_slots": ["kahvalti"]}
    )).json()
    assert plan["days"] == 1 and plan["start_date"] == date.today().isoformat()
    assert [e["recipe"]["slug"] for e in plan["entries"]] == ["menemen"]
    lines = {line["name"]: line for line in plan["cost"]["lines"]}
    # 4 kişilik menemen: 8 yumurta -> 15'li 1 koli; 900 g domates -> 1 kg
    assert D(lines["Yumurta"]["needed_quantity"]) == 8 and lines["Yumurta"]["packages"] == 1
    assert lines["Domates"]["packages"] == 1
    assert "Tuz" not in lines

    with_pantry = (await client.get(
        f"/api/meal-plans/{plan['id']}", headers=auth_headers, params={"include_pantry": True}
    )).json()["cost"]
    pantry_lines = {line["name"]: line for line in with_pantry["lines"]}
    assert pantry_lines["Tuz"]["match"]["group_id"] == ids["tuz"]
    assert with_pantry["pantry"] == []


async def test_unknown_cuisine_and_privacy(client, auth_headers):
    r = await client.post("/api/meal-plans", headers=auth_headers, json={"cuisine": "italyan"})
    assert r.status_code == 404
    plan = (await client.post("/api/meal-plans", headers=auth_headers, json={"period": "daily"})).json()

    other = await client.post("/api/auth/register", json={"email": "ayse@example.com", "password": "gizli-sifre-123"})
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get(f"/api/meal-plans/{plan['id']}", headers=other_headers)).status_code == 404
    assert (await client.get("/api/meal-plans")).status_code == 401


async def test_change_entry(client, auth_headers, kitchen):
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers, json={"period": "daily", "meal_slots": ["aksam"]}
    )).json()
    entry = plan["entries"][0]
    url = f"/api/meal-plans/{plan['id']}/entries/{entry['id']}"
    suggested = (await client.patch(url, headers=auth_headers, json={})).json()["entries"][0]
    assert suggested["recipe"]["id"] != entry["recipe"]["id"]
    assert "aksam" in suggested["recipe"]["meal_slots"]

    menemen = (await _recipes(client))["menemen"]
    chosen = (await client.patch(url, headers=auth_headers, json={"recipe_id": menemen["id"]})).json()
    assert chosen["entries"][0]["recipe"]["slug"] == "menemen"
    assert (await client.patch(url, headers=auth_headers, json={"recipe_id": 99999})).status_code == 404

    renamed = (await client.patch(
        f"/api/meal-plans/{plan['id']}", headers=auth_headers, json={"name": "Misafir akşamı", "servings": 6}
    )).json()
    assert renamed["name"] == "Misafir akşamı" and renamed["cost"]["portions"] == 6

    assert (await client.delete(f"/api/meal-plans/{plan['id']}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/meal-plans/{plan['id']}", headers=auth_headers)).status_code == 404


async def test_export_to_new_and_existing_list(client, auth_headers, kitchen):
    _, ids = kitchen
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers,
        json={"period": "daily", "servings": 2, "meal_slots": ["kahvalti"], "name": "Pazar kahvaltısı"},
    )).json()

    r = await client.post(f"/api/meal-plans/{plan['id']}/to-list", headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    out = r.json()
    lst = out["list"]
    assert lst["name"] == "Pazar kahvaltısı"
    by_group = {i["group_id"]: i for i in lst["items"]}
    assert set(by_group) == {ids["yumurta"], ids["domates"], ids["biber"], ids["zeytinyagi"]}
    assert out["added"] == 4 and out["skipped"] == []
    assert by_group[ids["yumurta"]]["note"] == "Yemek planı"
    assert (await client.get(f"/api/meal-plans/{plan['id']}", headers=auth_headers)).json()["exported_list_id"] == lst["id"]

    # Mevcut listeye: aynı ürün varsa miktarı artar, yeni kalem açılmaz
    existing = (await client.post("/api/lists", headers=auth_headers, json={"name": "Haftalık"})).json()
    await client.post(f"/api/lists/{existing['id']}/items", headers=auth_headers, json={"group_id": ids["yumurta"], "quantity": 2})
    out = (await client.post(
        f"/api/meal-plans/{plan['id']}/to-list", headers=auth_headers,
        json={"list_id": existing["id"], "include_pantry": True},
    )).json()
    items = {i["group_id"]: i for i in out["list"]["items"]}
    assert D(items[ids["yumurta"]]["quantity"]) == 3
    assert ids["tuz"] in items  # evdekiler de istendi
    assert out["skipped"] == ["Pul biber"]  # katalogda yok
    assert len(out["list"]["items"]) == 5

    other = await client.post("/api/auth/register", json={"email": "ayse@example.com", "password": "gizli-sifre-123"})
    other_list = (await client.post(
        "/api/lists", headers={"Authorization": f"Bearer {other.json()['access_token']}"}, json={"name": "X"}
    )).json()
    r = await client.post(
        f"/api/meal-plans/{plan['id']}/to-list", headers=auth_headers, json={"list_id": other_list["id"]}
    )
    assert r.status_code == 404


def test_generator_variety_unit():
    from app.services.meals import _choose

    class R:
        def __init__(self, i):
            self.id = i

    recipes = [R(1), R(2), R(3)]
    rng = random.Random(1)
    # Bugün yenen ve dün yenen yemekler en sona kalır
    assert _choose(recipes, Counter(), {1}, {2}, rng).id == 3
    # Hepsi bugün yendiyse en az kullanılan
    assert _choose(recipes, Counter({1: 3, 2: 1, 3: 2}), {1, 2, 3}, set(), rng).id == 2
    assert _choose(recipes, Counter(), set(), set(), rng, exclude=3).id in {1, 2}
