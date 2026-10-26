import re
from collections.abc import Awaitable, Callable

from app.services.http import PoliteClient
from app.services.marketfiyati.schemas import SearchProduct
from app.services.scrapers.base import ChainScraper
from app.services.scrapers.html import parse_product_html

_PRODUCT_ID = re.compile(r"_p-(\d+)/?$")

Renderer = Callable[[str], Awaitable[str]]


class PlaywrightRenderer:
    """Fiyatı JavaScript ile yükleyen sayfalar için başsız Chromium. Kendini MarketKiyas olarak tanıtır."""

    def __init__(self, user_agent: str, timeout_ms: int = 30_000) -> None:
        self.user_agent = user_agent
        self.timeout_ms = timeout_ms
        self._pw = self._browser = None

    async def __aenter__(self) -> "PlaywrightRenderer":
        from playwright.async_api import async_playwright  # opsiyonel bağımlılık (worker imajı)

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def __call__(self, url: str) -> str:
        page = await self._browser.new_page(user_agent=self.user_agent)
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
            return await page.content()
        finally:
            await page.close()


class A101Scraper(ChainScraper):
    """a101.com.tr "Kapıda" (market ürünleri): fiyat istemci tarafında yüklenir, sayfa render edilir."""

    market_slug = "a101"
    market_name = "A101"
    base_url = "https://www.a101.com.tr"
    sitemap_url = "https://www.a101.com.tr/sitemap.xml"

    def __init__(self, http: PoliteClient, render: Renderer) -> None:
        super().__init__(http)
        self.render = render

    def wants_sitemap(self, url: str) -> bool:
        return "products-kapida" in url

    def is_product_url(self, url: str) -> bool:
        return "/kapida/" in url and bool(_PRODUCT_ID.search(url))

    async def scrape_product(self, url: str) -> SearchProduct | None:
        if not await self.allowed(url):
            return None
        await self.http.throttle()  # render da aynı hız sınırına tabi
        parsed = parse_product_html(await self.render(url))
        if parsed is None:
            return None
        return self.listing(
            product_id=_PRODUCT_ID.search(url).group(1),
            title=parsed.title,
            brand=parsed.brand,
            price=parsed.price,
            image_url=parsed.image_url,
        )
