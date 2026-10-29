from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.models import AktuelItem
from app.services.aktuel import (
    BimPeriod,
    parse_bim_periods,
    parse_bim_products,
    parse_period,
    parse_sok_products,
    save_aktuel,
    sok_total_pages,
    sync_aktuel,
)
from app.services.http import PoliteClient

SITES = Path(__file__).parent / "fixtures" / "sites"
BIM_PAGE = (SITES / "bim_aktuel.html").read_text(encoding="utf-8")
SOK_PAGE = (SITES / "sok_firsatlar.html").read_text(encoding="utf-8")
TODAY = date(2026, 10, 29)


@pytest.mark.parametrize(
    ("label", "today", "expected"),
    [
        ("28 Ekim Çarşamba", TODAY, (date(2026, 10, 28), None)),
        ("04 Kasım Çarşamba", TODAY, (date(2026, 11, 4), None)),
        ("24-30 Ekim", TODAY, (date(2026, 10, 24), date(2026, 10, 30))),
        ("30 Ekim - 5 Kasım", TODAY, (date(2026, 10, 30), date(2026, 11, 5))),
        ("2 Ocak Cuma", date(2026, 12, 30), (date(2027, 1, 2), None)),
        ("28 Aralık - 3 Ocak", date(2027, 1, 1), (date(2026, 12, 28), date(2027, 1, 3))),
        ("Haftanın Fırsatları", TODAY, (None, None)),
    ],
)
def test_parse_period(label, today, expected):
    assert parse_period(label, today) == expected


def test_bim_menu_lists_aktuel_and_indirim_dates():
    assert [(p.key, p.label, p.kind) for p in parse_bim_periods(BIM_PAGE)] == [
        ("1693", "28 Ekim Çarşamba", "aktuel"),
        ("1701", "24-30 Ekim", "indirim"),
        ("1698", "04 Kasım Çarşamba", "aktuel"),
    ]


def test_bim_product_cards():
    items = parse_bim_products(BIM_PAGE, BimPeriod("1701", "24-30 Ekim", "indirim"), TODAY)
    assert len(items) == 2  # fiyatsız kart atlanır
    rice, bag = items
    assert rice.source_key == "1701:72418"
    assert (rice.title, rice.brand, rice.quantity_text) == ("Yerli Pilavlık Pirinç", "Efsane", "2,5 kg")
    assert (rice.price, rice.old_price) == (D("132.50"), D("147.50"))
    assert (rice.starts_on, rice.ends_on) == (date(2026, 10, 24), date(2026, 10, 30))
    assert rice.source_url == "https://www.bim.com.tr/aktuel-urunler/yerli-pilavlik-pirinc-24-10/aktuel.aspx"
    assert bag.title == "LEDLİ MOTOSİKLET SIRT ÇANTASI"
    assert (bag.brand, bag.quantity_text, bag.old_price) == (None, None, None)
    assert bag.price == D("4990.00")
    assert bag.details == "Kişiselleştirilebilir Led ekranlar"


def test_sok_product_cards():
    items = parse_sok_products(SOK_PAGE)
    assert [(i.source_key, i.title, i.price, i.old_price) for i in items] == [
        ("809394", "Lezita Piliç Salam 500 g", D("49.90"), None),
        ("722372", "Bizim Bitkisel Yağlı Kremsos %20 Yağlı 200 ml", D("26.90"), D("36.90")),
    ]
    assert items[0].image_url.startswith("https://images.ceptesok.com/")
    assert items[0].source_url == "https://www.sokmarket.com.tr/lezita-pilic-salam-500-g-p-809394"
    assert sok_total_pages(SOK_PAGE) == 6


class FakeSites:
    def __init__(self, sok_robots: str = "User-agent: *\nDisallow: /arama\n") -> None:
        self.sok_robots = sok_robots
        self.bim_page = BIM_PAGE
        self.sok_page = SOK_PAGE
        self.requested: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requested.append(url)
        if url == "https://www.bim.com.tr/robots.txt":
            return httpx.Response(404)
        if url == "https://www.sokmarket.com.tr/robots.txt":
            return httpx.Response(200, text=self.sok_robots)
        if url.startswith("https://www.bim.com.tr/Categories/100/aktuel-urunler.aspx"):
            return httpx.Response(200, text=self.bim_page)
        if url.startswith("https://www.sokmarket.com.tr/haftanin-firsatlari-market-sgrp-146401"):
            return httpx.Response(200, text=self.sok_page)
        return httpx.Response(404)

    def client(self) -> PoliteClient:
        return PoliteClient(transport=httpx.MockTransport(self.handler), min_interval=0, max_retries=0)


