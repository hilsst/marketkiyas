"""hafta içi yemekleri: 30 dakika civarında biten, malzemesi marketten alınan 28 tarif (pilot)

Yeni "Hafta İçi Yemekleri" mutfağı. Tarif verisi alembic/recipe_data/hafta_ici.py içindedir; alerjen, diyet ve
besin değeri malzemelerden hesaplanır. Veri bu göçe aittir: yayımlandıktan sonra değiştirilmez.

Revision ID: 0023
Revises: 0022
Create Date: 2026-11-04 18:00:00

"""
import sys
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recipe_data.hafta_ici import HAFTA_ICI  # noqa: E402

revision: str = '0023'
down_revision: str | None = '0022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CUISINE = ('haftaici', 'Hafta İçi Yemekleri', '⏱️', 4)
INGREDIENT_COLS = (
    'recipe_id', 'position', 'name', 'amount_text', 'quantity', 'unit', 'search_term', 'exclude_terms',
    'categories', 'is_pantry',
)


def upgrade() -> None:
    conn = op.get_bind()
    cuisines = sa.table('cuisines', *(sa.column(c) for c in ('slug', 'name', 'icon', 'is_default', 'is_active', 'position')))
    conn.execute(cuisines.insert(), [{
        'slug': CUISINE[0], 'name': CUISINE[1], 'icon': CUISINE[2], 'is_default': False, 'is_active': True,
        'position': CUISINE[3],
    }])
    cuisine_id = conn.execute(sa.text('SELECT id FROM cuisines WHERE slug = :s'), {'s': CUISINE[0]}).scalar_one()

    recipes = sa.table('recipes', *(sa.column(c) for c in (
        'id', 'cuisine_id', 'slug', 'name', 'course', 'course_type', 'pairs_with', 'meal_slots', 'servings',
        'prep_minutes', 'cook_minutes', 'description', 'steps', 'icon', 'is_active', 'allergens', 'diets',
        'kcal', 'protein_g', 'carbs_g', 'fat_g', 'popularity', 'tags',
    )))
    ingredients = sa.table('recipe_ingredients', *(sa.column(c) for c in INGREDIENT_COLS))
    for r in HAFTA_ICI:
        k, p, c, f = r['nutrition']
        recipe_id = conn.execute(recipes.insert().returning(recipes.c.id), {
            'cuisine_id': cuisine_id, 'slug': r['slug'], 'name': r['name'], 'course': r['course'],
            'course_type': r['course_type'], 'pairs_with': None, 'meal_slots': r['meal_slots'],
            'servings': r['servings'], 'prep_minutes': r['prep'], 'cook_minutes': r['cook'],
            'description': r['description'], 'steps': '\n'.join(r['steps']), 'icon': r['icon'], 'is_active': True,
            'allergens': r['allergens'], 'diets': r['diets'], 'kcal': k, 'protein_g': p, 'carbs_g': c, 'fat_g': f,
            'popularity': r['popularity'], 'tags': r['tags'],
        }).scalar_one()
        conn.execute(ingredients.insert(), [
            dict(zip(INGREDIENT_COLS, (recipe_id, i, *row))) for i, row in enumerate(r['ingredients'])
        ])


def downgrade() -> None:
    conn = op.get_bind()
    cid = '(SELECT id FROM cuisines WHERE slug = :s)'
    conn.execute(sa.text(f'DELETE FROM meal_plan_entries WHERE recipe_id IN (SELECT id FROM recipes WHERE cuisine_id = {cid})'), {'s': CUISINE[0]})
    conn.execute(sa.text(f'DELETE FROM meal_plans WHERE cuisine_id = {cid}'), {'s': CUISINE[0]})
    conn.execute(sa.text(f'DELETE FROM recipes WHERE cuisine_id = {cid}'), {'s': CUISINE[0]})
    conn.execute(sa.text('DELETE FROM cuisines WHERE slug = :s'), {'s': CUISINE[0]})
