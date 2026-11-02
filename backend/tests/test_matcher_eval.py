"""Bağımsız eşleştirme değerlendirmesi (BİM/A101 gerçek ürün adları) — rapor odaklı, gevşek tabanlı test.

Bu test eşleştirici için bir HEDEF koymaz (hedef koymak bu kümeyi de ikinci bir "ayar kümesi" yapar). Yalnızca:
- kümenin bütünlüğünü korur (etiketler sessizce değiştirilemez: labels.json SHA-256 sabitlenir),
- `dev` bölümünde ölçülen doğruluğun gevşek bir tabanın altına düşmediğini (gerileme) doğrular.
`holdout` bölümü testte ÇALIŞTIRILMAZ: yalnızca `python scripts/eval_matcher.py --split holdout` ile, son ölçüm için.
Sonuçlar ve hata kategorileri: tests/fixtures/matcher_eval/README.md
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import eval_matcher as ev  # noqa: E402

PRODUCTS_SHA256 = "7538832182c64b2cb2f8b6205a06360aae0b6a90ed8db579cc9a734d7e39307d"
LABELS_SHA256 = "3201c13059dd0d7daf461302401a93ecd7a6afe31d0137f24047f55d101e4961"
# Ölçülen dev değerlerinin (ilk ölçüm: malzeme %83,3, kesinlik %93,7, duyarlılık %96,3) yaklaşık 10 puan altı
DEV_ACCURACY_FLOOR = 0.70
DEV_PRECISION_FLOOR = 0.85
DEV_RECALL_FLOOR = 0.85


def test_labels_are_frozen():
    assert hashlib.sha256((ev.DIR / "labels.json").read_bytes()).hexdigest() == LABELS_SHA256, (
        "labels.json değişti: etiketler eşleştirici çıktısına bakılarak değiştirilmemeli. Bilinçli bir yeniden "
        "etiketleme ise README'ye gerekçeyi yazıp LABELS_SHA256'yı güncelleyin."
    )


def test_products_are_frozen():
    assert hashlib.sha256((ev.DIR / "products.json").read_bytes()).hexdigest() == PRODUCTS_SHA256, (
        "products.json değişti: ürün adları gerçek API yanıtlarından (raw_manifest.json) gelmeli; elle değiştirilmemeli."
    )


def test_set_structure():
    labels, products = ev.load()
    assert len(labels) >= 50
    assert {e["split"] for e in labels} == {"dev", "holdout"}
    for e in labels:
        for p in e["products"]:
            prod = products[p["id"]]
            assert prod["stores"] and set(prod["stores"]) <= {"bim", "a101"}
            assert p["ok"] in (True, False, None)
    assert sum(p["ok"] is True for e in labels for p in e["products"]) >= 250


def test_dev_split_does_not_regress():
    res = ev.evaluate("dev", "ad")
    assert res["all"]["ingredient_accuracy"] >= DEV_ACCURACY_FLOOR
    for store in ("bim", "a101"):
        assert res[store]["precision"] >= DEV_PRECISION_FLOOR, store
        assert res[store]["recall"] >= DEV_RECALL_FLOOR, store
