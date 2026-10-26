import json
from decimal import Decimal as D

import httpx
import pytest
from sqlalchemy import func, select

from app.models import GroupMember, Market, PriceHistory, Product, ProductGroup, Store, StorePrice, Unit
from app.services.marketfiyati.client import MarketFiyatiClient, MarketFiyatiError
from app.services.marketfiyati.ingest import market_slug, refresh_nearby_stores, sync_area
from app.services.marketfiyati.schemas import SearchPage
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


async def test_client_retries_rotates_user_agent_and_respects_retry_after(monkeypatch):
    calls = []
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("app.services.marketfiyati.client.asyncio.sleep", fake_sleep)

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
    assert len(calls) == 3 and len(set(calls)) == 3  # her denemede farklı User-Agent
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

    monkeypatch.setattr("app.services.marketfiyati.client.asyncio.sleep", no_sleep)
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
