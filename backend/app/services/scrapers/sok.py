import re

from app.services.marketfiyati.schemas import SearchProduct
from app.services.scrapers.base import ChainScraper
from app.services.scrapers.html import parse_product_html

_PRODUCT_ID = re.compile(r"-p-(\d+)/?$")


class SokScraper(ChainScraper):
    """sokmarket.com.tr: fiyat sunucuda HTML'e yazılır, düz HTTP yeterli."""

    market_slug = "sok"
    market_name = "Şok"
    base_url = "https://www.sokmarket.com.tr"
    sitemap_url = "https://www.sokmarket.com.tr/sitemap/sitemap.xml"

    def wants_sitemap(self, url: str) -> bool:
        return "market-product" in url  # "ekstra" (gıda dışı online ürünler) atlanır

    def is_product_url(self, url: str) -> bool:
        return bool(_PRODUCT_ID.search(url))

    async def scrape_product(self, url: str) -> SearchProduct | None:
        parsed = parse_product_html(await self.get(url))
        if parsed is None:
            return None
        return self.listing(
            product_id=_PRODUCT_ID.search(url).group(1),
            title=parsed.title,
            brand=parsed.brand,
            price=parsed.price,
            image_url=parsed.image_url,
        )
