"""0025 göçünün verisi: her değişiklik gerçek bir adıma denk gelir ve sayaç kurulabilecek bir süre içerir."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "alembic"))

from recipe_data.hafta_ici import HAFTA_ICI  # noqa: E402
from recipe_data.sureler import SURELER  # noqa: E402
from recipe_data.turk_ana import ANA  # noqa: E402
from recipe_data.turk_ek import EK  # noqa: E402
from recipe_data.world import ASYA, ITALYAN, MEKSIKA  # noqa: E402

RECIPES = {r["slug"]: r for data in (ANA, EK, ITALYAN, ASYA, MEKSIKA, HAFTA_ICI) for r in data}
DURATION = re.compile(r"\d+(?:\s*[-–]\s*\d+)?\s*(dakika|saat|saniye)")
# Mobil stepTimers: ısıtma ("fırını ısıtın") ve "bitmesine ... kala" cümleleri sayaç kurmaz
PREHEAT = re.compile(r"ısıt", re.I)
COOK_VERBS = re.compile(r"(pişir|fırınla|fırında|bekle|kavur|kaynat|haşla)", re.I)


def test_every_change_targets_a_real_step():
    for slug, steps in SURELER.items():
        assert slug in RECIPES, slug
        for idx in steps:
            assert idx < len(RECIPES[slug]["steps"]), (slug, idx)


def test_every_new_step_has_a_timer_duration():
    for slug, steps in SURELER.items():
        for idx, text in steps.items():
            assert DURATION.search(text), (slug, idx, text)
            for sentence in re.split(r"[.!?]\s+", text):
                assert not (PREHEAT.search(sentence) and not COOK_VERBS.search(sentence)), (slug, idx, text)
            assert not re.search(r"\bkala\b", text), (slug, idx, text)


def test_only_cold_or_trivial_recipes_stay_without_a_timer():
    """Süresiz kalan tarifler çiğ salata, soğuk içecek, ara sıcak ya da pişmeyen yan yemek olmalı."""
    for slug, r in RECIPES.items():
        if slug in SURELER or any(DURATION.search(step) for step in r["steps"]):
            continue
        assert r["course_type"] in ("salata", "icecek", "ara") or r["cook"] == 0, slug
