import json
from datetime import datetime, timezone
from decimal import Decimal as D

import httpx
import pytest
from sqlalchemy import func, select

from app.models import Category, GroupMember, Market, PriceHistory, Product, ProductGroup, Store, StorePrice, Unit
from app.services.marketfiyati.client import MarketFiyatiClient, MarketFiyatiError
from app.services.marketfiyati.ingest import (
    category_slug,
    market_slug,
    refresh_nearby_stores,
    sync_area,
    sync_selected_stores,
)
from app.services.marketfiyati.schemas import SearchPage, SearchProduct
from tests.marketfiyati_fake import FakeMarketFiyati, load

AREA = dict(latitude=40.987, longitude=29.027, distance_km=5)


def test_parse_search_page_skips_broken_rows():
    page = SearchPage.from_raw(load("marketfiyati_search_sut.json"))
    assert [p.id for p in page.products] == ["mf-1001", "mf-1002", "mf-1003"]
    sutas = page.products[1]
    assert sutas.prices[0].price == D("32.75")  # "32,75" metni
    assert len(page.products[2].prices) == 1  # fiyatsız şube atlandı


def test_market_slug_aliases():
    assert market_slug("ŞOK") == "sok"
    assert market_slug("CarrefourSA") == "carrefour"
    assert market_slug("Tarım Kredi") == "tarim_kredi"


@pytest.mark.parametrize(
    ("menu", "main", "slug"),
    [
        ("Süt Ürünleri ve Kahvaltılık", "Peynir", "sut-kahvaltilik"),
        ("Et, Tavuk ve Balık", "Beyaz Et", "et-tavuk-balik"),
        ("Temel Gıda", "Bakliyat", "temel-gida"),
        ("Temel Gıda", "Ekmek ve Unlu Mamüller", "firin"),
        ("Temel Gıda", "Bebek Mamaları", "bebek"),
        ("Atıştırmalık ve Tatlı", "Dondurmalar", "atistirmalik"),
        ("Diğer Ürünler", "Bebek Gereçleri", "bebek"),
        ("Diğer Ürünler", "Pet Shop", None),
        (None, None, None),
    ],
)
def test_category_slug(menu, main, slug):
    raw = {"id": "x", "title": "Ürün", "menu_category": menu, "main_category": main}
    assert category_slug(SearchProduct.from_raw(raw)) == slug


async def test_search_category_request_body():
    fake = FakeMarketFiyati()
    async with fake.client() as client:
        await client.search_category("Temel Gıda", depot_ids=["bim-4501"], **AREA)
    request = fake.requests[0]
    assert request.url.path == "/api/v2/searchByCategories"
    body = json.loads(request.content)
    assert body["keywords"] == "Temel Gıda"
    assert body["menuCategory"] is True
    assert body["depots"] == ["bim-4501"]


async def test_selected_stores_one_store_per_chain_per_request(db):
    # marketfiyati bir üründe zincir başına tek şube döndürür; aynı zincirin şubeleri ayrı aranmalı
    fake = FakeMarketFiyati()
    async with fake.client() as client:
        await sync_area(db, client, keywords=["süt"], **AREA)
        store_ids = list(await db.scalars(select(Store.id).where(Store.external_id.like("a101-%") | (Store.external_id == "bim-4501"))))
        fake.requests.clear()
        await sync_selected_stores(db, client, store_ids=store_ids, categories=["Süt Ürünleri ve Kahvaltılık"])

    depot_sets = [json.loads(r.content)["depots"] for r in fake.requests if json.loads(r.content)["pages"] == 0]
    assert sorted(d for depots in depot_sets for d in depots) == ["a101-7788", "a101-7790", "bim-4501"]
    for depots in depot_sets:
        chains = [d.split("-")[0] for d in depots]
        assert len(chains) == len(set(chains))


async def test_category_sync_assigns_categories(db):
    fake = FakeMarketFiyati()
    for row in fake.search["content"]:
        row["menu_category"] = "Süt Ürünleri ve Kahvaltılık"
        row["main_category"] = "Süt"
    async with fake.client() as client:
        await sync_area(db, client, keywords=[], categories=["Süt Ürünleri ve Kahvaltılık"], **AREA)

    category_id = await db.scalar(select(Category.id).where(Category.slug == "sut-kahvaltilik"))
    groups = (await db.scalars(select(ProductGroup))).all()
    assert groups and all(g.category_id == category_id for g in groups)
    products = (await db.scalars(select(Product))).all()
    assert products and all(p.category_id == category_id for p in products)

    # Sitenin alt kategorisi ("Süt") kategorinin altında bir alt kategori olur ve gruplara yazılır
    sub = await db.scalar(select(Category).where(Category.parent_id == category_id))
    assert (sub.name, sub.slug) == ("Süt", "sut-kahvaltilik--sut")
    assert all(g.subcategory_id == sub.id for g in groups)


