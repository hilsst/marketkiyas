"""Ürün sayfası HTML'inden ad, marka, fiyat ve görsel çıkarma.

Önce schema.org JSON-LD (Product/offers) denenir; yoksa sayfa yapısından sezgisel okunur.
"""

import json
from dataclasses import dataclass
from decimal import Decimal

from bs4 import BeautifulSoup, Tag

from app.services.scrapers.base import all_tl


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
    """JSON-LD'deki ürün; fiyatı yoksa 0 ile döner (ad/marka/görsel yine işe yarar)."""
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
        if not name:
            continue
        brand = item.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        image = item.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        return ParsedProduct(str(name).strip(), (brand or None) and str(brand).strip(), price or Decimal(0), image)
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


_MAX_SCOPE_DEPTH = 6


def _is_price_box(class_: str | None) -> bool:
    return bool(class_) and any(k in class_.lower() for k in ("price", "fiyat"))


def _price_from_markup(h1: Tag) -> Decimal | None:
    """Başlığa en yakın fiyat kutusu. Sayfanın geri kalanında "benzer ürünler" kartları da fiyat taşır,
    bu yüzden başlıktan yukarı doğru çıkıp fiyat kutusu içeren ilk kapsayıcıda durulur. Kutu boşsa
    (fiyat henüz yüklenmemiş) None döner; başka bir ürünün fiyatına kayılmaz.
    İndirimli üründe eski ve yeni fiyat aynı kutudadır; düşük olan güncel fiyattır."""
    node = h1
    for _ in range(_MAX_SCOPE_DEPTH):
        node = node.parent
        if not isinstance(node, Tag):
            break
        boxes = node.find_all(class_=_is_price_box)
        if not boxes:
            continue
        candidates = []
        for el in boxes:
            if el.name in ("del", "s", "strike") or el.find_parent(["del", "s", "strike"]):
                continue
            candidates += all_tl(el.get_text(" ", strip=True))
        return min(candidates) if candidates else None
    return None


def parse_product_html(html: str, *, trust_jsonld_price: bool = True) -> ParsedProduct | None:
    """trust_jsonld_price=False: JSON-LD'den sadece ad/marka/görsel alınır, fiyat sayfada görünen
    fiyat kutusundan okunur (A101'in JSON-LD fiyatı güncel değil)."""
    soup = BeautifulSoup(html, "html.parser")
    jsonld = _from_jsonld(soup)
    if jsonld and jsonld.price > 0 and trust_jsonld_price:
        return jsonld
    h1 = soup.find("h1")
    if h1 is None:
        return None
    price = _price_from_markup(h1)
    if price is None:
        return None
    if jsonld:
        return ParsedProduct(jsonld.title, jsonld.brand, price, jsonld.image_url)
    title = h1.get_text(" ", strip=True)
    if not title:
        return None
    og_image = soup.find("meta", property="og:image")
    return ParsedProduct(
        title=title,
        brand=_label_value(soup, "Marka"),
        price=price,
        image_url=og_image.get("content") if og_image else None,
    )
