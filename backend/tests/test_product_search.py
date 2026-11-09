"""Ürün arama: yazılan kelime gerçekten eşleşmeli (ilk iki harf yetmez), yakın şube önce gelir."""

from datetime import datetime, timezone
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.models import GroupMember, Market, Product, ProductGroup, Store, StorePrice, UserStore
from app.services.normalize import normalize_name

NAMES = [
    "Dana Kıyma 500 g", "Kıymalı Börek", "Kido Kakaolu Süt", "Kırkağaç Kavun", "Kırık Pirinç", "Kibrit",
    "Kırmızı Erik", "Süt 1 L", "Laktozsuz Süt 1 L", "Sütlaç", "Yumurta 30'lu", "Ayran 1 L", "Naneli Ayran",
    "Ayranlı Çorba Mix",
]


@pytest.fixture
async def groups(db):
    market = (await db.scalars(select(Market).order_by(Market.id))).first()
    ids = {}
    for i, name in enumerate(NAMES):
        g = ProductGroup(name=name, normalized_name=normalize_name(name))
        db.add(g)
        await db.flush()
        p = Product(
            market_id=market.id, external_id=f"p{i}", name=name, normalized_name=normalize_name(name),
            current_price=D("10"), last_seen_at=datetime.now(timezone.utc),
        )
        db.add(p)
        await db.flush()
        db.add(GroupMember(group_id=g.id, product_id=p.id))
        ids[name] = g.id
    await db.commit()
    return ids


async def _names(client, q, **params):
    r = await client.get("/api/products", params={"q": q, **params})
    assert r.status_code == 200
    return [x["name"] for x in r.json()]


@pytest.mark.parametrize("q", ["kıyma", "kiyma", "KIYMA", "Kıyma"])
async def test_kiyma_only_matches_the_word(client, groups, q):
    names = await _names(client, q)
    assert names[0] == "Dana Kıyma 500 g"  # tam kelime önce
    assert "Kıymalı Börek" in names  # kelime başı sonra
    for bad in ("Kido Kakaolu Süt", "Kırkağaç Kavun", "Kırık Pirinç", "Kibrit", "Kırmızı Erik"):
        assert bad not in names


async def test_sut_exact_word_before_prefix(client, groups):
    names = await _names(client, "süt")
    assert names[:2] == ["Süt 1 L", "Laktozsuz Süt 1 L"] or names[0] == "Süt 1 L"
    assert names.index("Süt 1 L") < names.index("Sütlaç")
    assert "Kibrit" not in names and "Kırık Pirinç" not in names


async def test_yumurta_and_ayran(client, groups):
    assert await _names(client, "yumurta") == ["Yumurta 30'lu"]
    assert await _names(client, "yumurtta") == []  # yazım hatası yakınlık yüzünden eşleşmez
    ayran = await _names(client, "ayran")
    assert set(ayran) == {"Ayran 1 L", "Naneli Ayran", "Ayranlı Çorba Mix"}
    assert ayran.index("Ayran 1 L") < ayran.index("Ayranlı Çorba Mix")


async def test_every_word_must_match(client, groups):
    assert await _names(client, "naneli ayran") == ["Naneli Ayran"]
    assert await _names(client, "dana ayran") == []


async def test_percent_is_not_a_wildcard(client, groups):
    assert await _names(client, "%") == []


async def test_nearest_store_first(client, db, auth_headers, groups):
    markets = (await db.scalars(select(Market).order_by(Market.id))).all()
    near = Store(market_id=markets[0].id, external_id="n", name="Yakın Şube", latitude=D("40.990"), longitude=D("29.030"))
    far = Store(market_id=markets[1].id, external_id="f", name="Uzak Şube", latitude=D("41.050"), longitude=D("29.100"))
    db.add_all([near, far])
    await db.flush()
    user_id = (await client.get("/api/auth/me", headers=auth_headers)).json()["id"]
    db.add_all([UserStore(user_id=user_id, store_id=near.id), UserStore(user_id=user_id, store_id=far.id)])
    # İki "Ayran" ürünü: biri yalnız uzak şubede (ucuz), biri yakın şubede (pahalı)
    products = {}
    for key, name in (("sade", "Ayran 1 L"), ("naneli", "Naneli Ayran")):
        products[key] = (await db.scalars(select(Product).where(Product.name == name))).one()
    now = datetime.now(timezone.utc)
    db.add_all([
        StorePrice(product_id=products["sade"].id, store_id=far.id, price=D("5"), updated_at=now),
        StorePrice(product_id=products["naneli"].id, store_id=near.id, price=D("50"), updated_at=now),
        StorePrice(product_id=products["naneli"].id, store_id=far.id, price=D("20"), updated_at=now),
    ])
    await db.commit()

    loc = {"lat": 40.987, "lon": 29.027}
    r = await client.get("/api/products", params={"q": "ayran", **loc}, headers=auth_headers)
    body = r.json()
    assert [x["name"] for x in body] == ["Naneli Ayran", "Ayran 1 L"]  # ucuz olan değil, yakın olan önce
    assert body[0]["nearest_store_name"] == "Yakın Şube"
    assert D(body[0]["nearest_price"]) == D("50")  # en yakın şubedeki fiyat
    assert D(body[0]["min_price"]) == D("20")  # "en ucuz" bilgisi hâlâ fiyat tarafında duruyor
    assert body[0]["nearest_distance_km"] < body[1]["nearest_distance_km"]

    # Konum yoksa fiyata göre değil ada göre
    names = [x["name"] for x in (await client.get("/api/products", params={"q": "ayran"}, headers=auth_headers)).json()]
    assert names == ["Ayran 1 L", "Naneli Ayran"]

    group_id = await db.scalar(select(GroupMember.group_id).where(GroupMember.product_id == products["naneli"].id))
    detail = (await client.get(f"/api/products/{group_id}", params=loc, headers=auth_headers)).json()
    sp = detail["products"][0]["store_prices"]
    assert [s["store_name"] for s in sp] == ["Yakın Şube", "Uzak Şube"]
