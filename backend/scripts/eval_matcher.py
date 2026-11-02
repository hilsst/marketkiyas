"""Eşleştirici (app.services.ingredient_match) bağımsız değerlendirmesi — BİM ve A101 gerçek ürün adları.

Küme: tests/fixtures/matcher_eval/{labels,products}.json (ölçütü: RUBRIC.md). Etiketler eşleştirici çalıştırılmadan
önce donduruldu. Bu araç yalnızca ÖLÇER; eşleştirici veya etiket ayarı için kullanılmamalıdır. `holdout` bölümü
(arama ifadesinin hash'ine göre ~%30) ayar sırasında hiç çalıştırılmamalı: yalnızca son ölçüm için.

İki mod:
  ad      : app.services.ingredient_match.accepts (kategori bilgisi yok; mevcut 202'lik küme testiyle aynı yol)
  kategori: marketfiyati menu_category'si bilinir -> temizlik/kişisel bakım elenir, grocery_like(category_known=True)
            (üretimdeki meals._groups_for'un yaklaşığı; malzeme kategori listesi eşlenemediği için uygulanmaz)

Kullanım: python scripts/eval_matcher.py [--split dev|holdout|all] [--mode ad|kategori] [--errors]
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingredient_match import accepts, grocery_like, name_matches, unit_compatible  # noqa: E402
from app.services.normalize import normalize_text, parse_quantity  # noqa: E402

DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "matcher_eval"
NON_FOOD_MENUS = {"Temizlik Ürünleri", "Kişisel Bakım"}


def load():
    labels = json.loads((DIR / "labels.json").read_text())
    products = {p["id"]: p for p in json.loads((DIR / "products.json").read_text())}
    return labels, products


def decide(entry: dict, product: dict, mode: str) -> bool:
    excludes = tuple(normalize_text(e) for e in entry["exclude"].split(",") if e.strip())
    if mode == "ad":
        return accepts(entry["term"], product["title"], excludes, entry["unit"])
    if product.get("menu_category") in NON_FOOD_MENUS:
        return False
    if not grocery_like(product["title"], None, category_known=True):
        return False
    parsed = parse_quantity(product["title"])
    if parsed is not None and not unit_compatible(entry["unit"], parsed[1]):
        return False
    return any(name_matches(a.strip(), product["title"], excludes) for a in entry["term"].split("|") if a.strip())


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def evaluate(split: str = "dev", mode: str = "ad") -> dict:
    labels, products = load()
    result = {}
    for store in ("bim", "a101", "all"):
        ing_pass = ing_total = tp = fp = fn = tn = 0
        failures = []
        for e in labels:
            if split != "all" and e["split"] != split:
                continue
            scored = [(products[p["id"]], p["ok"]) for p in e["products"] if p["ok"] is not None
                      and (store == "all" or store in products[p["id"]]["stores"])]
            if not scored:
                continue
            verdicts = [(pr, ok, decide(e, pr, mode)) for pr, ok in scored]
            wrong = [pr["title"] for pr, ok, got in verdicts if got and not ok]
            missed_all = any(ok for _, ok, _ in verdicts) and not any(ok and got for _, ok, got in verdicts)
            ing_total += 1
            ing_pass += not wrong and not missed_all
            for pr, ok, got in verdicts:
                tp += ok and got
                fp += (not ok) and got
                fn += ok and not got
                tn += (not ok) and not got
            if wrong or missed_all:
                failures.append({"key": e["key"], "false_accept": wrong,
                                 "missed_all": missed_all,
                                 "rejected_ok": [pr["title"] for pr, ok, got in verdicts if ok and not got]})
        result[store] = {
            "ingredients": ing_total, "ingredient_accuracy": ing_pass / ing_total if ing_total else None,
            "ingredient_ci95": wilson(ing_pass, ing_total), "products": tp + fp + fn + tn,
            "precision": tp / (tp + fp) if tp + fp else None, "precision_ci95": wilson(tp, tp + fp),
            "recall": tp / (tp + fn) if tp + fn else None, "recall_ci95": wilson(tp, tp + fn),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn, "failures": failures,
        }
    return result


def _fmt(x):
    return "-" if x is None else f"{x:.1%}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "holdout", "all"])
    ap.add_argument("--mode", default="ad", choices=["ad", "kategori"])
    ap.add_argument("--errors", action="store_true")
    a = ap.parse_args()
    sha = subprocess.run(["git", "log", "-1", "--format=%h", "--", "app/services/ingredient_match.py"],
                         capture_output=True, text=True, cwd=DIR.parent.parent.parent).stdout.strip()
    print(f"eşleştirici sürümü (son değiştiren commit): {sha}  bölüm={a.split}  mod={a.mode}")
    res = evaluate(a.split, a.mode)
    for store, r in res.items():
        lo, hi = r["ingredient_ci95"]
        print(f"[{store}] malzeme={r['ingredients']} doğruluk={_fmt(r['ingredient_accuracy'])} (%95 GA {lo:.0%}-{hi:.0%}) "
              f"| ürün={r['products']} kesinlik={_fmt(r['precision'])} duyarlılık={_fmt(r['recall'])} "
              f"(tp={r['tp']} fp={r['fp']} fn={r['fn']})")
        if a.errors:
            for f in r["failures"]:
                print("   ", f["key"], "YANLIŞ KABUL:", f["false_accept"], "| REDDEDİLEN UYGUN:", f["rejected_ok"])


if __name__ == "__main__":
    main()
