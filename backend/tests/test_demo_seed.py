from decimal import Decimal as D

from app.services.demo_seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo


async def test_seed_demo_matches_demo_numbers(client, db):
    assert (await seed_demo(db))["products"] == 38
    assert (await seed_demo(db))["products"] == 0  # tekrar çalıştırmak bir şey eklemez

    r = await client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    lists = {row["name"]: row for row in (await client.get("/api/lists", headers=h)).json()}
    weekly = lists["Haftalık Alışveriş"]
    assert weekly["item_count"] == 8

    opt = (await client.get(f"/api/lists/{weekly['id']}/optimize", headers=h)).json()
    # Haftalık listedeki her ürün dört markette de var
    assert opt["single_market"]["available"] is True
    assert D(opt["opportunist"]["total"]) == D(weekly["estimated_total"])
