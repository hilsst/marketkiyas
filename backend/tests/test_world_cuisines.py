"""Dünya mutfakları: birden çok mutfaktan haftalık plan ve malzemesi marketlerde olmayan tariflerin gizlenmesi."""

from collections import Counter
from decimal import Decimal as D

import pytest
from sqlalchemy import select, text

from app.models import GroupMember, Market, Product, ProductGroup, Unit
from app.services.meals import refresh_availability
from app.services.normalize import normalize_name


@pytest.fixture(autouse=True)
async def reset_availability(db):
    """Tarifler testler arasında silinmez; bulunabilirlik kontrolünün izini temizle."""
    yield
    await db.execute(text("UPDATE recipes SET missing_ingredients = NULL"))
    await db.commit()


async def _add_products(db, names):
    market = (await db.scalars(select(Market).where(Market.slug == "bim"))).one()
    for name, unit, qty, price in names:
        g = ProductGroup(name=name, normalized_name=normalize_name(name), unit=unit, quantity=qty)
        db.add(g)
        await db.flush()
        p = Product(
            market_id=market.id, external_id=f"w{g.id}", name=name, normalized_name=normalize_name(name),
            current_price=D(price),
        )
        db.add(p)
        await db.flush()
        db.add(GroupMember(group_id=g.id, product_id=p.id))
    await db.commit()


# Domatesli spagetti ve sarımsaklı ekmeğin bütün malzemeleri; kıyma, mozzarella, soya sosu yok
POMODORO = [
    ("Spagetti Makarna 500 g", Unit.G, 500, "25.00"),
    ("Domates 1 kg", Unit.G, 1000, "35.00"),
    ("Sarımsak 250 g", Unit.G, 250, "30.00"),
    ("Zeytinyağı 1 L", Unit.ML, 1000, "300.00"),
    ("Taze Fesleğen 20 g", Unit.G, 20, "15.00"),
]


def _meals(plan):
    meals: dict[tuple, list] = {}
    for e in plan["entries"]:
        meals.setdefault((e["day_index"], e["slot"]), []).append(e)
    return meals


async def test_weekly_plan_from_three_cuisines(client, auth_headers):
    r = await client.post("/api/meal-plans", headers=auth_headers, json={
        "period": "weekly", "cuisines": ["anadolu", "italyan", "uzakdogu"], "meal_slots": ["ogle", "aksam"],
    })
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["cuisines"] == ["anadolu", "italyan", "uzakdogu"] and plan["cuisine"] == "anadolu"
    meals = _meals(plan)
    assert len(meals) == 14

    meal_cuisines = Counter()
    for entries in meals.values():
        main = next(e for e in entries if e["course"] == "ana")
        cuisine = main["recipe"]["cuisine"]
        meal_cuisines[cuisine] += 1
        # Çorba, ana yemek, yan yemek ve salata öğünün mutfağından (spagettinin yanına mercimek çorbası gelmez)
        for e in entries:
            if e["course"] in ("corba", "ana", "yan", "salata"):
                assert e["recipe"]["cuisine"] == cuisine, (cuisine, e["recipe"]["slug"])
    # 14 öğün üç mutfağa dengeli dağılır (5/5/4)
    assert set(meal_cuisines) == {"anadolu", "italyan", "uzakdogu"}
    assert max(meal_cuisines.values()) - min(meal_cuisines.values()) <= 1

    # Planlarım listesinde de mutfaklar görünür
    summaries = (await client.get("/api/meal-plans", headers=auth_headers)).json()
    assert summaries[0]["cuisines"] == ["anadolu", "italyan", "uzakdogu"]


async def test_breakfast_comes_from_cuisines_that_have_one(client, auth_headers):
    plan = (await client.post("/api/meal-plans", headers=auth_headers, json={
        "period": "weekly", "cuisines": ["italyan", "meksika"], "meal_slots": ["kahvalti"],
    })).json()
    mains = [e["recipe"]["slug"] for e in plan["entries"] if e["course"] == "ana"]
    assert len(mains) == 7
    assert set(mains) <= {"sebzeli-frittata", "huevos-rancheros", "peynirli-quesadilla"}


