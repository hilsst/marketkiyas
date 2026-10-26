"""Komut satırı: marketfiyati.org.tr senkronizasyonu.

    python -m app.cli nearby --lat 40.99 --lon 29.03            # çevredeki şubeleri kaydet
    python -m app.cli sync --lat 40.99 --lon 29.03 --keywords süt ekmek
    python -m app.cli sync-selected                             # seçili şubelerin tüm ürünleri
    python -m app.cli sync-selected --every-hours 6             # sürekli çalışan worker
    python -m app.cli scrape --market sok --limit 100           # market sitesinden (Şok, A101)
    python -m app.cli seed-demo                                 # demo kataloğu + demo@marketkiyas.app
"""

import argparse
import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.marketfiyati.client import MarketFiyatiClient
from app.services.marketfiyati.ingest import (
    DEFAULT_KEYWORDS,
    refresh_nearby_stores,
    sync_area,
    sync_selected_stores,
)

from app.services.http import PoliteClient

log = logging.getLogger("marketkiyas.cli")

SCRAPERS = ("sok", "a101")


async def _nearby(args: argparse.Namespace) -> None:
    async with SessionLocal() as db, MarketFiyatiClient() as client:
        ids = await refresh_nearby_stores(db, client, args.lat, args.lon, args.distance)
        log.info("%d şube kaydedildi", len(ids))


async def _sync(args: argparse.Namespace) -> None:
    async with SessionLocal() as db, MarketFiyatiClient() as client:
        stats = await sync_area(
            db, client, latitude=args.lat, longitude=args.lon, distance_km=args.distance, keywords=args.keywords
        )
        log.info("bitti: %s", stats)


async def _sync_selected(args: argparse.Namespace) -> None:
    while True:
        async with SessionLocal() as db, MarketFiyatiClient() as client:
            if args.keywords:
                stats = await sync_selected_stores(db, client, keywords=args.keywords, categories=())
            else:
                stats = await sync_selected_stores(db, client)
            log.info("bitti: %s", stats)
        if not args.every_hours:
            return
        await asyncio.sleep(args.every_hours * 3600)


async def _scrape_once(market: str, limit: int | None) -> None:
    from app.services.scrapers.run import sync_chain
    from app.services.scrapers.sok import SokScraper

    async with SessionLocal() as db, PoliteClient(min_interval=settings.scraper_min_interval_seconds) as http:
        if market == "sok":
            stats = await sync_chain(db, SokScraper(http), limit)
        else:
            from app.services.scrapers.a101 import A101Scraper, PlaywrightRenderer

            async with PlaywrightRenderer(
                http.user_agent, executable_path=settings.chromium_executable_path
            ) as render:
                stats = await sync_chain(db, A101Scraper(http, render), limit)
        log.info("%s bitti: %s", market, stats)


async def _scrape(args: argparse.Namespace) -> None:
    markets = SCRAPERS if args.market == "all" else (args.market,)
    while True:
        for market in markets:
            try:
                await _scrape_once(market, args.limit)
            except Exception:
                log.exception("%s taraması başarısız", market)
        if not args.every_hours:
            return
        await asyncio.sleep(args.every_hours * 3600)


async def _seed_demo(args: argparse.Namespace) -> None:
    from app.services.demo_seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo

    async with SessionLocal() as db:
        stats = await seed_demo(db)
    log.info("demo verisi: %s (giriş: %s / %s)", stats, DEMO_EMAIL, DEMO_PASSWORD)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    def area(p: argparse.ArgumentParser) -> None:
        p.add_argument("--lat", type=float, required=True)
        p.add_argument("--lon", type=float, required=True)
        p.add_argument("--distance", type=int, default=settings.default_search_distance_km)

    p = sub.add_parser("nearby", help="çevredeki şubeleri kaydet")
    area(p)
    p.set_defaults(func=_nearby)

    p = sub.add_parser("sync", help="bir bölgenin fiyatlarını çek")
    area(p)
    p.add_argument("--keywords", nargs="+", default=list(DEFAULT_KEYWORDS))
    p.set_defaults(func=_sync)

    p = sub.add_parser("sync-selected", help="kullanıcıların seçtiği şubelerin fiyatlarını çek")
    p.add_argument("--keywords", nargs="+", help="verilmezse şubelerin tüm ürünleri (bütün kategoriler) çekilir")
    p.add_argument("--every-hours", type=float, default=0, help="0 = bir kez çalış")
    p.set_defaults(func=_sync_selected)

    p = sub.add_parser("scrape", help="market sitelerinden fiyat topla (robots.txt'ye uyar)")
    p.add_argument("--market", choices=[*SCRAPERS, "all"], default="all")
    p.add_argument("--limit", type=int, default=None, help="market başına en fazla ürün")
    p.add_argument("--every-hours", type=float, default=0, help="0 = bir kez çalış")
    p.set_defaults(func=_scrape)

    p = sub.add_parser("seed-demo", help="demo kataloğunu ve örnek listeleri yükle (gerçek fiyat değil)")
    p.set_defaults(func=_seed_demo)

    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
