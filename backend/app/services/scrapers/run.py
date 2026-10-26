import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.marketfiyati.ingest import Ingestor, SyncStats
from app.services.scrapers.base import ChainScraper

log = logging.getLogger(__name__)

COMMIT_EVERY = 50


async def sync_chain(db: AsyncSession, scraper: ChainScraper, limit: int | None = None) -> SyncStats:
    """Zincirin sitesindeki ürünleri gezip marketfiyati ile aynı aktarım hattından geçirir.

    Fiyatlar zincirin sanal "online" şubesine yazılır; gruplama ve fiyat geçmişi aynı şekilde çalışır.
    """
    ingestor = Ingestor(db)
    async for product in scraper.scrape(limit=limit):
        await ingestor.ingest_product(product)
        if ingestor.stats.products_seen % COMMIT_EVERY == 0:
            await db.commit()
            log.info("%s: %d ürün", scraper.market_slug, ingestor.stats.products_seen)
    await db.commit()
    return ingestor.stats
