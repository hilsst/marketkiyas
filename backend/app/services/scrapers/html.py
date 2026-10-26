"""Ürün sayfası HTML'inden ad, marka, fiyat ve görsel çıkarma.

Önce schema.org JSON-LD (Product/offers) denenir; yoksa sayfa yapısından sezgisel okunur.
"""

import json
from dataclasses import dataclass
from decimal import Decimal

from bs4 import BeautifulSoup, Tag

from app.services.scrapers.base import all_tl, parse_tl


@dataclass
class ParsedProduct:
    title: str
    brand: str | None
    price: Decimal
    image_url: str | None


def _jsonld_products(soup: BeautifulSoup) -> list[dict]:
    found = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        found += [i for i in items if isinstance(i, dict) and i.get("@type") in ("Product", ["Product"])]
    return found


def _from_jsonld(soup: BeautifulSoup) -> ParsedProduct | None:
    for item in _jsonld_products(soup):
        offers = item.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        raw_price = offers.get("price") or offers.get("lowPrice")
        try:
            price = Decimal(str(raw_price).replace(",", ".")).quantize(Decimal("0.01")) if raw_price else None
        except ArithmeticError:
            price = None
        name = item.get("name")
        if not price or price <= 0 or not name:
            continue
        brand = item.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        image = item.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        return ParsedProduct(str(name).strip(), (brand or None) and str(brand).strip(), price, image)
    return None


def _label_value(soup: BeautifulSoup, label: str) -> str | None:
    """'Marka' etiketinin yanındaki değer (ör. <span>Marka</span><span>ÜLKER</span>)."""
    for el in soup.find_all(string=lambda s: s and s.strip().casefold() == label.casefold()):
        node = el.parent
        for sibling in node.find_next_siblings() if isinstance(node, Tag) else []:
            text = sibling.get_text(" ", strip=True)
            if text:
                return text
        nxt = node.find_next(string=lambda s: s and s.strip() and s.strip().casefold() != label.casefold())
        if nxt:
            return nxt.strip()
    return None


def _price_from_markup(soup: BeautifulSoup, h1: Tag | None) -> Decimal | None:
    # Sınıf adında "price"/"fiyat" geçen öğeler; indirimli sayfada en düşük olan güncel fiyattır
    candidates = []
    for el in soup.find_all(class_=lambda c: c and any(k in c.lower() for k in ("price", "fiyat"))):
        if el.find_parent(["del", "s", "strike"]) or el.name in ("del", "s", "strike"):
            continue
        candidates += all_tl(el.get_text(" ", strip=True))
    if candidates:
        return min(candidates)
    # Son çare: başlıktan sonraki ilk TL ifadesi
    start = h1 if h1 is not None else soup
    for text in start.find_all_next(string=True) if h1 is not None else soup.find_all(string=True):
        if (price := parse_tl(text)) is not None:
            return price
    return None


def parse_product_html(html: str) -> ParsedProduct | None:
    soup = BeautifulSoup(html, "html.parser")
    if parsed := _from_jsonld(soup):
        return parsed
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else None
    if not title:
        return None
    price = _price_from_markup(soup, h1)
    if price is None:
        return None
    og_image = soup.find("meta", property="og:image")
    return ParsedProduct(
        title=title,
        brand=_label_value(soup, "Marka"),
        price=price,
        image_url=og_image.get("content") if og_image else None,
    )
