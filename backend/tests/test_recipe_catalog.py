"""Tarif kataloğunun (migrasyonla gelen veri) değişmezleri: sayı, Türk ağırlığı, alerjen/diyet/besin tutarlılığı."""

from collections import Counter

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Allergen, CourseType, Diet, Recipe

TURKISH = {"anadolu"}
ANIMAL = {"sut", "yumurta"}
MEAT_WORDS = ("kıyma", "tavuk", "piliç", "dana", "kuzu", "balık", "sucuk", "pastırma", "somon", "ton balığı", "karides")


@pytest.fixture
async def recipes(db):
    return list((await db.scalars(
        select(Recipe).options(selectinload(Recipe.ingredients), selectinload(Recipe.cuisine))
    )).all())


async def test_catalog_size_and_turkish_weight(recipes):
    assert len(recipes) >= 300
    turkish = [r for r in recipes if r.cuisine.slug in TURKISH]
    assert len(turkish) >= 150
    assert sum("ramazan" in r.tags.split(",") for r in recipes) >= 15
    assert len({r.slug for r in recipes}) == len(recipes)


async def test_every_recipe_is_complete(recipes):
    for r in recipes:
        assert r.steps and r.name and r.description, r.slug
        assert r.servings >= 1 and r.ingredients, r.slug
        assert None not in (r.kcal, r.protein_g, r.carbs_g, r.fat_g), f"{r.slug}: besin değeri eksik"
        low = 0 if r.course_type is CourseType.DRINK else 30  # maden suyu gibi içecekler 0 kcal
        assert low <= r.kcal <= 1500, f"{r.slug}: kcal {r.kcal}"
        assert all(i.search_term for i in r.ingredients), r.slug


async def test_pools_per_diet_and_course(recipes):
    # Her diyet için her öğün tipinde seçilecek yemek var (vegan kahvaltı hariç yemek tipleri)
    for diet in (Diet.VEGETARIAN, Diet.VEGAN, Diet.GLUTEN_FREE):
        suited = [r for r in recipes if r.suits([diet], [])]
        by_course = Counter(r.course_type for r in suited)
        assert len(suited) >= 40, diet
        for course in (CourseType.MAIN, CourseType.SOUP, CourseType.SALAD):
            assert by_course[course] >= 3, (diet, course)


async def test_diet_and_allergen_consistency(recipes):
    for r in recipes:
        diets = {d.value for d in r.diet_list}
        allergens = {a.value for a in r.allergen_list}
        text = " ".join(i.name.lower() for i in r.ingredients)
        if "vegan" in diets:
            assert not allergens & ANIMAL, f"{r.slug}: vegan ama {allergens & ANIMAL}"
            assert not any(w in text for w in MEAT_WORDS), r.slug
        if "vejetaryen" in diets:
            assert not any(w in text for w in MEAT_WORDS), f"{r.slug}: vejetaryen ama et var"
        if "glutensiz" in diets:
            assert "gluten" not in allergens, r.slug
        for a in allergens:
            Allergen(a)  # bilinmeyen alerjen yok


async def test_pairs_point_to_existing_recipes(recipes):
    slugs = {r.slug for r in recipes}
    for r in recipes:
        if r.pairs_with:
            missing = [s for s in r.pairs_with.split(",") if s not in slugs]
            assert not missing, f"{r.slug}: olmayan eşleşme {missing}"
    # Yan yemek ve içecek havuzu çeşitli
    sides = [r for r in recipes if r.course_type in (CourseType.SIDE, CourseType.DRINK)]
    assert len(sides) >= 12
