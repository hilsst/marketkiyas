"""Türkçe ürün adı ve miktar normalizasyonu. Scraper'lar ve arama aynı fonksiyonu kullanır."""

import re
from decimal import Decimal

from app.models.enums import Unit

_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_ASCII = str.maketrans("çğıöşüâîû", "cgiosuaiu")

# (çarpan, temel birim)
_UNITS: dict[str, tuple[Decimal, Unit]] = {
    "ml": (Decimal(1), Unit.ML),
    "cl": (Decimal(10), Unit.ML),
    "lt": (Decimal(1000), Unit.ML),
    "l": (Decimal(1000), Unit.ML),
    "litre": (Decimal(1000), Unit.ML),
    "g": (Decimal(1), Unit.G),
    "gr": (Decimal(1), Unit.G),
    "gram": (Decimal(1), Unit.G),
    "kg": (Decimal(1000), Unit.G),
    "kilo": (Decimal(1000), Unit.G),
    "adet": (Decimal(1), Unit.PIECE),
    "li": (Decimal(1), Unit.PIECE),  # "30'lu yumurta" -> "30 lu"
    "lu": (Decimal(1), Unit.PIECE),
    "lü": (Decimal(1), Unit.PIECE),
}
_QTY_RE = re.compile(
    r"(?:(\d+)\s*x\s*)?(\d+(?:[.,]\d+)?)\s*'?\s*(" + "|".join(sorted(_UNITS, key=len, reverse=True)) + r")\b"
)


def turkish_lower(text: str) -> str:
    return text.translate(_TR_LOWER).lower()


def normalize_text(text: str) -> str:
    """'Pınar Süt 1 L' -> 'pinar sut 1 l'. Aksanları atar, noktalamayı boşluğa çevirir."""
    text = turkish_lower(text).translate(_ASCII)
    text = re.sub(r"[^a-z0-9.,'x ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_quantity(text: str) -> tuple[Decimal, Unit] | None:
    """'Süt 1 L' -> (1000, ml), 'Yoğurt 2x500 g' -> (1000, g), '30'lu Yumurta' -> (30, adet)."""
    match = _QTY_RE.search(turkish_lower(text))
    if not match:
        return None
    multiplier, amount, unit = match.groups()
    factor, base = _UNITS[unit]
    value = Decimal(amount.replace(",", ".")) * factor * (int(multiplier) if multiplier else 1)
    return (value.quantize(Decimal(1)) if value == value.to_integral() else value.normalize()), base


def normalize_name(text: str) -> str:
    """Eşleştirme anahtarı: miktar ifadesi temel birime çevrilir. 'Pınar Süt 1 L' -> 'pinar sut 1000ml'."""
    base = normalize_text(text)
    qty = parse_quantity(text)
    if qty is None:
        return base
    value, unit = qty
    stripped = _QTY_RE.sub(" ", base).strip()
    stripped = re.sub(r"\s+", " ", stripped)
    return f"{stripped} {value}{unit.value}".strip()
