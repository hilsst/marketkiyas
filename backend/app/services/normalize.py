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


# Zincirler aynı ürünü farklı yazar: "UHT Süt %3.1 Yağlı" (Şok) = "Tam Yağlı Süt" (BİM)
_FAT_SYNONYMS = (
    (re.compile(r"\b3(?:[.,]\d)?\s*yagli\b"), "tam yagli"),
    (re.compile(r"\b1[.,]5\s*yagli\b"), "yarim yagli"),
    (re.compile(r"\b0(?:[.,]\d+)?\s*yagli\b"), "yagsiz"),
    # Diğer oranlar ayırt edici kalsın: "%2.5 yağlı" -> "yag25 yagli" ("%1 yağlı" ile karışmasın)
    (re.compile(r"\b(\d+)(?:[.,](\d+))?\s*yagli\b"), lambda m: f"yag{m.group(1)}{m.group(2) or ''} yagli"),
)
# Ürünü ayırt etmeyen kelimeler
_NOISE_TOKENS = frozenset(
    {"uht", "pastorize", "homojenize", "sade", "inek", "x", "ve", "li", "lu", "lt", "l", "ml", "g", "gr", "kg", "adet", "cl"}
)
# Tek başına ürünü değiştiren kelimeler (kökleriyle): biri varken diğeri yoksa farklı üründür
_DISTINCTIVE_TOKENS = frozenset(
    {"laktozsuz", "light", "yagsiz", "organik", "sekersiz", "diyet", "zero", "glutensiz", "cocuk", "bebek",
     "kepekl", "tam", "yarim", "tuzsuz", "kafeinsiz", "protein", "keci", "koyun", "dondurulmus"}
)
# Eşleşme için gereken en düşük kelime benzerliği (Jaccard); eşit kümeler her zaman eşleşir
SAME_PRODUCT_MIN_JACCARD = 0.8


def _stem(token: str) -> str:
    """Basit kök: 'sutu' -> 'sut', 'ekmegi' -> 'ekmek'. Her iki tarafa da aynı uygulandığı için kaba olması sorun değil."""
    if len(token) > 3 and token[-1] in "iu":
        token = token[:-1]
    if len(token) > 3 and token.endswith("g"):
        token = token[:-1] + "k"
    return token


def product_tokens(name: str) -> frozenset[str]:
    """Miktarsız, sırasız ürün kelimeleri: 'UHT Süt %3.1 Yağlı 1 Lt' -> {'sut', 'tam', 'yagl'}."""
    text = _QTY_RE.sub(" ", normalize_text(name))
    for pattern, replacement in _FAT_SYNONYMS:
        text = pattern.sub(replacement, text)
    return frozenset(
        _stem(t) for t in re.split(r"[^a-z0-9]+", text) if t and t not in _NOISE_TOKENS and not t.isdigit()
    )


def same_product(a: str, b: str) -> bool:
    """İki ürün adı (markasız) aynı ürünü mü anlatıyor? Miktar ayrıca karşılaştırılmalı.

    Harf benzerliği yetmez ("su" ile "süt"); kelimeler bire bir ya da çok büyük ölçüde örtüşmeli.
    """
    ta, tb = product_tokens(a), product_tokens(b)
    if not ta or not tb:
        return False
    if ta == tb or len(ta & tb) / len(ta | tb) >= SAME_PRODUCT_MIN_JACCARD:
        return True
    # Biri diğerinin tek bir tanım kelimesi eksik hâli: "Sıvı Bulaşık Deterjanı" ~ "Ultra Sıvı Bulaşık
    # Deterjanı". Kısa adlar ("Süt") ve ürünü değiştiren kelimeler ("Laktozsuz") hariç.
    small, large = sorted((ta, tb), key=len)
    extra = large - small
    return small < large and len(small) >= 2 and len(extra) == 1 and not (extra & _DISTINCTIVE_TOKENS)
