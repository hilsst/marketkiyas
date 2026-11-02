"""İndirimden menü: indirimdeki malzemeler, bunları kullanan tarifler ve from_deals planı."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D

from sqlalchemy import select

from app.models import AktuelItem, PriceHistory, Product
from tests.test_meals import kitchen  # noqa: F401  (fixture)


async def _discount_chicken(db):
    """Piliç göğüs 260 -> 220 TL (%15): katalog fırsatı."""
    pilic = await db.scalar(select(Product).where(Product.name == "Piliç Göğüs Fileto 1 kg"))
    db.add(PriceHistory(product_id=pilic.id, price=D("260.00"), recorded_at=datetime.now(timezone.utc) - timedelta(days=3)))
    await db.commit()
    return pilic


def _aktuel(title, price, old, qty=None, **kw):
    return AktuelItem(
        market_slug="bim", source_key=f"k-{title}", period_key="1", period_label="bu hafta", title=title,
        price=D(price), old_price=D(old) if old else None, quantity_text=qty,
        starts_on=date.today() - timedelta(days=1), ends_on=date.today() + timedelta(days=3), **kw,
    )


async def test_no_deals_gives_note_and_empty_menu(client, kitchen):  # noqa: F811
    r = await client.get("/api/meal-deals")
    assert r.status_code == 200
    body = r.json()
    assert body["ingredients"] == [] and body["recipes"] == [] and "indirimde olan" in body["note"]


async def test_catalog_deal_lists_ingredient_and_recipes(client, db, kitchen):  # noqa: F811
    await _discount_chicken(db)
    body = (await client.get("/api/meal-deals")).json()
    assert body["note"] is None
    chicken = [i for i in body["ingredients"] if i["source"] == "katalog"]
    assert chicken, body
    top = chicken[0]
    assert top["discount_percent"] == 15 and D(top["price"]) == D("220.00") and top["recipe_count"] >= 1
    assert body["recipes"]
    assert all(r["deal_ingredients"] for r in body["recipes"])
    # En çok indirimli malzeme kullanan tarif başta
    counts = [len(r["deal_ingredients"]) for r in body["recipes"]]
    assert counts == sorted(counts, reverse=True)


async def test_aktuel_is_hint_only_and_junk_is_ignored(client, db, kitchen):  # noqa: F811
    db.add_all([
        _aktuel("Piliç But 1 kg", "120.00", "150.00"),
        _aktuel("Tavuk Aromalı Cips 150 g", "30.00", "40.00"),  # gıda ama tavuk değil
        _aktuel("Çamaşır Suyu Limonlu 2 L", "40.00", "50.00"),  # gıda değil
        _aktuel("Eski Piliç Kanat 1 kg", "90.00", "100.00"),
    ])
    old = await db.scalar(select(AktuelItem).where(AktuelItem.title == "Eski Piliç Kanat 1 kg"))
    old.ends_on = date.today() - timedelta(days=2)  # süresi dolmuş
    await db.commit()

    body = (await client.get("/api/meal-deals")).json()
    names = {i["product_name"] for i in body["ingredients"]}
    assert "Piliç But 1 kg" in names
    assert not names & {"Tavuk Aromalı Cips 150 g", "Çamaşır Suyu Limonlu 2 L", "Eski Piliç Kanat 1 kg"}
    assert all(i["source"] == "aktuel" for i in body["ingredients"])


async def test_plan_from_deals_reports_deals_and_prefers_them(client, db, auth_headers, kitchen):  # noqa: F811
    await _discount_chicken(db)
    # Kontrol: from_deals kapalıyken plan alanı false ve deals boş
    off = await client.post("/api/meal-plans", headers=auth_headers, json={
        "cuisines": ["anadolu"], "period": "daily", "meal_slots": ["aksam"], "courses": ["ana"],
    })
    assert off.status_code == 201 and off.json()["from_deals"] is False and off.json()["deals"] == []

    hits = 0
    for _ in range(4):
        r = await client.post("/api/meal-plans", headers=auth_headers, json={
            "cuisines": ["anadolu"], "period": "daily", "meal_slots": ["aksam"], "courses": ["ana"],
            "from_deals": True,
        })
        assert r.status_code == 201, r.text
        plan = r.json()
        assert plan["from_deals"] is True
        # Plan detayı tekrar okunduğunda da aynı
        again = (await client.get(f"/api/meal-plans/{plan['id']}", headers=auth_headers)).json()
        assert again["from_deals"] is True and again["deals"] == plan["deals"]
        for d in plan["deals"]:
            assert d["source"] in ("katalog", "aktuel") and (d["discount_percent"] or 0) >= 5 or d["source"] == "aktuel"
        hits += bool(plan["deals"])
    assert hits >= 3  # indirimli malzemeli yemek hemen her seferinde öne çıkar
