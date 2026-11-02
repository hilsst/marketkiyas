"""Bağımsız eşleştirme değerlendirme kümesi için aday ürün havuzunu üretir (etiketleme öncesi).

Girdi: marketfiyati /search ham yanıtları (raw/search-<sorgu>.json = [sayfa0, sayfa1]); BİM ve A101'de satılan
ürünler alınır. Çıktı: tests/fixtures/matcher_eval/products.json (ürün havuzu) ve candidates.json (malzeme başına
aday listesi, etiketsiz). Eşleştirici BU ADIMDA çalıştırılmaz; etiketler adayları görmeden/eşleştiriciyi çalıştırmadan verilir.
Kullanım: python scripts/build_matcher_eval_candidates.py <raw_dir> """

import hashlib
import json
import sys
import unicodedata
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "matcher_eval"
STORES = ("bim", "a101")
PER_STORE = 8
DISTRACTORS_PER_STORE = 2
HOLDOUT_SHARE = 0.3

# (anahtar, arama ifadesi, elenecek kelimeler, birim, sorgu dosyası) — arama ifadeleri recipe_data/vocab.py'den aynen
INGREDIENTS = [
    ("domates", "domates", "salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl", "g", "domates"),
    ("sogan", "kuru sogan", "toz,granul", "g", "soğan"),
    ("sarimsak", "sarimsak", "toz,granul", "g", "sarımsak"),
    ("sivribiber", "sivri biber", "tursu,toz", "g", "biber"),
    ("kapya", "kapya biber|kirmizi biber|renkli biber", "pul,toz,salca,tursu,kozlenmis,konserve,sos", "g", "biber"),
    ("havuc", "havuc", "suyu,rendesi,tursu", "g", "havuç"),
    ("kabak", "kabak", "bal,cekirde,tatlisi", "g", "kabak"),
    ("patates", "patates", "cips,kizartma,dondurulmus,pure", "g", "patates"),
    ("patlican", "patlican", "salata,kozlenmis,konserve,tursu,kuru,kizartma", "g", "patlıcan"),
    ("mantar", "mantar", "konserve,tursu,sos,corba", "g", "mantar"),
    ("ispanak", "ispanak", "dondurulmus,konserve", "g", "ıspanak"),
    ("salatalik", "salatalik", "tursu,kornison", "g", "salatalık"),
    ("bezelye", "bezelye", "konserve", "g", "bezelye"),
    ("limon", "limon", "sosu,kolonya,tuzu,suyu,aromali", "g", "limon"),
    ("maydanoz", "maydanoz", "kurusu,kuru", "g", "maydanoz"),
    ("misir", "misir konservesi|konserve misir|tatli misir|misir", "cips,patlak,patlamis,unu,nisasta,gevrek,yag,irmik", "g", "mısır"),
    ("nohut", "nohut", "konserve,haslanmis,leblebi,unu", "g", "nohut"),
    ("kirmizimercimek", "kirmizi mercimek", "", "g", "mercimek"),
    ("kurufasulye", "kuru fasulye", "konserve,haslanmis", "g", "fasulye"),
    ("barbunya", "kirmizi fasulye|barbunya", "tursu,pilaki", "g", "fasulye"),
    ("un", "bugday unu|un", "kurabiye,manti,makarna,helva,biskuvi,galeta,misir,pirinc,nohut,cavdar,patlagi,elegi", "g", "un"),
    ("nisasta", "misir nisastasi|nisasta", "", "g", "nişasta"),
    ("pirinc", "pirinc", "unu,patlagi,sirkesi", "g", "pirinç"),
    ("bulgur", "pilavlik bulgur|bulgur", "koftelik,kofte,ince", "g", "bulgur"),
    ("makarna", "makarna|spagetti|penne", "", "g", "makarna"),
    ("seker", "toz seker", "pudra,esmer,kup", "g", "toz şeker"),
    ("bal", "bal", "balik,kabak,kabag,cekirdek", "g", "bal"),
    ("kakao", "kakao", "kremasi,sutlu,icecek,gofret,findik", "g", "kakao"),
    ("salca", "domates salcasi", "", "g", "salça"),
    ("sirke", "elma sirkesi|uzum sirkesi|sirke", "", "ml", "sirke"),
    ("zeytinyagi", "zeytinyagi", "", "ml", "zeytinyağı"),
    ("aycicek", "aycicek yagi", "", "ml", "ayçiçek yağı"),
    ("tuz", "tuz", "tuzsuz,tuzlu", "g", "tuz"),
    ("kabartma", "kabartma tozu", "", "g", "kabartma tozu"),
    ("vanilya", "vanilya|vanilin", "", "g", "vanilya"),
    ("cay", "cay", "bitki,yesil,ada,ihlamur,soguk,kupa,bardak,demlik,makinesi,kasigi", "g", "çay"),
    ("turkkahvesi", "turk kahvesi", "sutlu,3u1,2si1,kapsul", "g", "kahve"),
    ("sodasu", "maden suyu|soda", "aromali,meyveli", "ml", "maden suyu"),
    ("sut", "sut", "tozu,cikolatali,kakaolu,cilekli,muzlu,laktozsuz,keci,badem,soya,hindistan", "ml", "süt"),
    ("yogurt", "yogurt", "icecek,meyveli,suzme,cilekli,kakaolu", "g", "yoğurt"),
    ("beyazpeynir", "beyaz peynir", "light,yarim", "g", "beyaz peynir"),
    ("kasar", "kasar peyniri|kasar", "tost,cubuk", "g", "kaşar"),
    ("krema", "sivi krema|krema", "sanitize,sekerli,kakaolu,kremasi,cikolata,kahve,sac,yuz,el", "ml", "krema"),
    ("tereyagi", "tereyagi", "", "g", "tereyağı"),
    ("yumurta", "yumurta", "cikolata,makarna,eriste", "adet", "yumurta"),
    ("kiyma", "dana kiyma|kiyma", "tavuk,hindi,kuzu", "g", "kıyma"),
    ("kusbasi", "dana kusbasi|kusbasi", "tavuk,hindi,kuzu", "g", "dana eti"),
    ("tavukgogus", "tavuk gogus|pilic gogus|pilic bonfile|tavuk bonfile|pilic fileto", "fume,jambon,salam,doner,pane,haslanmis", "g", "tavuk göğsü"),
    ("tavukbut", "tavuk but|pilic but", "pane,haslanmis,fume", "g", "tavuk but"),
    ("sucuk", "sucuk", "tost,pizza,cips", "g", "sucuk"),
    ("tonbaligi", "ton baligi", "", "g", "ton balığı"),
    ("ekmek", "ekmek", "galeta,kirintisi,kadayif", "g", "ekmek"),
    ("galetaunu", "galeta unu", "", "g", "galeta unu"),
]


