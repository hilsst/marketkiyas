"""pantry: quantity may be unknown (ingredients ticked in "Dolabımda ne var")

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-31 23:30:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0018'
down_revision: str | None = '0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column('pantry_items', 'quantity', existing_type=sa.Numeric(10, 2), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM pantry_items WHERE quantity IS NULL")
    op.alter_column('pantry_items', 'quantity', existing_type=sa.Numeric(10, 2), nullable=False)
