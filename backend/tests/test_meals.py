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
        # Malzeme sanılmaması gereken, daha ucuz ürünler (Kemal'in gördüğü hata)
        "sabun": await group("Zeytinyağlı Sıvı Sabun 1 L", Unit.ML, 1000, [("bim", "45.00")]),
        "popkek": await group("Limonlu Popkek 45 g", Unit.G, 45, [("bim", "8.00")]),
        "salca_domates": await group("Domates Salçalı Sos 500 g", Unit.G, 500, [("bim", "15.00")]),
        "icetea": await group("Ice Tea Limon 1 Lt", Unit.ML, 1000, [("sok", "30.00")]),
    }
    await db.commit()
    return markets, ids


async def _recipes(client, **params):
    return {r["slug"]: r for r in (await client.get("/api/recipes", params=params)).json()}


async def _set_recipe(client, headers, plan, index, slug):
    recipe = (await _recipes(client))[slug]
    entry = plan["entries"][index]
    r = await client.patch(
        f"/api/meal-plans/{plan['id']}/entries/{entry['id']}", headers=headers, json={"recipe_id": recipe["id"]}
    )
    assert r.status_code == 200, r.text
    return r.json()


async def _with_mains(client, headers, plan, slugs):
    """Testin bildiği malzemelerle hesap yapabilmek için ilk öğünlerin ana yemeğini sabitle."""
    mains = [i for i, e in enumerate(plan["entries"]) if e["course"] == "ana"]
    for index, slug in zip(mains, slugs):
        plan = await _set_recipe(client, headers, plan, index, slug)
    return plan


