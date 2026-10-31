"""Esnek süre, hafta içi, bütçe, bir pişir iki ye, az israf ve "dolabımda ne var"."""

import random
from collections import Counter
from datetime import date
from decimal import Decimal as D

from app.services import meals as svc
from tests.test_meals import _recipes, kitchen  # noqa: F401  (fixture)


async def _create(client, headers, **body):
    body.setdefault("cuisines", ["anadolu"])
    r = await client.post("/api/meal-plans", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_custom_length_and_weekdays(client, auth_headers):
    # 2 Kasım 2026 Pazartesi; 10 gün, yalnız hafta içi -> 8 gün yemek
    plan = await _create(
        client, auth_headers, days=10, weekdays=[0, 1, 2, 3, 4], meal_slots=["aksam"], courses=["ana"],
        start_date="2026-11-02",
    )
    assert plan["days"] == 10 and plan["period"] == "custom" and plan["weekdays"] == [0, 1, 2, 3, 4]
    assert plan["name"] == "10 günlük yemek planı · 2 Kasım"
    dates = sorted({e["date"] for e in plan["entries"]})
    assert len(dates) == 8
    assert all(date.fromisoformat(d).weekday() < 5 for d in dates)
    assert "2026-11-07" not in dates and "2026-11-11" in dates

    # Plan dışındaki güne ekleme yapılamaz; 10. güne (index 9) yapılabilir
    add = f"/api/meal-plans/{plan['id']}/entries"
    assert (await client.post(add, headers=auth_headers, json={"day_index": 10, "slot": "aksam", "course": "ana"})).status_code == 422
    r = await client.post(add, headers=auth_headers, json={"day_index": 5, "slot": "aksam", "course": "ana"})
    assert r.status_code == 201 and any(e["day_index"] == 5 for e in r.json()["entries"])

    # Seçilen günler süreye hiç denk gelmiyorsa hata (Pazartesi başlayan 1 günlük planda Pazar)
    r = await client.post("/api/meal-plans", headers=auth_headers, json={"days": 1, "weekdays": [6], "start_date": "2026-11-02"})
    assert r.status_code == 422
    assert (await client.post("/api/meal-plans", headers=auth_headers, json={"days": 15})).status_code == 422
    # Eski istemci: period yeterli
    assert (await _create(client, auth_headers, period="daily"))["days"] == 1


async def test_leftovers_lunch_next_day(client, auth_headers):
    plan = await _create(
        client, auth_headers, days=3, meal_slots=["ogle", "aksam"], courses=["corba", "ana", "salata"],
        leftovers=True, start_date="2026-11-02",
    )
    assert plan["leftovers"] is True
    entries = {e["id"]: e for e in plan["entries"]}
    by_meal = {(e["day_index"], e["slot"], e["course"]): e for e in plan["entries"]}
    # Gün 1 ve 2 öğlesi: önceki akşamın çorbası ve ana yemeği; salata taze
    for day in (1, 2):
        for course in ("corba", "ana"):
            left = by_meal[(day, "ogle", course)]
            src = entries[left["leftover_of"]]
            assert (src["day_index"], src["slot"], src["course"]) == (day - 1, "aksam", course)
            assert src["recipe"]["id"] == left["recipe"]["id"] and src["leftover_for"] == [left["id"]]
        assert by_meal[(day, "ogle", "salata")]["leftover_of"] is None
    # İlk günün öğlesi ve son akşam kalan değil (son akşamın ertesi günü yok)
    assert by_meal[(0, "ogle", "ana")]["leftover_of"] is None
    assert by_meal[(2, "aksam", "ana")]["leftover_for"] == []

    # Akşam yemeği değişince kalanı da değişir
    src = by_meal[(0, "aksam", "ana")]
    url = f"/api/meal-plans/{plan['id']}/entries"
    changed = (await client.patch(f"{url}/{src['id']}", headers=auth_headers, json={})).json()
    new = {(e["day_index"], e["slot"], e["course"]): e for e in changed["entries"]}
    assert new[(0, "aksam", "ana")]["recipe"]["id"] != src["recipe"]["id"]
    assert new[(1, "ogle", "ana")]["recipe"]["id"] == new[(0, "aksam", "ana")]["recipe"]["id"]

    # Kalanı değiştiren kullanıcı o öğünde ayrıca pişirir: bağ kopar
    left = new[(2, "ogle", "ana")]
    changed = (await client.patch(f"{url}/{left['id']}", headers=auth_headers, json={})).json()
    new = {(e["day_index"], e["slot"], e["course"]): e for e in changed["entries"]}
    assert new[(2, "ogle", "ana")]["leftover_of"] is None
    assert new[(1, "aksam", "ana")]["leftover_for"] == []

    # Kaynağı silinen kalan yemek ayrıca pişirilecek yemek olarak kalır
    src = new[(0, "aksam", "corba")]
    removed = (await client.delete(f"{url}/{src['id']}", headers=auth_headers)).json()
    after = {(e["day_index"], e["slot"], e["course"]): e for e in removed["entries"]}
    assert (0, "aksam", "corba") not in after
    assert after[(1, "ogle", "corba")]["leftover_of"] is None


async def test_leftovers_without_lunch_every_other_dinner(client, auth_headers):
    plan = await _create(client, auth_headers, days=5, meal_slots=["aksam"], courses=["ana"], leftovers=True)
    mains = sorted(plan["entries"], key=lambda e: e["day_index"])
    assert [e["leftover_of"] is not None for e in mains] == [False, True, False, True, False]
    assert mains[1]["recipe"]["id"] == mains[0]["recipe"]["id"]
    # Maliyet: kalan da porsiyon sayılır (iki kat pişirildi), 5 akşam x 2 kişi
    assert plan["cost"]["portions"] == 10


async def test_have_items_excluded_from_cost_and_preferred(client, auth_headers, kitchen):
    ingredients = (await client.get("/api/ingredients")).json()
    names = [i["name"] for i in ingredients]
    assert "Tuz" not in names  # evde var sayılanlar seçicide yok
    assert ingredients[0]["recipe_count"] >= ingredients[-1]["recipe_count"]
    assert "Kırmızı mercimek" in names

    # Dolabımda ne var: mercimek ve soğan; mercimek kullanan tarifler başta, eksikleri yazılı
    found = (await client.get("/api/recipes", params={"have": ["Kırmızı mercimek", "Kuru soğan"]})).json()
    assert found and all(r["missing"] is not None for r in found)
    misses = [len(r["missing"]) for r in found]
    assert misses == sorted(misses)
    mercimek = next(r for r in found if r["slug"] == "mercimek-corbasi")
    assert "Kırmızı mercimek" not in mercimek["missing"]
    assert (await client.get("/api/recipes")).json()[0]["missing"] is None

    plan = await _create(
        client, auth_headers, period="daily", meal_slots=["aksam"], courses=["corba"], have=["Kırmızı mercimek"],
    )
    assert plan["have"] == ["Kırmızı mercimek"]
    # Dolaptaki malzemeyi kullanan bir çorba (mercimek, ezogelin...)
    uses_lentil = {r["slug"] for r in found if r["course_type"] == "corba" and "Kırmızı mercimek" not in r["missing"]}
    assert plan["entries"][0]["recipe"]["slug"] in uses_lentil
    lines = {line["name"] for line in plan["cost"]["lines"]}
    assert "Kırmızı mercimek" not in lines and plan["cost"]["have"] == ["Kırmızı mercimek"]

    # Listeye aktarırken evdeki malzeme eklenmez
    out = (await client.post(f"/api/meal-plans/{plan['id']}/to-list", headers=auth_headers, json={})).json()
    assert out["list"]["items"] and all("Mercimek" not in i["group_name"] for i in out["list"]["items"])


async def test_low_waste_prefers_shared_ingredients():
    """Birim test: eşit kullanımda ortak malzemesi olan tarif seçilir."""

    class Ing:
        def __init__(self, name):
            self.name = name
            self.search_term = name
            self.is_pantry = False

    class R:
        def __init__(self, id, ings):
            self.id = id
            self.ingredients = [Ing(i) for i in ings]
            self.score = 50

    first = R(1, ["maydanoz", "yogurt", "bulgur"])
    shares = R(2, ["maydanoz", "yogurt", "nohut"])
    other = R(3, ["kabak", "pirinc", "nane"])
    rng = random.Random(1)
    prefs = svc._Prefs([first, shares, other], low_waste=True, have=set(), prices=None)
    prefs.add(first)
    picks = Counter(svc._choose([shares, other], Counter(), set(), set(), rng, prefs=prefs).id for _ in range(30))
    assert picks == {2: 30}
    # Çeşitlilik önce: ortak malzemeli tarif zaten bir kez kullanıldıysa diğeri seçilir
    assert svc._choose([shares, other], Counter({2: 1}), set(), set(), rng, prefs=prefs).id == 3
    # Tercih yoksa ikisi de seçilebilir
    plain = Counter(svc._choose([shares, other], Counter(), set(), set(), random.Random(i)).id for i in range(40))
    assert set(plain) == {2, 3}


async def test_budget_swaps_expensive_dishes(client, auth_headers, kitchen):
    unlimited = await _create(client, auth_headers, days=3, meal_slots=["aksam"], courses=["corba", "ana", "tatli", "icecek"])
    assert unlimited["budget_status"] is None

    plan = await _create(
        client, auth_headers, days=3, meal_slots=["aksam"], courses=["corba", "ana", "tatli", "icecek"], budget="150",
    )
    status = plan["budget_status"]
    assert D(status["budget"]) == 150 and D(status["total"]) == D(plan["cost"]["purchase_total"])
    assert status["within"] == (D(status["total"]) <= 150)
    assert status["swaps"] >= 0
    # Ana yemek hiç çıkarılmaz
    assert sorted(e["day_index"] for e in plan["entries"] if e["course"] == "ana") == [0, 1, 2]
    # Bütçe uygulanınca aynı seçimlerle bütçesiz plandan pahalı olmaz (ucuzlar seçilir)
    assert D(plan["cost"]["purchase_total"]) <= D(unlimited["cost"]["purchase_total"]) or status["within"]

    # Bol bütçe: hiçbir şey değişmez
    roomy = await _create(client, auth_headers, days=2, meal_slots=["aksam"], courses=["ana", "icecek"], budget="100000")
    assert roomy["budget_status"] == {**roomy["budget_status"], "within": True, "swaps": 0}

    # Çok düşük bütçe: ucuzu kalmayınca içecek ve tatlı çıkar, ana yemekler kalır; aşım görünür
    tiny = await _create(client, auth_headers, days=2, meal_slots=["aksam"], courses=["ana", "tatli", "icecek"], budget="1")
    assert tiny["budget_status"]["within"] is False and tiny["budget_status"]["swaps"] > 0
    assert sorted(e["course"] for e in tiny["entries"]) == ["ana", "ana"]
