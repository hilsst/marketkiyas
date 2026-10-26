"""Komut satırı: marketfiyati.org.tr senkronizasyonu.

    python -m app.cli nearby --lat 40.99 --lon 29.03            # çevredeki şubeleri kaydet
    python -m app.cli sync --lat 40.99 --lon 29.03 --keywords süt ekmek
    python -m app.cli sync-selected                             # kullanıcıların seçtiği şubeler
    python -m app.cli sync-selected --every-hours 6             # sürekli çalışan worker
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

log = logging.getLogger("marketkiyas.cli")


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
            stats = await sync_selected_stores(db, client, keywords=args.keywords)
            log.info("bitti: %s", stats)
        if not args.every_hours:
            return
        await asyncio.sleep(args.every_hours * 3600)


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
    p.add_argument("--keywords", nargs="+", default=list(DEFAULT_KEYWORDS))
    p.add_argument("--every-hours", type=float, default=0, help="0 = bir kez çalış")
    p.set_defaults(func=_sync_selected)

    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