async def test_cuisines_and_seeded_recipes(client):
    cuisines = (await client.get("/api/cuisines")).json()
    assert cuisines == [
        {"slug": "anadolu", "name": "Anadolu (Türk) Mutfağı", "icon": "🇹🇷", "is_default": True, "recipe_count": 42}
    ]
    recipes = await _recipes(client)
    assert {"mercimek-corbasi", "kuru-fasulye", "karniyarik", "menemen", "tavuk-sote", "izmir-kofte", "manti"} <= set(recipes)
    assert set(await _recipes(client, slot="kahvalti")) == {
        "menemen", "portakal-suyu", "sucuklu-yumurta", "kahvalti-tabagi", "cay",
    }
    assert set(await _recipes(client, course="corba")) == {
        "mercimek-corbasi", "ezogelin-corbasi", "yayla-corbasi", "domates-corbasi", "tarhana-corbasi", "tavuk-corbasi",
    }
    assert set(await _recipes(client, course="yan")) == {"pirinc-pilavi", "bulgur-pilavi", "patates-puresi", "tereyagli-makarna"}
    assert set(await _recipes(client, course="ara")) == {"meyve-tabagi", "cevizli-yogurt"}
    assert len(await _recipes(client, course="salata")) == 4 and len(await _recipes(client, course="tatli")) == 5
    assert len(await _recipes(client, course="ana")) == 16
    assert recipes["salgam"]["pairs_with"] == ["kuru-fasulye", "karniyarik", "etli-nohut", "mercimek-koftesi", "izmir-kofte"]
    # En sevilenler önce
    scores = [r["like_count"] for r in recipes.values()]
    assert list(recipes)[0] == "cay" and scores == [0] * len(scores)
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
        json={"period": "weekly", "servings": 2, "meal_slots": ["aksam", "ogle"], "courses": ["ana"], "start_date": "2026-11-02"},
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
    # Yalnız ana yemek istendi (yan yemek de yok); 14 öğünde aynı yemek en fazla 2 kez
    assert {e["course"] for e in entries} == {"ana"}
    counts = Counter(e["recipe"]["slug"] for e in entries)
    assert max(counts.values()) <= 2 and len(counts) >= 7

    cost = plan["cost"]
    assert cost["portions"] == 28
    plan = await _with_mains(client, auth_headers, plan, ["kuru-fasulye", "tavuk-sote", "karniyarik", "kuru-fasulye"])
    cost = plan["cost"]
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
        "/api/meal-plans", headers=auth_headers, json={"period": "daily", "servings": 4, "meal_slots": ["kahvalti"], "courses": ["ana"]}
    )).json()
    assert plan["days"] == 1 and plan["start_date"] == date.today().isoformat()
    assert [e["recipe"]["slug"] for e in plan["entries"]] in (["menemen"], ["sucuklu-yumurta"], ["kahvalti-tabagi"])
    plan = await _set_recipe(client, auth_headers, plan, 0, "menemen")
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
        "/api/meal-plans", headers=auth_headers, json={"period": "daily", "meal_slots": ["aksam"], "courses": ["ana"]}
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
        json={"period": "daily", "servings": 2, "meal_slots": ["kahvalti"], "courses": ["ana"], "name": "Pazar kahvaltısı"},
    )).json()
    plan = await _set_recipe(client, auth_headers, plan, 0, "menemen")

    r = await client.post(f"/api/meal-plans/{plan['id']}/to-list", headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    out = r.json()
    lst = out["list"]
    assert lst["name"] == "Pazar kahvaltısı"
    by_group = {i["group_id"]: i for i in lst["items"]}
    # Daha ucuz "Zeytinyağlı Sıvı Sabun" ve "Domates Salçalı Sos" değil, gerçek malzemeler
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
            self.score = 50

    recipes = [R(1), R(2), R(3)]
    rng = random.Random(1)
    # Bugün yenen ve dün yenen yemekler en sona kalır
    assert _choose(recipes, Counter(), {1}, {2}, rng).id == 3
    # Hepsi bugün yendiyse en az kullanılan
    assert _choose(recipes, Counter({1: 3, 2: 1, 3: 2}), {1, 2, 3}, set(), rng).id == 2
    assert _choose(recipes, Counter(), set(), set(), rng, exclude=3).id in {1, 2}


async def test_full_menu_with_courses_and_drink_pairing(client, auth_headers, kitchen):
    recipes = await _recipes(client)
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers,
        json={"period": "weekly", "servings": 2, "meal_slots": ["kahvalti", "ogle", "ara", "aksam"]},
    )).json()
    assert plan["courses"] == ["corba", "ana", "yan", "salata", "tatli", "icecek"]
    assert plan["entry_count"] == 28  # 7 gün x 4 öğün
    for day in range(7):
        meals = {}
        for e in plan["entries"]:
            if e["day_index"] == day:
                meals.setdefault(e["slot"], []).append(e)
        assert list(meals) == ["kahvalti", "ogle", "ara", "aksam"]
        assert [e["course"] for e in meals["kahvalti"]] == ["ana", "icecek"]
        assert [e["course"] for e in meals["ara"]] == ["ara"]
        for slot in ("ogle", "aksam"):
            courses = [e["course"] for e in meals[slot]]
            main = meals[slot][1]["recipe"]
            sides = [r for r in recipes.values() if r["course_type"] == "yan" and main["slug"] in r["pairs_with"]]
            # Pilav, püre gibi yan yemek yalnız uyan ana yemeğin yanında (İzmir köfte, mantı yanına yok)
            expected = ["corba", "ana"] + (["yan"] if sides else []) + ["salata", "tatli", "icecek"]
            assert courses == expected
            if sides:
                assert main["slug"] in meals[slot][2]["recipe"]["pairs_with"]
            drink = meals[slot][-1]["recipe"]
            assert drink["course_type"] == "icecek"
            assert not drink["pairs_with"] or main["slug"] in drink["pairs_with"]
        # Öğle ve akşam aynı çorba/ana yemek gelmez
        for i in (0, 1):
            assert meals["ogle"][i]["recipe"]["id"] != meals["aksam"][i]["recipe"]["id"]
    assert plan["cost"]["portions"] == 28 * 2
    assert "salgam" in recipes