async def test_sync_saves_both_chains_and_follows_sok_pages(db):
    sites = FakeSites()
    async with sites.client() as http:
        stats = await sync_aktuel(db, http, today=TODAY)
    # BİM: 3 tarih sayfası x 2 kart; Şok: 6 sayfa aynı 2 ürünü döndürür, tekrarlar birleşir
    assert stats == {"bim": 6, "sok": 2}
    assert sum("haftanin-firsatlari" in u for u in sites.requested) == 6
    labels = set((await db.scalars(select(AktuelItem.period_label).where(AktuelItem.market_slug == "bim"))).all())
    assert labels == {"28 Ekim Çarşamba", "24-30 Ekim", "04 Kasım Çarşamba"}


async def test_sync_drops_items_gone_from_brochure_but_keeps_all_when_page_is_empty(db):
    sites = FakeSites()
    async with sites.client() as http:
        await sync_aktuel(db, http, today=TODAY)
        sites.sok_page = SOK_PAGE.replace("Lezita", "XX").split('<div class="PLPProductListing_PLPCardParent', 2)
        sites.sok_page = '<div class="PLPProductListing_PLPCardParent'.join(sites.sok_page[::2])  # yalnızca 2. kart
        await sync_aktuel(db, http, markets=("sok",), today=TODAY)
        remaining = (await db.scalars(select(AktuelItem.source_key).where(AktuelItem.market_slug == "sok"))).all()
        assert remaining == ["722372"]

        sites.sok_page = "<html>site değişti</html>"
        assert await sync_aktuel(db, http, markets=("sok",), today=TODAY) == {"sok": 0}
        assert len((await db.scalars(select(AktuelItem).where(AktuelItem.market_slug == "sok"))).all()) == 1


async def test_sync_obeys_robots_txt(db):
    sites = FakeSites(sok_robots="User-agent: *\nDisallow: /haftanin-firsatlari\n")
    async with sites.client() as http:
        assert await sync_aktuel(db, http, markets=("sok",), today=TODAY) == {"sok": 0}
    assert not any("haftanin-firsatlari" in u for u in sites.requested)


async def test_api_lists_current_then_upcoming_and_hides_expired(client, db):
    today = date.today()
    base = dict(title="Ürün", price=D("10"), period_key="k", brand=None, quantity_text=None, details=None,
                old_price=None, image_url=None, source_url=None)
    from app.services.aktuel import ParsedAktuel

    def item(key, label, starts, ends=None):
        return ParsedAktuel(source_key=key, period_label=label, starts_on=starts, ends_on=ends, **base)

    await save_aktuel(db, "bim", [
        item("eski", "geçen hafta", today - timedelta(days=7)),
        item("yeni", "bugün", today),
        item("yakinda", "gelecek hafta", today + timedelta(days=5)),
        item("bitti", "indirim", today - timedelta(days=8), today - timedelta(days=1)),
    ])
    await save_aktuel(db, "sok", [item("hf", "Haftanın Fırsatları", None)])

    body = (await client.get("/api/aktuel")).json()
    assert [(i["market_slug"], i["period_label"], i["upcoming"]) for i in body["items"]] == [
        ("bim", "bugün", False),
        ("sok", "Haftanın Fırsatları", False),
        ("bim", "geçen hafta", False),
        ("bim", "gelecek hafta", True),
    ]
    sources = {s["slug"]: s for s in body["sources"]}
    assert sources["bim"]["item_count"] == 3 and sources["bim"]["automatic"]
    assert sources["a101"]["item_count"] == 0 and not sources["a101"]["automatic"]

    only_sok = (await client.get("/api/aktuel", params={"market": "sok"})).json()["items"]
    assert [i["title"] for i in only_sok] == ["Ürün"]
