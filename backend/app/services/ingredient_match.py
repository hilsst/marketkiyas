"""Tarif malzemesini katalogdaki ürün adıyla eşleştirme.

Eski kural "ürün adı arama ifadesinin kelimelerini içersin" idi; bu yüzden "zeytinyağı" araması
"Zeytinyağlı Sıvı Sabun"u, "limon" araması "Limonlu Popkek"i buluyordu. Şimdi:

1. Kelime kelime bakılır: ürün adındaki bir kelime, aranan kökle başlamalı ve kalan kısım yalnızca
   bir çekim eki olmalıdır ("salçası", "yağı"). "-lı/-lu" (limonlu), "-sız" (tuzsuz) gibi yeni bir
   ürünü niteleyen ekler eşleşmez.
2. Ürün adında, arama ifadesinde geçmeyen bir "başka ürün" kelimesi (sabun, deterjan, popkek, kek,
   cips, sos, aromalı...) varsa ürün elenir.
3. Temizlik, kişisel bakım ve bebek kategorisindeki ürünler hiç aday olmaz (bkz. meals._match).
"""

import re

from app.models.enums import Unit
from app.services.normalize import normalize_text, parse_quantity

# Kökten sonra gelebilecek çekim ekleri (aksansız): iyelik, çoğul, belirtme. Bunların dışındaki her
# ek ("li", "lu", "siz", "lik", "ci"...) kelimeyi başka bir ürüne çevirir.
INFLECTIONS = frozenset({
    "", "i", "u", "a", "e", "si", "su", "isi", "usu",
    "lar", "ler", "lari", "leri", "larin", "lerin",
})

# Gıda malzemesi olmayan ya da malzemeyi yalnızca tat/aroma olarak taşıyan ürün kelimeleri.
# Arama ifadesinin kendisi bu kelimeyi içeriyorsa (ör. "portakal suyu", "nar eksisi") engel olmaz.
OTHER_PRODUCT_WORDS = frozenset({
    # temizlik ve kişisel bakım
    "sabun", "deterjan", "sampuan", "temizleyici", "temizlik", "yumusatici", "bulasik",
    "camasir", "kolonya", "parfum", "deodorant", "losyon", "krem", "mendil", "pecete", "havlu",
    "dezenfektan", "kozmetik", "dus", "jel", "kremi", "macun", "sac", "cilt", "tiras", "oda",
    "kokusu", "koku", "mum", "kedi", "kopek", "mama", "tablet", "kapsul", "vitamin",
    # tatlandırılmış / işlenmiş ürünler
    "popkek", "kek", "biskuvi", "gofret", "kraker", "cips", "sakiz", "sekerleme", "lokum",
    "dondurma", "gazoz", "kola", "cikolata", "puding", "jole", "bar", "aroma", "aromali", "esans",
    "esansi", "sos", "ketcap", "mayonez", "tursu", "recel", "marmelat", "pekmez", "surup", "likor",
    "icecek", "ice", "tea", "icetea", "enerji", "kokteyl", "sirop", "nektar", "limonata", "sirke", "corba", "kadayif", "bulyon", "baharat",
    "cesni", "kabugu", "tozu", "tuzu", "suyu", "ezmesi", "unu", "yagi", "salca", "kurusu",
    "kurutulmus", "cubuk", "kraker", "tatlisi", "helva", "tahin", "kremasi", "dolgulu",
    "kaplamali", "soslu", "turta", "pasta", "bebe", "bebek", "mama", "tohum", "fide", "bardak",
    # mutfak gereci ve ev eşyası ("sarımsak ezici", "kaşar rendesi", "yumurta fırçası")
    "ezici", "soyucu", "press", "fircasi", "firca", "rende", "rendesi", "kabi", "kasik", "kasigi", "tuzluk",
    "suzgec", "suzgeci", "sikacagi", "surahisi", "kovasi", "kutusu", "kalibi", "lamba", "lambasi", "pano",
    "makinesi", "aparati", "tabagi", "organizeri", "kiracagi", "yumak", "saksi", "oyuncak", "kamyonu",
    # giyim ve kişisel ürün
    "corap", "lastik", "soket", "slip", "terlik", "pijama", "sutyen", "bere", "canta", "dudak", "pedi",
    # temizlik markaları
    "finish", "fairy", "vanish", "domestos", "persil", "ariel", "omo", "bingo", "pril",
    # hazır / işlenmiş: kurabiye, atıştırmalık, hazır yemek, bitki çayı, bebek maması
    "kurabiye", "kurabiyesi", "granola", "cerezi", "pastil", "propolis", "draje", "citir", "cizi", "bitki", "bitkisel",
    "pure", "puresi", "devam", "formula", "indomie", "dudomi", "oreo", "duble", "ezmeli", "sehriye",
    "arabiata", "bolonez", "napoliten", "falim", "fresh", "fanta", "schweppes", "cappy", "sprite", "pepsi",
    "jusstea", "fuse", "pinari", "baklava", "karbonat", "lezztat", "kozlenmis", "kizartma",
    "latte", "mocha", "elidor", "arko", "rolls", "patos", "activia", "probiyotik", "kofte", "koftesi", "patlagi",
    "bergamotlu", "ananasli", "cheesecake", "bardagi",
    # dolgulu / aromalı ürün sıfatları ("etli ekmek", "cevizli sucuk", "tereyağlı kuru fasulye")
    "etli", "kiymali", "peynirli", "sucuklu", "cevizli", "findikli", "fistikli", "bademli", "cikolatali",
    "tereyagli", "margarin",
})