async def test_client_retries_and_respects_retry_after(monkeypatch):
    calls = []
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("app.services.http.asyncio.sleep", fake_sleep)

    def handler(request):
        calls.append(request.headers["User-Agent"])
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        if len(calls) == 2:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json=load("marketfiyati_nearest.json"))

    client = MarketFiyatiClient(
        "https://api.test", transport=httpx.MockTransport(handler), min_interval=0, max_retries=3
    )
    depots = await client.nearest_depots(40.98, 29.02, 5)
    await client.aclose()

    assert [d.id for d in depots] == ["bim-4501", "a101-7788", "far-1"]
    assert len(calls) == 3
    assert set(calls) == {"MarketKiyas/0.1 (+https://github.com/hilsst/marketkiyas)"}  # kendini açıkça tanıtır
    assert sleeps[0] == 3.0  # Retry-After


async def test_client_does_not_retry_client_errors():
    fake = FakeMarketFiyati()
    fake.fail_with = 400
    client = fake.client(max_retries=3)
    with pytest.raises(MarketFiyatiError):
        await client.nearest_depots(40.98, 29.02, 5)
    await client.aclose()
    assert len(fake.requests) == 1


async def test_client_gives_up_after_max_retries(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("app.services.http.asyncio.sleep", no_sleep)
    fake = FakeMarketFiyati()
    fake.fail_with = 503
    client = fake.client(max_retries=2)
    with pytest.raises(MarketFiyatiError):
        await client.search(keywords="süt", **{"latitude": 1, "longitude": 1, "distance_km": 1})
    await client.aclose()
    assert len(fake.requests) == 3


async def test_search_request_body():
    fake = FakeMarketFiyati()
    async with fake.client() as client:
        await client.search(keywords="süt", depot_ids=["bim-4501"], **AREA)
    body = json.loads(fake.requests[0].content)
    assert body == {
        "keywords": "süt",
        "pages": 0,
        "size": 100,
        "latitude": 40.987,
        "longitude": 29.027,
        "distance": 5,
        "depots": ["bim-4501"],
    }


async def test_sync_area_ingests_products_prices_and_groups(db):
    fake = FakeMarketFiyati()
    async with fake.client() as client:
        stats = await sync_area(db, client, keywords=["süt"], **AREA)

    assert stats.products_seen == 3
    assert set(stats.markets_created) == {"migros"}  # bim/a101/sok seed'de var
    assert stats.groups_created == 2  # "Süt 1 L" ve "Laktozsuz Süt 1 L"

    groups = {g.name: g for g in (await db.scalars(select(ProductGroup))).all()}
    milk = groups["Süt 1 L"]
    assert milk.normalized_name == "sut 1000ml"
    assert (milk.quantity, milk.unit) == (D(1000), Unit.ML)

    members = (
        await db.execute(
            select(Product.brand, Market.slug, Product.current_price)
            .join(GroupMember, GroupMember.product_id == Product.id)
            .join(Market, Market.id == Product.market_id)
            .where(GroupMember.group_id == milk.id)
            .order_by(Market.slug, Product.brand)
        )
    ).all()
    # Pınar ve Sütaş aynı grupta; ürün zincir başına bir satır, fiyat = zincirin en ucuz şubesi
    assert members == [
        ("Pınar", "a101", D("33.90")),
        ("Pınar", "bim", D("34.50")),
        ("Sütaş", "bim", D("32.75")),
        ("Sütaş", "migros", D("37.50")),
        ("Sütaş", "sok", D("36.00")),
    ]
    assert await db.scalar(select(func.count()).select_from(StorePrice)) == 7
    assert await db.scalar(select(func.count()).select_from(Store)) == 5


async def test_resync_is_idempotent_and_records_price_changes(db):
    fake = FakeMarketFiyati()
    async with fake.client() as client:
        await sync_area(db, client, keywords=["süt"], **AREA)
        history_before = await db.scalar(select(func.count()).select_from(PriceHistory))

        # Aynı veri: yeni satır yok
        await sync_area(db, client, keywords=["süt"], **AREA)
        assert await db.scalar(select(func.count()).select_from(PriceHistory)) == history_before
        assert await db.scalar(select(func.count()).select_from(Product)) == 6

        # Bahariye A101'de Pınar indirime girdi
        fake.search["content"][0]["productDepotInfoList"][1]["price"] = 29.9
        stats = await sync_area(db, client, keywords=["süt"], **AREA)
    assert stats.price_changes == 1
    price = await db.scalar(
        select(Product.current_price).join(Market).where(Product.external_id == "mf-1001", Market.slug == "a101")
    )
    assert price == D("29.90")


async def test_refresh_nearby_stores(db):
    fake = FakeMarketFiyati()
    async with fake.client() as client:
        ids = await refresh_nearby_stores(db, client, 40.987, 29.027, 5)
    assert len(ids) == 3
    store = await db.scalar(select(Store).where(Store.external_id == "bim-4501"))
    assert store.name == "Moda Şubesi" and store.latitude == D("40.986200")


async def test_campaign_price_is_recorded_for_deals(db):
    fake = FakeMarketFiyati()
    # BİM Moda'da Pınar süt indirimde: 34,50 (önce 40,00)
    fake.search["content"][0]["productDepotInfoList"][0].update(discount=True, discountlessPrice=40)
    async with fake.client() as client:
        await sync_area(db, client, keywords=["süt"], **AREA)
    row = (
        await db.execute(
            select(PriceHistory.price, PriceHistory.regular_price, PriceHistory.is_campaign)
            .join(Product)
            .join(Market)
            .where(Product.external_id == "mf-1001", Market.slug == "bim")
        )
    ).one()
    assert tuple(row) == (D("34.50"), D("40.00"), True)

    # Aynı veri tekrar gelince yeni satır yazılmaz; kampanya bitince yazılır
    async with fake.client() as client:
        await sync_area(db, client, keywords=["süt"], **AREA)
        fake.search["content"][0]["productDepotInfoList"][0].update(discount=False)
        await sync_area(db, client, keywords=["süt"], **AREA)
    rows = (
        await db.execute(
            select(PriceHistory.is_campaign)
            .join(Product)
            .join(Market)
            .where(Product.external_id == "mf-1001", Market.slug == "bim")
            .order_by(PriceHistory.id)
        )
    ).scalars().all()
    assert rows == [True, False]


def test_index_time_is_parsed_as_turkish_time():
    raw = {
        "id": "x",
        "title": "Süt",
        "productDepotInfoList": [
            {"depotId": "bim-1", "marketAdi": "bim", "price": 10, "indexTime": "29.10.2026 09:15"},
            {"depotId": "a101-1", "marketAdi": "a101", "price": 11, "indexTime": "bozuk"},
            {"depotId": "sok-1", "marketAdi": "sok", "price": 12, "indexTime": "01.01.2999 10:00"},
        ],
    }
    first, broken, future = SearchProduct.from_raw(raw).prices
    assert first.updated_at == datetime(2026, 10, 29, 6, 15, tzinfo=timezone.utc)
    assert broken.updated_at is None
    assert future.updated_at <= datetime.now(timezone.utc)  # gelecekteki saat şimdiye çekilir


async def test_store_price_keeps_source_update_time(db):
    fake = FakeMarketFiyati()
    fake.search["content"][0]["productDepotInfoList"][0]["indexTime"] = "28.10.2026 09:15"
    async with fake.client() as client:
        await sync_area(db, client, keywords=["süt"], **AREA)
    moda = await db.scalar(select(Store.id).where(Store.external_id == "bim-4501"))
    updated = await db.scalars(select(StorePrice.updated_at).where(StorePrice.store_id == moda))
    assert datetime(2026, 10, 28, 6, 15, tzinfo=timezone.utc) in list(updated)


async def test_sync_area_without_depots_searches_nearby_depots(db):
    # Şubesiz arama konumu yok sayıp İstanbul fiyatı getirir: önce çevredeki şubeler alınır
    fake = FakeMarketFiyati()
    async with fake.client() as client:
        await sync_area(db, client, keywords=["süt"], **AREA)
    assert fake.requests[0].url.path == "/api/v2/nearest"
    searches = [json.loads(r.content) for r in fake.requests if r.url.path == "/api/v2/search"]
    assert searches and all(b["depots"] == ["bim-4501", "a101-7788", "far-1"] for b in searches)


async def test_sync_area_with_no_nearby_depots_does_nothing(db):
    fake = FakeMarketFiyati(nearest=[])
    async with fake.client() as client:
        stats = await sync_area(db, client, keywords=["süt"], **AREA)
    assert stats.products_seen == 0
    assert [r.url.path for r in fake.requests] == ["/api/v2/nearest"]
