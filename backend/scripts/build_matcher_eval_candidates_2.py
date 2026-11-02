"""Taze holdout (ikinci küme) için aday havuzu: ilk kümede hiç kullanılmamış 60 yeni sorgudan.

Eşleştirici bu kümeye bakılarak AYARLANMAZ. Kullanım: python scripts/build_matcher_eval_candidates_2.py <raw_dir>
Çıktı: tests/fixtures/matcher_eval_2/{products,candidates}.json (aynı yöntem: build_matcher_eval_candidates.py)."""

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_matcher_eval_candidates as b  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "matcher_eval_2"

# (anahtar, arama ifadesi, elenecek kelimeler, birim, sorgu) — recipe_data/vocab.py'den aynen
INGREDIENTS = [
    ("biberSalcasi", "biber salcasi", "", "g", "biber salçası"),
    ("pulbiber", "pul biber", "", "g", "pul biber"),
    ("karabiber", "karabiber", "", "g", "karabiber"),
    ("kimyon", "kimyon", "", "g", "kimyon"),
    ("nane", "nane", "sekeri,sakiz,cay", "g", "nane"),
    ("kekik", "kekik", "yagi,sabun,cay", "g", "kekik"),
    ("tarcin", "tarcin", "sakiz,cay,kek", "g", "tarçın"),
    ("zerdecal", "zerdecal", "", "g", "zerdeçal"),
    ("sumak", "sumak", "", "g", "sumak"),
    ("irmik", "irmik", "tatlisi,helva", "g", "irmik"),
    ("yulaf", "yulaf ezmesi|yulaf", "", "g", "yulaf ezmesi"),
    ("tahin", "tahin", "helva", "g", "tahin"),
    ("pekmez", "uzum pekmezi|pekmez", "", "g", "pekmez"),
    ("susam", "susam", "yagi,tahin,simit,kraker,bar,helva", "g", "susam"),
    ("hindistancevizi", "hindistan cevizi", "sutu,yagi,sekerleme", "g", "hindistan cevizi"),
    ("findik", "findik", "ezmesi,cikolata,kakaolu,sutlu,kremasi", "g", "fındık"),
    ("ceviz", "ceviz ici|ceviz", "yagi,kabuklu", "g", "ceviz"),
    ("badem", "badem", "ezmesi,sutu,yagi,cikolata", "g", "badem"),
    ("uzum", "kuru uzum|sultaniye", "", "g", "kuru üzüm"),
    ("kayisi", "kuru kayisi", "", "g", "kuru kayısı"),
    ("hurma", "hurma", "trabzon", "g", "hurma"),
    ("incir", "kuru incir", "", "g", "kuru incir"),
    ("zeytin", "siyah zeytin|zeytin", "ezmesi", "g", "zeytin"),
    ("mozzarella", "mozzarella|mozarella", "", "g", "mozzarella"),
    ("parmesan", "parmesan|rende kasar", "", "g", "parmesan"),
    ("lor", "lor peyniri|lor", "", "g", "lor peyniri"),
    ("ayran", "ayran", "", "ml", "ayran"),
    ("pastirma", "pastirma", "", "g", "pastırma"),
    ("somon", "somon", "fume,konserve", "g", "somon"),
    ("hamsi", "hamsi", "konserve", "g", "hamsi"),
    ("yufka", "yufka", "kadayif", "g", "yufka"),
    ("pide", "pide", "kadayif", "g", "pide"),
    ("tortilla", "tortilla|lavas", "cips", "g", "tortilla"),
    ("noodle", "noodle", "cup,bardak", "g", "noodle"),
    ("sehriye", "arpa sehriye|sehriye", "tel", "g", "şehriye"),
    ("eriste", "eriste", "", "g", "erişte"),
    ("misirunu", "misir unu", "", "g", "mısır unu"),
    ("pudraseker", "pudra seker", "", "g", "pudra şeker"),
    ("maya", "instant maya|kuru maya|maya", "kabartma", "g", "instant maya"),
    ("brokoli", "brokoli", "", "g", "brokoli"),
    ("karnabahar", "karnabahar", "dondurulmus,tursu", "g", "karnabahar"),
    ("marul", "marul|kivircik|aysberg", "tohum", "g", "marul"),
    ("roka", "roka", "tohum", "g", "roka"),
    ("lahana", "beyaz lahana|lahana", "tursu,kirmizi,bruksel", "g", "lahana"),
    ("bamya", "bamya", "konserve", "g", "bamya"),
    ("avokado", "avokado", "", "g", "avokado"),
    ("portakal", "portakal", "suyu,aromali", "g", "portakal"),
    ("elma", "elma", "suyu,sirkesi,kurusu,cips,kek,turta,aromali", "g", "elma"),
    ("muz", "muz", "cips,kurusu,aromali,sut", "g", "muz"),
    ("cilek", "cilek", "recel,aromali,sut,kurusu", "g", "çilek"),
    ("nareksisi", "nar eksisi", "", "ml", "nar ekşisi"),
    ("soyasosu", "soya sosu", "", "ml", "soya sosu"),
    ("yesilcay", "yesil cay", "aromali,soguk,icecek", "g", "yeşil çay"),
    ("ihlamur", "ihlamur", "aromali,soguk,seker", "g", "ihlamur"),
    ("dereotu", "dereotu|dere otu", "kurusu,kuru", "g", "dereotu"),
    ("tazefasulye", "taze fasulye|ayse fasulye", "konserve,dondurulmus", "g", "taze fasulye"),
    ("kuzukusbasi", "kuzu kusbasi", "", "g", "kuzu eti"),
]


def main(raw_dir: str) -> None:
    products, by_query = b.load_pool(Path(raw_dir))
    out = []
    for key, term, exclude, unit, query in INGREDIENTS:
        query = unicodedata.normalize("NFC", query)
        pool = by_query.get(query, [])
        if not pool:
            print("BİM/A101 ürünü yok, atlandı:", key)
            continue
        chosen: list[str] = []
        for store in b.STORES:
            ids = sorted((i for i in pool if store in products[i]["stores"]), key=lambda i: b.h(key + i))
            chosen += [i for i in ids[: b.PER_STORE] if i not in chosen]
            others = sorted((i for q, v in by_query.items() if q != query for i in v
                             if store in products[i]["stores"] and i not in pool), key=lambda i: b.h("d" + key + i))
            chosen += [i for i in others[: b.DISTRACTORS_PER_STORE] if i not in chosen]
        chosen.sort(key=lambda i: b.h("o" + key + i))
        out.append({"key": key, "term": term, "exclude": exclude, "unit": unit, "split": "holdout", "candidates": chosen})
    OUT.mkdir(parents=True, exist_ok=True)
    used = {i for e in out for i in e["candidates"]}
    (OUT / "products.json").write_text(json.dumps(sorted((products[i] for i in used), key=lambda p: p["id"]), ensure_ascii=False, indent=0))
    (OUT / "candidates.json").write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print(len(out), "ingredients,", sum(len(e["candidates"]) for e in out), "candidate rows,", len(used), "unique products")


if __name__ == "__main__":
    main(sys.argv[1])