async def test_remove_and_add_back_course(client, auth_headers, kitchen):
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers,
        json={"period": "daily", "meal_slots": ["aksam"], "courses": ["corba", "ana", "salata", "tatli", "icecek"]},
    )).json()
    soup = next(e for e in plan["entries"] if e["course"] == "corba")
    before = D(plan["cost"]["used_total"])

    r = await client.delete(f"/api/meal-plans/{plan['id']}/entries/{soup['id']}", headers=auth_headers)
    assert r.status_code == 200
    after = r.json()
    assert [e["course"] for e in after["entries"]] == ["ana", "salata", "tatli", "icecek"]
    assert D(after["cost"]["used_total"]) < before
    assert after["entry_count"] == 1 and after["cost"]["portions"] == 2  # hâlâ tek öğün

    added = await client.post(
        f"/api/meal-plans/{plan['id']}/entries", headers=auth_headers,
        json={"day_index": 0, "slot": "aksam", "course": "corba"},
    )
    assert added.status_code == 201
    assert [e["course"] for e in added.json()["entries"]] == ["corba", "ana", "salata", "tatli", "icecek"]
    # Aynı türden ikinci yemek eklenmez; kahvaltıya çorba eklenmez; plan dışı gün olmaz
    url = f"/api/meal-plans/{plan['id']}/entries"
    assert (await client.post(url, headers=auth_headers, json={"day_index": 0, "slot": "aksam", "course": "corba"})).status_code == 409
    assert (await client.post(url, headers=auth_headers, json={"day_index": 0, "slot": "kahvalti", "course": "corba"})).status_code == 422
    assert (await client.post(url, headers=auth_headers, json={"day_index": 3, "slot": "aksam", "course": "ana"})).status_code == 422
    # Yeni bir öğün (ara öğün) de eklenebilir
    snack = await client.post(url, headers=auth_headers, json={"day_index": 0, "slot": "ara", "course": "ara"})
    assert snack.status_code == 201 and snack.json()["entry_count"] == 2


async def test_plan_without_soup_and_drink_follows_main(client, auth_headers, kitchen):
    recipes = await _recipes(client)
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers,
        json={"period": "daily", "meal_slots": ["aksam"], "courses": ["ana", "icecek"]},
    )).json()
    assert [e["course"] for e in plan["entries"]] == ["ana", "icecek"]
    main = plan["entries"][0]
    # Ana yemek tavuk sote olursa şalgam (yalnız fasulye/karnıyarık) uyumsuz kalır, içecek değişir
    await client.patch(
        f"/api/meal-plans/{plan['id']}/entries/{plan['entries'][1]['id']}", headers=auth_headers,
        json={"recipe_id": recipes["salgam"]["id"]},
    )
    changed = (await client.patch(
        f"/api/meal-plans/{plan['id']}/entries/{main['id']}", headers=auth_headers,
        json={"recipe_id": recipes["tavuk-sote"]["id"]},
    )).json()
    drink = changed["entries"][1]["recipe"]
    assert drink["slug"] != "salgam" and "tavuk-sote" in drink["pairs_with"]


async def test_ingredients_do_not_match_soap_or_cake(client, kitchen):
    """Kemal'in bulduğu hata: zeytinyağı için sıvı sabun, limon için limonlu popkek listeye giriyordu."""
    _, ids = kitchen
    recipes = await _recipes(client)
    salad = (await client.get(f"/api/recipes/{recipes['coban-salatasi']['id']}")).json()["cost"]
    lines = {line["name"]: line for line in salad["lines"]}
    assert lines["Zeytinyağı"]["match"]["group_id"] == ids["zeytinyagi"]
    assert lines["Limon"]["match"]["group_id"] == ids["limon"]
    assert lines["Domates"]["match"]["group_id"] == ids["domates"]
    matched = {line["match"]["group_id"] for line in salad["lines"] if line["match"]}
    assert not matched & {ids["sabun"], ids["popkek"], ids["salca_domates"], ids["icetea"]}


