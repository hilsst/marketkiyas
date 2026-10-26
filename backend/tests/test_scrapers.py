from decimal import Decimal as D
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.models import Market, Product, ProductGroup, Store, StorePrice
from app.services.http import PoliteClient
from app.services.scrapers.a101 import A101Scraper
from app.services.scrapers.base import ScrapeError, parse_tl
from app.services.scrapers.html import parse_product_html
from app.services.scrapers.run import sync_chain
from app.services.scrapers.sok import SokScraper

SITES = Path(__file__).parent / "fixtures" / "sites"
SOK_PAGE = (SITES / "sok_product.html").read_text(encoding="utf-8")
A101_PAGE = (SITES / "a101_product_rendered.html").read_text(encoding="utf-8")

SOK_ROBOTS = "User-agent: *\nDisallow: /arama\n"
SOK_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://www.sokmarket.com.tr/sitemap/ekstra-product_1.xml</loc></sitemap>
  <sitemap><loc>https://www.sokmarket.com.tr/sitemap/market-product_1.xml</loc></sitemap>
</sitemapindex>"""
SOK_PRODUCTS = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.sokmarket.com.tr/ulker-kekstra-jolebol-portakalli-xl-70-g-p-469843</loc></url>
  <url><loc>https://www.sokmarket.com.tr/arama?q=x-p-1</loc></url>
  <url><loc>https://www.sokmarket.com.tr/kampanyalar</loc></url>
  <url><loc>https://www.sokmarket.com.tr/fiyatsiz-urun-p-2</loc></url>
</urlset>"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [("13,90₺", D("13.90")), ("1.249,90 ₺", D("1249.90")), ("Fiyat: 7,50 TL", D("7.50")), ("yok", None)],
)
def test_parse_tl(text, expected):
    assert parse_tl(text) == expected


def test_parse_sok_markup_takes_discounted_price_from_product_box():
    parsed = parse_product_html(SOK_PAGE)
    assert parsed.title == "Ülker Kekstra Jölebol Portakallı Xl 70 g"
    assert parsed.brand == "ÜLKER"
    # 16,50 eski fiyat; 13,00 aşağıdaki "benzer ürünler" kartı, sepet 0,00: hiçbiri bu ürünün fiyatı değil
    assert parsed.price == D("13.90")
    assert parsed.image_url == "https://images.sokmarket.com.tr/469843.jpg"


def test_parse_jsonld_first():
    parsed = parse_product_html(A101_PAGE)
    assert (parsed.title, parsed.brand, parsed.price) == ("Doyfarm Piliç Salam 850 G", "DOYFARM", D("33.50"))


def test_parse_visible_price_when_jsonld_price_is_untrusted():
    parsed = parse_product_html(A101_PAGE, trust_jsonld_price=False)
    assert (parsed.title, parsed.brand, parsed.price) == ("Doyfarm Piliç Salam 850 G", "DOYFARM", D("189.50"))
    assert parsed.image_url.startswith("https://cdn2.a101.com.tr/")


def test_untrusted_jsonld_price_is_not_used_when_price_box_is_empty():
    page = A101_PAGE.replace('<span class="product-price">189,50 ₺</span>', '<div class="hHMyUW_price"></div>')
    assert parse_product_html(page, trust_jsonld_price=False) is None


def test_page_without_price_is_skipped():
    assert parse_product_html("<html><h1>Ürün</h1><p>Stokta yok</p></html>") is None


class FakeSite:
    def __init__(self, pages: dict[str, tuple[int, str]]) -> None:
        self.pages = pages
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self.pages.get(str(request.url), (404, ""))
        return httpx.Response(status, text=body)

    def http(self) -> PoliteClient:
        return PoliteClient(transport=httpx.MockTransport(self.handler), min_interval=0, max_retries=0)


def sok_site() -> FakeSite:
    base = "https://www.sokmarket.com.tr"
    return FakeSite(
        {
            f"{base}/robots.txt": (200, SOK_ROBOTS),
            f"{base}/sitemap/sitemap.xml": (200, SOK_INDEX),
            f"{base}/sitemap/market-product_1.xml": (200, SOK_PRODUCTS),
            f"{base}/ulker-kekstra-jolebol-portakalli-xl-70-g-p-469843": (200, SOK_PAGE),
            f"{base}/fiyatsiz-urun-p-2": (200, "<html><h1>Fiyatsız</h1></html>"),
        }
    )


async def test_sok_scraper_follows_sitemap_and_robots():
    site = sok_site()
    async with site.http() as http:
        products = [p async for p in SokScraper(http).scrape()]

    assert [p.id for p in products] == ["sok:469843"]
    assert products[0].prices[0].price == D("13.90")
    assert products[0].prices[0].depot.id == "sok-online"
    paths = [r.url.path for r in site.requests]
    assert "/sitemap/ekstra-product_1.xml" not in paths  # gıda dışı sitemap gezilmez
    assert not any(p.startswith("/arama") for p in paths)  # robots.txt yasağı
    assert all(r.headers["User-Agent"].startswith("MarketKiyas/") for r in site.requests)


class FakeBrowser:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.opened: list[str] = []

    async def __call__(self, url: str) -> str:
        self.opened.append(url)
        return A101_PAGE

    async def fetch_text(self, url: str) -> tuple[int, str]:
        self.opened.append(url)
        return (200, self.files[url]) if url in self.files else (404, "")


async def test_a101_scraper_uses_browser_and_respects_robots():
    base = "https://www.a101.com.tr"
    allowed = f"{base}/kapida/et-tavuk-sarkuteri/doyfarm-pilic-salam-850-g_p-11000066"
    blocked = f"{base}/kapida/arama?x_p-1"
    # Site düz HTTP'ye sitemap vermiyor (403); sadece robots.txt düz istekle okunur
    site = FakeSite({f"{base}/robots.txt": (200, "User-agent: *\nDisallow: /kapida/arama?\n")})
    browser = FakeBrowser(
        {
            f"{base}/sitemap.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>{base}/sitemaps/products-ecom-1.xml</loc></sitemap>
  <sitemap><loc>{base}/sitemaps/products-kapida-1.xml</loc></sitemap>
</sitemapindex>""",
            f"{base}/sitemaps/products-kapida-1.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{allowed}</loc></url><url><loc>{blocked}</loc></url><url><loc>{base}/kapida/kampanyalar</loc></url>
