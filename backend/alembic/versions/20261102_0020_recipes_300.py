"""tarif kataloğu 84 -> 300+: Türk (Ramazan dahil), İtalyan, Uzak Doğu, Meksika

Tarif verisi alembic/recipe_data/ altındadır (malzeme sözlüğü + tarifler); alerjen, diyet ve besin değeri
malzemelerden hesaplanır. Veri bu göçe aittir: yayımlandıktan sonra değiştirilmez, yeni tarif için yeni göç yazılır.

- Yeni yan yemekler ve içecekler, uyan ana yemeklerle eşleşir (pairs_with); var olan yan yemeklere
  (pirinç pilavı, bulgur pilavı...) ve ayran/şalgama yeni ana yemekler eklenir.
- Mevcut bazı tariflere "ramazan" etiketi verilir.

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-02 13:30:00

"""
import sys
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recipe_data.turk_ana import ANA  # noqa: E402
from recipe_data.turk_ek import EK  # noqa: E402
from recipe_data.world import ASYA, ITALYAN, MEKSIKA  # noqa: E402

revision: str = '0020'
down_revision: str | None = '0019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW = ANA + EK + ITALYAN + ASYA + MEKSIKA

# Var olan yan yemek / içecek -> eşleşme grubu
EXISTING_PAIRS = {
    'pirinc-pilavi': 'pilav', 'bulgur-pilavi': 'bulgur', 'patates-puresi': 'puresi', 'tereyagli-makarna': 'makarna',
    'sarimsakli-ekmek': 'itekmek', 'yasemin-pilavi': 'asyapilav', 'meksika-pilavi': 'mxpilav',
    'ayran': 'ayran', 'salgam': 'salgam',
}
RAMAZAN_EXISTING = [
    'ezogelin-corbasi', 'mercimek-corbasi', 'tarhana-corbasi', 'domates-corbasi', 'yayla-corbasi', 'tavuk-corbasi',
    'sutlac', 'muhallebi', 'revani', 'kabak-tatlisi', 'irmik-helvasi', 'pirinc-pilavi', 'bulgur-pilavi',
    'mercimek-koftesi', 'kuru-fasulye', 'etli-nohut', 'manti', 'menemen', 'piyaz', 'kisir', 'coban-salatasi',
    'ayran', 'cevizli-yogurt', 'salgam',
]
INGREDIENT_COLS = (
    'recipe_id', 'position', 'name', 'amount_text', 'quantity', 'unit', 'search_term', 'exclude_terms',
    'categories', 'is_pantry',
)


def upgrade() -> None:
    conn = op.get_bind()
    cuisine_ids = dict(conn.execute(sa.text('SELECT slug, id FROM cuisines')).all())
    recipes = sa.table('recipes', *(sa.column(c) for c in (
        'id', 'cuisine_id', 'slug', 'name', 'course', 'course_type', 'pairs_with', 'meal_slots', 'servings',
        'prep_minutes', 'cook_minutes', 'description', 'steps', 'icon', 'is_active', 'allergens', 'diets',
        'kcal', 'protein_g', 'carbs_g', 'fat_g', 'popularity', 'tags',
    )))
    ingredients = sa.table('recipe_ingredients', *(sa.column(c) for c in INGREDIENT_COLS))

    existing_pairs = {
        slug: pairs for slug, pairs in conn.execute(sa.text(
            'SELECT slug, COALESCE(pairs_with, \'\') FROM recipes WHERE slug = ANY(:s)'
        ), {'s': list(EXISTING_PAIRS)}).all()
    }
    mains_by_group: dict[str, list[str]] = {}
    for r in NEW:
        if r['course_type'] == 'ana':
            for g in r['groups']:
                mains_by_group.setdefault(g, []).append(r['slug'])
    group_base = {g: existing_pairs.get(slug, '') for slug, g in EXISTING_PAIRS.items()}

    def paired(group: str) -> str:
        return ','.join([s for s in group_base.get(group, '').split(',') if s] + mains_by_group.get(group, []))

    for r in NEW:
        k, p, c, f = r['nutrition']
        pairs = paired(r['pair']) if r['course_type'] == 'yan' else None
        recipe_id = conn.execute(recipes.insert().returning(recipes.c.id), {
            'cuisine_id': cuisine_ids[r['cuisine']],
            'slug': r['slug'], 'name': r['name'], 'course': r['course'], 'course_type': r['course_type'],
            'pairs_with': pairs or None, 'meal_slots': r['meal_slots'], 'servings': r['servings'],
            'prep_minutes': r['prep'], 'cook_minutes': r['cook'], 'description': r['description'],
            'steps': '\n'.join(r['steps']), 'icon': r['icon'], 'is_active': True, 'allergens': r['allergens'],
            'diets': r['diets'], 'kcal': k, 'protein_g': p, 'carbs_g': c, 'fat_g': f,
            'popularity': r['popularity'], 'tags': r['tags'],
        }).scalar_one()
        conn.execute(ingredients.insert(), [
            dict(zip(INGREDIENT_COLS, (recipe_id, i, *row))) for i, row in enumerate(r['ingredients'])
        ])

    for slug, group in EXISTING_PAIRS.items():
        if slug in existing_pairs:
            conn.execute(sa.text('UPDATE recipes SET pairs_with = :p WHERE slug = :s'), {'p': paired(group), 's': slug})
    conn.execute(sa.text("UPDATE recipes SET tags = 'ramazan' WHERE slug = ANY(:s)"), {'s': RAMAZAN_EXISTING})


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [r['slug'] for r in NEW]
    conn.execute(sa.text(
        'DELETE FROM meal_plan_entries WHERE recipe_id IN (SELECT id FROM recipes WHERE slug = ANY(:s))'
    ), {'s': slugs})
    conn.execute(sa.text('DELETE FROM recipes WHERE slug = ANY(:s)'), {'s': slugs})
    removed = set(slugs)
    for slug, pairs in conn.execute(sa.text(
        "SELECT slug, pairs_with FROM recipes WHERE slug = ANY(:s)"
    ), {'s': list(EXISTING_PAIRS)}).all():
        kept = ','.join(s for s in (pairs or '').split(',') if s and s not in removed)
        conn.execute(sa.text('UPDATE recipes SET pairs_with = :p WHERE slug = :s'), {'p': kept or None, 's': slug})
    conn.execute(sa.text("UPDATE recipes SET tags = ''"))