async def test_ingredient_category_gate(client, db, kitchen):
    """Kemal'in ikinci bulduğu: revanideki limon için "Ice Tea Limon". Ürünün kategorisi biliniyorsa
    malzemenin kategorisinde olmalı (limon: Meyve & Sebze)."""
    from app.models import Category, ProductGroup

    _, ids = kitchen
    cats = {c.slug: c.id for c in (await db.scalars(select(Category))).all()}
    # Kelime kuralını aşan, kategorisi İçecek olan bir ürün: yalnız kategori kuralı eler
    tricky = ProductGroup(
        name="Limon 1 L Şişe", normalized_name=normalize_name("Limon 1 L Şişe"), unit=Unit.G, quantity=1000,
        category_id=cats["icecek"],
    )
    db.add(tricky)
    await db.flush()
    markets = {m.slug: m.id for m in (await db.scalars(select(Market))).all()}
    p = Product(market_id=markets["bim"], external_id="tricky", name=tricky.name, normalized_name=tricky.normalized_name,
                current_price=D("5.00"))
    db.add(p)
    await db.flush()
    db.add(GroupMember(group_id=tricky.id, product_id=p.id))
    limon = await db.get(ProductGroup, ids["limon"])
    limon.category_id = cats["meyve-sebze"]
    await db.commit()

    recipes = await _recipes(client)
    revani = (await client.get(f"/api/recipes/{recipes['revani']['id']}")).json()["cost"]
    line = next(line for line in revani["lines"] if line["name"] == "Limon")
    assert line["match"]["group_id"] == ids["limon"]


async def test_side_dish_follows_main(client, auth_headers, kitchen):
    """Kuru fasulyenin yanına pilav önerilir; mantının yanına yan yemek olmaz; ana yemek değişince
    yan yemek de uyar."""
    recipes = await _recipes(client)
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers,
        json={"period": "daily", "meal_slots": ["aksam"], "courses": ["ana", "yan"]},
    )).json()
    main = plan["entries"][0]
    url = f"/api/meal-plans/{plan['id']}/entries/{main['id']}"

    plan = (await client.patch(url, headers=auth_headers, json={"recipe_id": recipes["kuru-fasulye"]["id"]})).json()
    assert [e["course"] for e in plan["entries"]] == ["ana", "yan"]
    side = plan["entries"][1]["recipe"]
    assert side["slug"] in {"pirinc-pilavi", "bulgur-pilavi"} and "kuru-fasulye" in side["pairs_with"]

    plan = (await client.patch(url, headers=auth_headers, json={"recipe_id": recipes["manti"]["id"]})).json()
    assert [e["course"] for e in plan["entries"]] == ["ana"]  # mantının yanına pilav yok
    r = await client.post(
        f"/api/meal-plans/{plan['id']}/entries", headers=auth_headers, json={"day_index": 0, "slot": "aksam", "course": "yan"}
    )
    assert r.status_code == 422 and "yan" in r.json()["detail"]

    plan = (await client.patch(url, headers=auth_headers, json={"recipe_id": recipes["tavuk-sote"]["id"]})).json()
    assert [e["course"] for e in plan["entries"]] == ["ana", "yan"]  # menüde yan yemek var: geri gelir
    side_entry = plan["entries"][1]
    assert "tavuk-sote" in side_entry["recipe"]["pairs_with"]
    # "Başka öner" de yalnız tavuk soteye uyan yan yemeklerden seçer
    other = (await client.patch(
        f"/api/meal-plans/{plan['id']}/entries/{side_entry['id']}", headers=auth_headers, json={}
    )).json()["entries"][1]["recipe"]
    assert other["id"] != side_entry["recipe"]["id"] and "tavuk-sote" in other["pairs_with"]


