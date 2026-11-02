"""Malzeme eşleştirme doğruluğu: 200+ malzemelik örnek küme (hedef >= %95).

tests/fixtures/ingredient_match_set.json: her kayıt bir tarif malzemesi (arama ifadesi, elenecek kelimeler) ve
Şok kataloğundaki gerçek ürün adlarından seçilmiş örnekler; `ok` = bu ürün bu malzeme yerine alınabilir mi.
Etiketler eşleştirici ayarlanmadan önce, yalnızca ürün adlarına bakılarak verildi.

Bir malzeme şu durumda doğru sayılır: kabul edilen ürünlerin hiçbiri yanlış değil ve (uygun ürün varsa)
en az biri kabul edildi. Maliyet motoru en ucuz kabul edilen ürünü seçtiği için tek bir yanlış ürün de
"zeytinyağı -> sıvı sabun" hatasına yol açar.
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import RecipeIngredient
from app.services.ingredient_match import accepts
from app.services.normalize import normalize_text

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "ingredient_match_set.json").read_text())
TARGET = 0.95


def _excludes(entry: dict) -> tuple[str, ...]:
    return tuple(normalize_text(e) for e in entry["exclude"].split(",") if e.strip())


def _verdict(entry: dict) -> tuple[bool, list[str], list[str]]:
    excludes = _excludes(entry)
    wrong = [p["name"] for p in entry["products"] if not p["ok"] and accepts(entry["term"], p["name"], excludes, entry["unit"])]
    has_ok = any(p["ok"] for p in entry["products"])
    missed = has_ok and not any(p["ok"] and accepts(entry["term"], p["name"], excludes, entry["unit"]) for p in entry["products"])
    return not wrong and not missed, wrong, (["(hiçbir uygun ürün kabul edilmedi)"] if missed else [])


def test_fixture_has_at_least_200_ingredients():
    keys = {(e["term"], e["exclude"]) for e in FIXTURE}
    assert len(keys) == len(FIXTURE) >= 200


def test_matching_accuracy_target():
    failures = []
    for entry in FIXTURE:
        passed, wrong, missed = _verdict(entry)
        if not passed:
            failures.append(f"{entry['term']!r}: yanlış kabul={wrong} {missed}")
    accuracy = 1 - len(failures) / len(FIXTURE)
    report = "\n".join(failures)
    assert accuracy >= TARGET, f"doğruluk {accuracy:.1%} < {TARGET:.0%}, {len(failures)} hata:\n{report}"


def test_no_wrong_product_is_ever_accepted_for_core_staples():
    """Pazarlık yok: en sık kullanılan temel malzemelerde yanlış ürün kabul edilmez."""
    core = {"zeytinyagi", "limon", "domates", "sut", "yumurta", "tereyagi", "pirinc", "aycicek yagi", "tuz"}
    for entry in FIXTURE:
        if entry["term"] in core:
            passed, wrong, missed = _verdict(entry)
            assert passed, f"{entry['term']}: {wrong} {missed}"


async def test_fixture_covers_every_recipe_ingredient(db):
    """Göçle gelen her (arama ifadesi, elenecek kelimeler) çifti örnek kümede olmalı; yeni tarif eklenince
    küme de büyüsün."""
    rows = (await db.execute(
        select(RecipeIngredient.search_term, RecipeIngredient.exclude_terms).where(~RecipeIngredient.is_pantry).distinct()
    )).all()
    covered = {e["term"] for e in FIXTURE}
    missing = sorted({term for term, _ in rows} - covered)
    assert not missing, f"örnek kümede olmayan malzemeler: {missing}"