async def test_suggest_another_keeps_meal_cuisine(client, auth_headers):
    plan = (await client.post("/api/meal-plans", headers=auth_headers, json={
        "period": "daily", "cuisines": ["meksika", "uzakdogu"], "meal_slots": ["ogle", "aksam"],
    })).json()
    for _ in range(3):
        for entry in [e for e in plan["entries"] if e["course"] in ("ana", "corba", "salata")]:
            cuisine = entry["recipe"]["cuisine"]
            r = await client.patch(f"/api/meal-plans/{plan['id']}/entries/{entry['id']}", headers=auth_headers, json={})
            assert r.status_code == 200, r.text
            plan = r.json()
            changed = next(e for e in plan["entries"] if e["id"] == entry["id"])
            assert changed["recipe"]["cuisine"] == cuisine


async def test_unknown_cuisine_in_list(client, auth_headers):
    r = await client.post("/api/meal-plans", headers=auth_headers, json={"cuisines": ["italyan", "fransiz"]})
    assert r.status_code == 404 and "fransiz" in r.json()["detail"]


async def test_recipes_with_missing_ingredients_are_hidden(client, auth_headers, db):
    # Katalog boşken (ilk kurulum) hiçbir tarif gizlenmez
    assert await refresh_availability(db) == {"recipes": 84, "hidden": 0}
    assert len((await client.get("/api/recipes", params={"cuisine": "italyan"})).json()) == 15

    await _add_products(db, POMODORO)
    stats = await refresh_availability(db)
    assert stats["recipes"] == 84 and stats["hidden"] > 70

    italian = {r["slug"] for r in (await client.get("/api/recipes", params={"cuisine": "italyan"})).json()}
    assert "spagetti-pomodoro" in italian
    assert "spagetti-bolonez" not in italian and "tiramisu" not in italian
    cuisines = {c["slug"]: c for c in (await client.get("/api/cuisines")).json()}
    assert cuisines["italyan"]["recipe_count"] == len(italian)
    assert cuisines["italyan"]["examples"][0] == "Domatesli Fesleğenli Spagetti"
    # Soya sosu yok: Uzak Doğu'nun hiçbir tarifi kalmaz
    assert cuisines["uzakdogu"]["recipe_count"] == 0

    # Plan yalnız malzemesi bulunan tariflerden oluşur
    plan = (await client.post("/api/meal-plans", headers=auth_headers, json={
        "period": "weekly", "cuisines": ["italyan"], "meal_slots": ["aksam"],
    })).json()
    assert {e["recipe"]["slug"] for e in plan["entries"]} <= italian
    assert plan["cost"]["missing_count"] == 0
    r = await client.post("/api/meal-plans", headers=auth_headers, json={"cuisines": ["uzakdogu"]})
    assert r.status_code == 422

    # Markete kıyma ve rende peynir gelince Bolonez yeniden görünür
    await _add_products(db, [
        ("Dana Kıyma 500 g", Unit.G, 500, "250.00"),
        ("Kuru Soğan 1 kg", Unit.G, 1000, "20.00"),
        ("Havuç 1 kg", Unit.G, 1000, "25.00"),
        ("Domates Salçası 830 g", Unit.G, 830, "70.00"),
        ("Rende Kaşar 200 g", Unit.G, 200, "90.00"),
    ])
    await refresh_availability(db)
    italian = {r["slug"] for r in (await client.get("/api/recipes", params={"cuisine": "italyan"})).json()}
    assert "spagetti-bolonez" in italian


async def test_pantry_items_do_not_hide_recipes(db):
    """Tuz, karabiber gibi evde var sayılanlar katalogda olmasa da tarif gizlenmez."""
    await _add_products(db, POMODORO)
    await refresh_availability(db)
    from app.models import Recipe

    pomodoro = (await db.scalars(select(Recipe).where(Recipe.slug == "spagetti-pomodoro"))).one()
    await db.refresh(pomodoro)
    assert pomodoro.missing_ingredients == ""
    bolonez = (await db.scalars(select(Recipe).where(Recipe.slug == "spagetti-bolonez"))).one()
    await db.refresh(bolonez)
    assert "Dana kıyma" in bolonez.missing_ingredients
