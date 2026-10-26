import logging
import re
from typing import Protocol

from app.services.http import PoliteClient
from app.services.marketfiyati.schemas import SearchProduct
from app.services.scrapers.base import ChainScraper, ScrapeError
from app.services.scrapers.html import parse_product_html

log = logging.getLogger(__name__)

_PRODUCT_ID = re.compile(r"_p-(\d+)/?$")
# Fiyat yüklenene kadar yerinde duran boş kutu
_PRICE_SKELETON = '[data-testid="kapida-price-skeleton"]'


class Renderer(Protocol):
    async def __call__(self, url: str) -> str:
        """Sayfayı JavaScript çalıştırarak açar, son HTML'i döner."""

    async def fetch_text(self, url: str) -> tuple[int, str]:
        """Dosyayı (ör. sitemap) tarayıcıyla indirir: (HTTP durumu, gövde)."""


class PlaywrightRenderer:
    """Fiyatı JavaScript ile yükleyen sayfalar için başsız Chromium. Kendini MarketKiyas olarak tanıtır."""

    def __init__(self, user_agent: str, timeout_ms: int = 30_000, executable_path: str | None = None) -> None:
        self.user_agent = user_agent
        self.executable_path = executable_path
        self.timeout_ms = timeout_ms
        self._pw = self._browser = self._context = None

    async def __aenter__(self) -> "PlaywrightRenderer":
        from playwright.async_api import async_playwright  # opsiyonel bağımlılık (worker imajı)

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(executable_path=self.executable_path)
        # Tek oturum: sayfalar arası çerezler normal bir tarayıcıdaki gibi korunur
        self._context = await self._browser.new_context(user_agent=self.user_agent)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def __call__(self, url: str) -> str:
        page = await self._context.new_page()
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
            if response is not None and response.status >= 400:
                # ör. 403 "Just a moment..." bot kontrolü: aşmaya çalışılmaz, sayfa atlanır
                raise ScrapeError(f"GET {url} -> HTTP {response.status}", response.status)
            try:
                await page.wait_for_selector(_PRICE_SKELETON, state="detached", timeout=10_000)
            except Exception:  # fiyat gelmedi; parser fiyatsız sayfayı atlar
                log.info("fiyat yüklenmedi: %s", url)
            return await page.content()
        finally:
            await page.close()

    async def fetch_text(self, url: str) -> tuple[int, str]:
        page = await self._context.new_page()
        try:
            response = await page.goto(url, timeout=self.timeout_ms)
            if response is None:
                return 0, ""
            return response.status, await response.text()
        finally:
            await page.close()


class A101Scraper(ChainScraper):
    """a101.com.tr "Kapıda" (market ürünleri): fiyat istemci tarafında yüklenir, sayfa render edilir.

    Site düz HTTP isteklerine (sitemap dahil) 403 döndüğü için robots.txt dışındaki her şey
    tarayıcıyla açılır. Sayfadaki JSON-LD fiyatı eski olduğundan fiyat görünen kutudan okunur.
    """

    market_slug = "a101"
    market_name = "A101"
    base_url = "https://www.a101.com.tr"
    sitemap_url = "https://www.a101.com.tr/sitemap.xml"

    def __init__(self, http: PoliteClient, render: Renderer) -> None:
        super().__init__(http)
        self.render = render

    def wants_sitemap(self, url: str) -> bool:
        return "products-kapida" in url

    async def get(self, url: str) -> str:
        if not await self.allowed(url):
            raise ScrapeError(f"robots.txt izin vermiyor: {url}")
        await self.http.throttle()
        status, text = await self.render.fetch_text(url)
        if not 200 <= status < 300:
            raise ScrapeError(f"GET {url} -> HTTP {status}", status)
        return text

    def is_product_url(self, url: str) -> bool:
        return "/kapida/" in url and bool(_PRODUCT_ID.search(url))

    async def scrape_product(self, url: str) -> SearchProduct | None:
        if not await self.allowed(url):
            return None
        await self.http.throttle()  # render da aynı hız sınırına tabi
        parsed = parse_product_html(await self.render(url), trust_jsonld_price=False)
        if parsed is None:
            return None
        return self.listing(
            product_id=_PRODUCT_ID.search(url).group(1),
            title=parsed.title,
            brand=parsed.brand,
            price=parsed.price,
            image_url=parsed.image_url,
        )