</urlset>""",
        }
    )

    async with site.http() as http:
        products = [p async for p in A101Scraper(http, browser).scrape()]

    assert browser.opened == [f"{base}/sitemap.xml", f"{base}/sitemaps/products-kapida-1.xml", allowed]
    assert [r.url.path for r in site.requests] == ["/robots.txt"]
    assert [p.id for p in products] == ["a101:11000066"]
    assert products[0].prices[0].price == D("189.50")  # JSON-LD'deki eski 33.50 değil


async def test_sync_chain_ingests_into_online_store(db):
    site = sok_site()
    async with site.http() as http:
        stats = await sync_chain(db, SokScraper(http))
    assert stats.products_seen == 1

    store = await db.scalar(select(Store).where(Store.external_id == "sok-online"))
    assert store.latitude is None and store.name == "Şok (online fiyat)"
    product = await db.scalar(select(Product).where(Product.external_id == "sok:469843"))
    assert product.current_price == D("13.90") and product.brand == "ÜLKER"
    assert (await db.scalar(select(Market.slug).where(Market.id == product.market_id))) == "sok"
    assert await db.scalar(select(StorePrice.price).where(StorePrice.product_id == product.id)) == D("13.90")
    group = await db.scalar(select(ProductGroup))
    assert group.name == "Kekstra Jölebol Portakallı Xl 70 g" and group.normalized_name.endswith("70g")


async def test_online_store_is_offered_in_nearby(client, auth_headers, db):
    from app.api.routes.stores import get_marketfiyati_client
    from app.main import app
    from tests.marketfiyati_fake import FakeMarketFiyati

    site = sok_site()
    async with site.http() as http:
        await sync_chain(db, SokScraper(http))

    fake = FakeMarketFiyati()
    fake.fail_with = 404  # marketfiyati erişilemez

    async def _client():
        async with fake.client() as c:
            yield c

    app.dependency_overrides[get_marketfiyati_client] = _client
    r = await client.get("/api/stores/nearby", params={"lat": 40.98, "lon": 29.02}, headers=auth_headers)
    assert [s["name"] for s in r.json()] == ["Şok (online fiyat)"]


async def test_scrape_stops_when_site_keeps_refusing():
    base = "https://www.sokmarket.com.tr"
    urls = "".join(f"<url><loc>{base}/urun-{i}-p-{i}</loc></url>" for i in range(1, 9))
    site = FakeSite(
        {
            f"{base}/robots.txt": (200, SOK_ROBOTS),
            f"{base}/sitemap/sitemap.xml": (200, SOK_INDEX),
            f"{base}/sitemap/market-product_1.xml": (
                200,
                f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
            ),
        }
    )  # ürün sayfaları 404
    async with site.http() as http:
        with pytest.raises(ScrapeError, match="üst üste 5"):
            [p async for p in SokScraper(http).scrape()]
    assert sum("-p-" in r.url.path for r in site.requests) == 5