def _words(text: str) -> list[str]:
    return [w for w in normalize_text(text).replace(".", " ").replace(",", " ").replace("'", " ").split() if w]


def roots(term: str) -> list[str]:
    """Kaba kök: 'domates salcasi' -> ['domates', 'salca'], 'zeytinyagi' -> ['zeytinyag']."""
    out = []
    for word in _words(term):
        root = word
        if word.endswith(("si", "su")) and len(word) > 4:
            root = word[:-2]
        elif word[-1] in "iu" and len(word) > 3:
            root = word[:-1]
        out.append(root)
    return out


def word_is(word: str, root: str) -> bool:
    """'salcasi' ve 'salca' -> True; 'limonlu' ve 'limon' -> False (limonlu başka bir ürün)."""
    return word.startswith(root) and word[len(root):] in INFLECTIONS


def _tokens(name: str) -> list[str]:
    words = _words(name)
    # "Zeytin Yağı" ile "zeytinyağı" aynı şey: yan yana iki kelimenin bitişik hali de denenir
    return words + [a + b for a, b in zip(words, words[1:])]


def name_matches(term: str, product_name: str, excludes: tuple[str, ...] = ()) -> bool:
    """Ürün adı bu arama ifadesinin malzemesi mi?"""
    name = normalize_text(product_name)
    if any(ex and ex in name for ex in excludes):
        return False
    term_roots = roots(term)
    if not term_roots:
        return False
    tokens = _tokens(product_name)
    matched = all(any(word_is(t, r) for t in tokens) for r in term_roots)
    if not matched and len(term_roots) > 1:
        # "zeytin yagi" araması "Zeytinyağı" ürününü de bulsun
        joined = "".join(term_roots)
        matched = any(word_is(t, joined) for t in tokens)
    if not matched:
        return False
    return not _has_other_product_word(term, product_name)


def _has_other_product_word(term: str, product_name: str) -> bool:
    term_words = _words(term)
    term_roots = roots(term)
    term_text = " ".join(term_words)
    words = _words(product_name)
    for word in words:
        if any(word_is(word, other) for other in OTHER_PRODUCT_WORDS):
            # Arama ifadesinin kendi kelimesiyse sorun değil ("nar eksisi", "portakal suyu", "tereyagi")
            if word in term_words or any(word_is(word, r) for r in term_roots) or word in term_text.replace(" ", ""):
                continue
            return True
    return False


_FRESH_UNIT = re.compile(r"\b(kg|adet|demet)\b")


def grocery_like(product_name: str, quantity=None, category_known: bool = False) -> bool:
    """Kategorisi bilinmeyen ürün yalnızca miktarı varsa gıda sayılır: gerçek gıdada gramaj/hacim ("500 g", "1 l"),
    adet ya da kg bulunur; "sarımsak ezici", "patates kamyonu" gibi eşya adlarında bulunmaz. İki-beş adetlik
    paketler ("2 li") giyim ve temizlik ürünlerinde olur; yumurta paketleri (10'lu) geçer."""
    if category_known:
        return True
    if quantity is not None:
        return True
    name = normalize_text(product_name)
    if _FRESH_UNIT.search(name):
        return True
    parsed = parse_quantity(product_name)
    if parsed is None:
        return False
    amount, unit = parsed
    return unit is not Unit.PIECE or amount >= 6


def unit_compatible(need_unit: Unit | str, product_unit: Unit | str | None) -> bool:
    """Gramla aranan malzeme için hacimle (ml) satılan ürün (dondurma, içecek) uygun değildir, tersi de."""
    if product_unit is None:
        return True
    pair = {Unit(need_unit), Unit(product_unit)}
    return pair != {Unit.G, Unit.ML}


def accepts(search_term: str, product_name: str, excludes: tuple[str, ...] = (), unit: Unit | str | None = None) -> bool:
    """Malzemenin arama ifadesi ("|" ile alternatifli) için ürün adı uygun mu? meals._match ile aynı kural.
    unit verilirse ürünün adından okunan birim malzemeyle uyuşmalı; kategori bilinmediğinde gıda gibi görünmeli."""
    if not grocery_like(product_name):
        return False
    if unit is not None:
        parsed = parse_quantity(product_name)
        if parsed is not None and not unit_compatible(unit, parsed[1]):
            return False
    return any(name_matches(alt.strip(), product_name, excludes) for alt in search_term.split("|") if alt.strip())
