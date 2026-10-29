"""Marketlerin aktüel (broşür) ürünlerini sitelerinden toplar.

- BİM: bim.com.tr "Aktüel Ürünler" sayfası. Menüde her broşürün tarihi var ("28 Ekim Çarşamba",
  indirimler için "24-30 Ekim"); her tarih ayrı sayfa (?Bim_AktuelTarihKey=...).
- Şok: sokmarket.com.tr "Haftanın Fırsatları" ürün grubu (sayfa sayfa, 20'şer ürün).
- A101 otomatik erişim istemediği için toplanmaz; Migros/CarrefourSA henüz denenmedi. Uygulamada
  bunlar için marketin kendi sitesine bağlantı gösterilir (AKTUEL_SOURCES).

Kurallar fiyat toplayıcılarla aynı: kibar istemci (app/services/http.py), robots.txt'ye uyulur,
bot kontrolü atlatılmaz. Bir kaynak hiç ürün döndürmezse (site değişti, erişim yok) eldeki
aktüeller silinmez; böylece uygulama boş kalmaz.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup, Tag
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AktuelItem
from app.services.http import HttpError, PoliteClient
from app.services.scrapers.base import parse_tl

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AktuelSource:
    slug: str
    name: str
    url: str  # marketin kendi aktüel sayfası (uygulamada "Sitede gör")
    automatic: bool  # True: ürünleri biz topluyoruz; False: yalnızca bağlantı


AKTUEL_SOURCES: tuple[AktuelSource, ...] = (
    AktuelSource("bim", "BİM", "https://www.bim.com.tr/Categories/100/aktuel-urunler.aspx", True),
    AktuelSource("sok", "Şok", "https://www.sokmarket.com.tr/haftanin-firsatlari-market-sgrp-146401", True),
    AktuelSource("a101", "A101", "https://www.a101.com.tr", False),
    AktuelSource("migros", "Migros", "https://www.migros.com.tr", False),
    AktuelSource("carrefour", "CarrefourSA", "https://www.carrefoursa.com", False),
)


@dataclass
class ParsedAktuel:
    source_key: str
    period_key: str
    period_label: str
    starts_on: date | None
    ends_on: date | None
    title: str
    brand: str | None
    quantity_text: str | None
    details: str | None
    price: Decimal
    old_price: Decimal | None
    image_url: str | None
    source_url: str | None


def _text(node: Tag | None) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ")).strip() if node else ""


# --- tarih ------------------------------------------------------------------------------

_MONTHS = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}
_DAY_MONTH = re.compile(r"(\d{1,2})\s*([A-Za-zÇĞİÖŞÜçğıöşü]+)?")


def _month(word: str | None) -> int | None:
    return _MONTHS.get(word.replace("I", "ı").replace("İ", "i").lower()) if word else None


def _near_year(month: int, day: int, today: date) -> date | None:
    """Yılsız tarih ("28 Ekim"): bugüne en yakın yıl (Aralık'ta "2 Ocak" gelecek yıl olur)."""
    candidates = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            pass
    return min(candidates, key=lambda d: abs((d - today).days), default=None)


def parse_period(label: str, today: date) -> tuple[date | None, date | None]:
    """'28 Ekim Çarşamba' -> (28 Ekim, None); '24-30 Ekim' -> (24 Ekim, 30 Ekim);
    '30 Ekim - 5 Kasım' -> (30 Ekim, 5 Kasım). Okunamazsa (None, None)."""
    parts = [p.strip() for p in label.split("-", 1)]
    found = []
    for part in parts:
        m = _DAY_MONTH.search(part)
        if not m:
            return None, None
        found.append((int(m.group(1)), _month(m.group(2))))
    end_month = found[-1][1]
    if end_month is None:
        return None, None
    try:
        end = _near_year(end_month, found[-1][0], today)
        if len(found) == 1 or end is None:
            return end, None
        day, month = found[0]
        start = date(end.year, month or end_month, day)
        if start > end:  # "28 Aralık - 3 Ocak"
            start = start.replace(year=end.year - 1)
    except ValueError:
        return None, None
    return start, end


# --- BİM --------------------------------------------------------------------------------

BIM_BASE = "https://www.bim.com.tr"
BIM_AKTUEL = f"{BIM_BASE}/Categories/100/aktuel-urunler.aspx"
_BIM_KEY = re.compile(r"Bim_AktuelTarihKey=(\d+)")


@dataclass
class BimPeriod:
    key: str
    label: str
    kind: str  # "aktuel" (tek gün başlar, stoklarla sınırlı) ya da "indirim" (tarih aralığı)


def parse_bim_periods(html: str) -> list[BimPeriod]:
    """Üst menüdeki tablo: 1. sütun AKTÜEL ÜRÜNLER, 2. sütun İNDİRİM."""
    soup = BeautifulSoup(html, "html.parser")
    menu = soup.select_one(".aktuelsubmenu table") or soup
    periods: dict[str, BimPeriod] = {}
    for row in menu.find_all("tr"):
        for column, cell in enumerate(row.find_all("td")):
            link = cell.find("a", href=_BIM_KEY)
            label = _text(link)
            if link and label:
                key = _BIM_KEY.search(link["href"]).group(1)
                periods.setdefault(key, BimPeriod(key, label, "indirim" if column == 1 else "aktuel"))
    if not periods:  # menü yapısı değiştiyse sayfadaki tüm tarih bağlantıları
        for link in soup.find_all("a", href=_BIM_KEY):
            if label := _text(link):
                key = _BIM_KEY.search(link["href"]).group(1)
                periods.setdefault(key, BimPeriod(key, label, "aktuel"))
    return list(periods.values())


def _bim_price(area: Tag | None) -> Decimal | None:
    """'<div class="text quantify">4.990,</div><span class="number">00</span>' -> 4990.00"""
    if area is None:
        return None
    whole = _text(area.select_one(".quantify")).rstrip(",").strip()
    cents = _text(area.select_one(".kusurArea .number")) or "00"
    return parse_tl(f"{whole},{cents} ₺") if whole else None


def parse_bim_products(html: str, period: BimPeriod, today: date) -> list[ParsedAktuel]:
    soup = BeautifulSoup(html, "html.parser")
    starts_on, ends_on = parse_period(period.label, today)
    items = []
    for card in soup.select(".productArea .product"):
        title = _text(card.select_one(".title"))
        price = _bim_price(card.select_one(".buttonArea a.gButton"))
        if not title or not price:
            continue
        old = card.select_one(".buttonArea .strikethrough")
        old_price = parse_tl(f"{_text(old.select_one('.quantify'))} ₺") if old else None
        link = card.select_one(".imageArea a[href]")
        share = card.select_one(".shareArea a[data-id]")
        image = card.select_one(".imageArea img[src]")
        quantity = _text(card.select_one(".gramajadet")).lstrip("•").strip()
        details = "\n".join(t for li in card.select(".textArea li .text") if (t := _text(li)))
        url = urljoin(BIM_BASE, link["href"]) if link else None
        ident = share["data-id"] if share else urlsplit(url or title).path
        items.append(
            ParsedAktuel(
                source_key=f"{period.key}:{ident}",
                period_key=period.key,
                period_label=period.label,
                starts_on=starts_on,
                ends_on=ends_on,
                title=title,
                brand=_text(card.select_one(".subTitle")) or None,
                quantity_text=quantity or None,
                details=details or None,
                price=price,
                old_price=old_price if old_price and old_price > price else None,
                image_url=image["src"] if image else None,
                source_url=url,
            )
        )
    return items


# --- Şok --------------------------------------------------------------------------------

SOK_BASE = "https://www.sokmarket.com.tr"
SOK_FIRSATLAR = f"{SOK_BASE}/haftanin-firsatlari-market-sgrp-146401"
SOK_PERIOD = ("haftanin-firsatlari", "Haftanın Fırsatları")
_SOK_PAGES = re.compile(r'\\?"totalPages\\?":(\d+)')
_SOK_ID = re.compile(r"-p-(\d+)")
SOK_MAX_PAGES = 15


def sok_total_pages(html: str) -> int:
    m = _SOK_PAGES.search(html)
    return min(int(m.group(1)), SOK_MAX_PAGES) if m else 1


def parse_sok_products(html: str) -> list[ParsedAktuel]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select('[class*="PLPCardParent"]'):
        link = card.find("a", href=_SOK_ID)
        title = _text(card.find("h2"))
        price_tag = card.select_one('[data-testid="discountedPrice"]')
        regular_tag = card.select_one('[data-testid="price"]')
        price = parse_tl(_text(price_tag or regular_tag))
        if not link or not title or not price:
            continue
        regular = parse_tl(_text(regular_tag)) if price_tag and regular_tag else None
        image = card.find("img", src=True)
        items.append(
            ParsedAktuel(
                source_key=_SOK_ID.search(link["href"]).group(1),
                period_key=SOK_PERIOD[0],
                period_label=SOK_PERIOD[1],
                starts_on=None,
                ends_on=None,
                title=title,
                brand=None,
                quantity_text=None,
                details=None,
                price=price,
                old_price=regular if regular and regular > price else None,
                image_url=image["src"] if image else None,
                source_url=urljoin(SOK_BASE, link["href"]),
            )
        )
    return items


# --- toplama ----------------------------------------------------------------------------


class AktuelCollector:
    def __init__(self, http: PoliteClient, today: date | None = None) -> None:
        self.http = http
        self.today = today or date.today()
        self._robots: dict[str, RobotFileParser] = {}

    async def get(self, url: str) -> str:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser = RobotFileParser()
            try:
                parser.parse((await self.http.fetch("GET", f"{origin}/robots.txt")).text.splitlines())
            except HttpError as exc:
                if not (exc.status_code and 400 <= exc.status_code < 500):
                    raise
                parser.parse([])  # robots.txt yok: her şey serbest
            self._robots[origin] = parser
        if not self._robots[origin].can_fetch(self.http.user_agent, url):
            raise HttpError(f"robots.txt izin vermiyor: {url}")
        return (await self.http.fetch("GET", url)).text

    async def bim(self) -> list[ParsedAktuel]:
        items = []
        for period in parse_bim_periods(await self.get(BIM_AKTUEL)):
            html = await self.get(f"{BIM_AKTUEL}?Bim_AktuelTarihKey={period.key}")
            items += parse_bim_products(html, period, self.today)
        return items

    async def sok(self) -> list[ParsedAktuel]:
        first = await self.get(SOK_FIRSATLAR)
        items = parse_sok_products(first)
        for page in range(2, sok_total_pages(first) + 1):
            items += parse_sok_products(await self.get(f"{SOK_FIRSATLAR}?page={page}"))
        return items


COLLECTORS = {"bim": AktuelCollector.bim, "sok": AktuelCollector.sok}


async def save_aktuel(db: AsyncSession, market_slug: str, items: list[ParsedAktuel]) -> int:
    """Gelenleri kaydeder, bu turda görünmeyen (broşürden kalkmış) eskileri siler."""
    if not items:
        return 0
    started = datetime.now(timezone.utc)
    unique = {item.source_key: item for item in items}
    rows = [{"market_slug": market_slug, "seen_at": started, **vars(item)} for item in unique.values()]
    stmt = insert(AktuelItem).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_aktuel_items_market_source",
        set_={c: stmt.excluded[c] for c in rows[0] if c not in ("market_slug", "source_key")},
    )
    await db.execute(stmt)
    await db.execute(
        delete(AktuelItem).where(AktuelItem.market_slug == market_slug, AktuelItem.seen_at < started)
    )
    await db.commit()
    return len(rows)


async def sync_aktuel(
    db: AsyncSession, http: PoliteClient, markets: tuple[str, ...] = tuple(COLLECTORS), today: date | None = None
) -> dict[str, int]:
    collector = AktuelCollector(http, today)
    stats = {}
    for slug in markets:
        try:
            items = await COLLECTORS[slug](collector)
        except HttpError as exc:
            log.warning("%s aktüelleri alınamadı: %s", slug, exc)
            stats[slug] = 0
            continue
        if not items:
            log.warning("%s aktüel sayfasında ürün bulunamadı; eldekiler korunuyor", slug)
        stats[slug] = await save_aktuel(db, slug, items)
    return stats
