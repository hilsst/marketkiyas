"""plan totals on shopping lists

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26 09:04:12.325370

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('shopping_lists', sa.Column('planned_total', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('shopping_lists', sa.Column('preference_total', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('shopping_lists', sa.Column('expected_savings', sa.Numeric(precision=10, scale=2), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column('shopping_lists', 'expected_savings')
    op.drop_column('shopping_lists', 'preference_total')
    op.drop_column('shopping_lists', 'planned_total')
    # ### end Alembic commands ###