async def test_diet_and_allergen_filters(client, auth_headers, kitchen):
    vegan = await _recipes(client, diet="vegan")
    assert vegan and all("vegan" in r["diets"] for r in vegan.values())
    assert {"imam-bayildi", "taze-fasulye", "mercimek-koftesi", "coban-salatasi"} <= set(vegan)
    assert "ayran" not in vegan and "menemen" not in vegan
    no_gluten_milk = await _recipes(client, avoid=["gluten", "sut"])
    assert all(not {"gluten", "sut"} & set(r["allergens"]) for r in no_gluten_milk.values())
    assert "mercimek-corbasi" not in no_gluten_milk and "karniyarik" in no_gluten_milk
    assert "glutensiz" in (await _recipes(client))["muhallebi"]["diets"]
    assert (await client.get("/api/recipes", params={"diet": "keto"})).status_code == 422

    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers,
        json={"period": "weekly", "meal_slots": ["ogle", "aksam"], "diets": ["vegan"], "avoid_allergens": ["gluten"]},
    )).json()
    assert plan["diets"] == ["vegan"] and plan["avoid_allergens"] == ["gluten"]
    assert plan["entries"]
    for e in plan["entries"]:
        assert "vegan" in e["recipe"]["diets"] and "gluten" not in e["recipe"]["allergens"], e["recipe"]["slug"]
    # "Başka öner" de diyete uyar
    entry = plan["entries"][0]
    changed = (await client.patch(
        f"/api/meal-plans/{plan['id']}/entries/{entry['id']}", headers=auth_headers, json={}
    )).json()
    new = next(e for e in changed["entries"] if e["id"] == entry["id"])["recipe"]
    assert "vegan" in new["diets"] and "gluten" not in new["allergens"]

    # Vegan kahvaltılık yok: anlaşılır hata
    r = await client.post(
        "/api/meal-plans", headers=auth_headers, json={"meal_slots": ["kahvalti"], "courses": ["ana"], "diets": ["vegan"]}
    )
    assert r.status_code == 422 and "diyet" in r.json()["detail"]


async def test_nutrition(client, auth_headers):
    recipes = await _recipes(client)
    assert recipes["mercimek-corbasi"]["nutrition"] == {"kcal": 290, "protein_g": 14, "carbs_g": 42, "fat_g": 7}
    assert all(r["nutrition"] is not None for r in recipes.values())
    plan = (await client.post(
        "/api/meal-plans", headers=auth_headers, json={"period": "weekly", "meal_slots": ["aksam"], "courses": ["ana"]}
    )).json()
    total = sum(e["recipe"]["nutrition"]["kcal"] for e in plan["entries"])
    assert plan["daily_nutrition"]["kcal"] == round(total / 7)


async def test_likes_rank_recipes(client, auth_headers):
    recipes = await _recipes(client)
    kisir = recipes["kisir"]
    url = f"/api/recipes/{kisir['id']}/like"
    assert (await client.put(url)).status_code == 401
    assert (await client.put(url, headers=auth_headers)).status_code == 204
    assert (await client.put(url, headers=auth_headers)).status_code == 204  # ikinci kez sayılmaz
    other = await client.post("/api/auth/register", json={"email": "ayse@example.com", "password": "gizli-sifre-123"})
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    await client.put(url, headers=other_headers)

    mine = {r["slug"]: r for r in (await client.get("/api/recipes", headers=auth_headers)).json()}
    assert mine["kisir"]["like_count"] == 2 and mine["kisir"]["liked"] is True
    assert mine["piyaz"]["liked"] is False
    order = list(mine)
    assert order.index("kisir") < order.index("coban-salatasi")  # 87 + 2x3 > 88
    detail = (await client.get(f"/api/recipes/{kisir['id']}", headers=auth_headers)).json()
    assert detail["liked"] is True

    assert (await client.delete(url, headers=auth_headers)).status_code == 204
    assert (await client.delete(url, headers=auth_headers)).status_code == 204
    after = (await _recipes(client))["kisir"]
    assert after["like_count"] == 1 and after["liked"] is False
