"""Tarif arama: recipes.search_text + trigram GIN indeksi

Revision ID: 0027
Revises: 0026
Create Date: 2026-11-08 14:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.services.normalize import normalize_text

revision: str = '0027'
down_revision: str | None = '0026'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.add_column('recipes', sa.Column('search_text', sa.Text(), server_default='', nullable=False))
    conn = op.get_bind()
    names = {}
    for rid, name in conn.execute(sa.text("SELECT id, name FROM recipes")):
        names[rid] = [name]
    for rid, name in conn.execute(sa.text("SELECT recipe_id, name FROM recipe_ingredients ORDER BY position")):
        names.setdefault(rid, []).append(name)
    for rid, parts in names.items():
        conn.execute(sa.text("UPDATE recipes SET search_text = :t WHERE id = :i"),
                     {"t": normalize_text(" ".join(parts)), "i": rid})
    op.execute(
        "CREATE INDEX ix_recipes_search_text_trgm ON recipes USING gin (search_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.drop_index('ix_recipes_search_text_trgm', table_name='recipes')
    op.drop_column('recipes', 'search_text')
