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

from app.services.normalize import normalize_text

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
    "icecek", "ice", "tea", "icetea", "enerji", "kokteyl", "sirop", "nektar", "limonata", "sirke", "konserve", "corba", "kadayif", "bulyon", "baharat",
    "cesni", "kabugu", "tozu", "tuzu", "suyu", "ezmesi", "unu", "yagi", "salca", "kurusu",
    "kurutulmus", "cubuk", "kraker", "tatlisi", "helva", "tahin", "kremasi", "dolgulu",
    "kaplamali", "soslu", "turta", "pasta", "bebe", "bebek", "mama", "tohum", "fide", "bardak", "tabak",
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