def h(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)


def load_pool(raw: Path) -> tuple[dict, dict]:
    products: dict[str, dict] = {}
    by_query: dict[str, list[str]] = {}
    for f in sorted(raw.glob("search-*.json")):
        q = unicodedata.normalize("NFC", f.stem[len("search-"):])
        for page in json.loads(f.read_text()):
            for p in page.get("content", []):
                stores = sorted({x["marketAdi"] for x in p["productDepotInfoList"] if x["marketAdi"] in STORES})
                if not stores:
                    continue
                cur = products.setdefault(p["id"], {
                    "id": p["id"], "title": p["title"], "stores": [], "menu_category": p.get("menu_category"),
                    "main_category": p.get("main_category"), "quantity": p.get("refinedVolumeOrWeight"),
                })
                cur["stores"] = sorted(set(cur["stores"]) | set(stores))
                by_query.setdefault(q, [])
                if p["id"] not in by_query[q]:
                    by_query[q].append(p["id"])
    return products, by_query


def main(raw_dir: str) -> None:
    products, by_query = load_pool(Path(raw_dir))
    out = []
    for key, term, exclude, unit, query in INGREDIENTS:
        query = unicodedata.normalize("NFC", query)
        pool = by_query.get(query, [])
        if not pool:
            print("BİM/A101 ürünü yok, atlandı:", key)
            continue
        chosen: list[str] = []
        for store in STORES:
            ids = sorted((i for i in pool if store in products[i]["stores"]), key=lambda i: h(key + i))
            chosen += [i for i in ids[:PER_STORE] if i not in chosen]
            others = sorted((i for q, v in by_query.items() if q != query for i in v
                             if store in products[i]["stores"] and i not in pool), key=lambda i: h("d" + key + i))
            chosen += [i for i in others[:DISTRACTORS_PER_STORE] if i not in chosen]
        chosen.sort(key=lambda i: h("o" + key + i))  # sıra: sorgu/mağaza ipucu vermesin
        split = "holdout" if h("split:" + term) % 100 < HOLDOUT_SHARE * 100 else "dev"
        out.append({"key": key, "term": term, "exclude": exclude, "unit": unit, "split": split, "candidates": chosen})
    OUT.mkdir(parents=True, exist_ok=True)
    used = {i for e in out for i in e["candidates"]}
    (OUT / "products.json").write_text(json.dumps(sorted((products[i] for i in used), key=lambda p: p["id"]), ensure_ascii=False, indent=0))
    (OUT / "candidates.json").write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print(len(out), "ingredients,", sum(len(e["candidates"]) for e in out), "candidate rows,", len(used), "unique products,",
          sum(e["split"] == "holdout" for e in out), "holdout")


if __name__ == "__main__":
    main(sys.argv[1])
