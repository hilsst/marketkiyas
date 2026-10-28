"""price alert can follow one chosen product (brand/market) instead of the cheapest

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-28 16:45:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('price_alerts', sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_price_alerts_product_id_products', 'price_alerts', 'products', ['product_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_price_alerts_product_id_products', 'price_alerts', type_='foreignkey')
    op.drop_column('price_alerts', 'product_id')
