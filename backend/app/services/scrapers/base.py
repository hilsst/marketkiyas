import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from app.services.http import HttpError, PoliteClient
from app.services.marketfiyati.schemas import Depot, DepotPrice, SearchProduct

log = logging.getLogger(__name__)

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# Site üst üste bu kadar sayfayı reddederse (ör. bot kontrolü) tarama durur, zorlamaya devam edilmez
MAX_CONSECUTIVE_FAILURES = 5
_PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+),(\d{2})\s*(?:₺|TL)")


class ScrapeError(HttpError):
    pass


def parse_tl(text: str | None) -> Decimal | None:
    """'1.249,90 ₺' -> Decimal('1249.90'). Metindeki ilk TL fiyatını alır."""
    if not text:
        return None
    match = _PRICE_RE.search(text.replace("\xa0", " "))
    if not match:
        return None
    try:
        return Decimal(f"{match.group(1).replace('.', '')}.{match.group(2)}")
    except InvalidOperation:
        return None


def all_tl(text: str) -> list[Decimal]:
    return [d for d in (parse_tl(m.group(0)) for m in _PRICE_RE.finditer(text.replace("\xa0", " "))) if d]


def parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    """(alt sitemap'ler, sayfa url'leri)."""
    root = ET.fromstring(xml_text)
    locs = [el.text.strip() for el in root.iter(f"{_SITEMAP_NS}loc") if el.text]
    if root.tag == f"{_SITEMAP_NS}sitemapindex":
        return locs, []
    return [], locs


class ChainScraper(ABC):
    """Bir zincirin sitesinden ürün sayfalarını gezip fiyatları çıkarır."""

    market_slug: str
    market_name: str
    base_url: str
    sitemap_url: str

    def __init__(self, http: PoliteClient) -> None:
        self.http = http
        self._robots: RobotFileParser | None = None

    # --- robots.txt ---------------------------------------------------------------------

    async def robots(self) -> RobotFileParser:
        if self._robots is None:
            parser = RobotFileParser()
            try:
                text = (await self.http.fetch("GET", f"{self.base_url}/robots.txt")).text
                parser.parse(text.splitlines())
            except HttpError as exc:
                if exc.status_code and 400 <= exc.status_code < 500:
                    parser.parse([])  # robots.txt yok: her şey serbest
                else:
                    raise
            self._robots = parser
        return self._robots

    async def allowed(self, url: str) -> bool:
        return (await self.robots()).can_fetch(self.http.user_agent, url)

    async def get(self, url: str) -> str:
        if not await self.allowed(url):
            raise ScrapeError(f"robots.txt izin vermiyor: {url}")
        return (await self.http.fetch("GET", url)).text

    # --- sitemap ------------------------------------------------------------------------

    @abstractmethod
    def wants_sitemap(self, url: str) -> bool:
        """Sitemap index'te hangi alt sitemap'ler gezilsin (ör. sadece market ürünleri)."""

    @abstractmethod
    def is_product_url(self, url: str) -> bool: ...

    async def product_urls(self) -> AsyncIterator[str]:
        queue = [self.sitemap_url]
        seen: set[str] = set()
        while queue:
            sitemap = queue.pop(0)
            if sitemap in seen:
                continue
            seen.add(sitemap)
            children, pages = parse_sitemap(await self.get(sitemap))
            queue.extend(c for c in children if self.wants_sitemap(c))
            for page in pages:
                if self.is_product_url(page):
                    yield page

    # --- ürün sayfası -------------------------------------------------------------------

    @abstractmethod
    async def scrape_product(self, url: str) -> SearchProduct | None:
        """Sayfadan ürünü çıkarır; fiyat bulunamazsa None."""

    def online_depot(self) -> Depot:
        """Zincir siteleri şube değil zincir geneli (online) fiyat verir: tek sanal şube."""
        return Depot(
            id=f"{self.market_slug}-online",
            name=f"{self.market_name} (online fiyat)",
            market_name=self.market_slug,
            latitude=None,
            longitude=None,
        )

    def listing(
        self,
        *,
        product_id: str,
        title: str,
        brand: str | None,
        price: Decimal,
        image_url: str | None = None,
        volume: str | None = None,
    ) -> SearchProduct:
        return SearchProduct(
            id=f"{self.market_slug}:{product_id}",
            title=title,
            brand=brand,
            image_url=image_url,
            volume_or_weight=volume,
            categories=(),
            prices=(DepotPrice(self.online_depot(), price, None),),
        )

    async def scrape(self, limit: int | None = None) -> AsyncIterator[SearchProduct]:
        count = failures = 0
        async for url in self.product_urls():
            if limit is not None and count >= limit:
                return
            try:
                product = await self.scrape_product(url)
            except HttpError as exc:
                log.warning("%s: %s", url, exc)
                failures += 1
                if failures >= MAX_CONSECUTIVE_FAILURES:
                    raise ScrapeError(f"{self.market_name} üst üste {failures} sayfayı reddetti, tarama durduruldu") from exc
                continue
            failures = 0
            if product is None:
                log.info("fiyat bulunamadı: %s", url)
                continue
            count += 1
            yield product
