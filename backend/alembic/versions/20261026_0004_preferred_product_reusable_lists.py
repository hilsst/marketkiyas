"""preferred product on list items; lists are reusable every week

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-26 18:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('shopping_list_items', sa.Column('preferred_product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f('fk_shopping_list_items_preferred_product_id_products'),
        'shopping_list_items', 'products', ['preferred_product_id'], ['id'], ondelete='SET NULL',
    )
    # Liste her hafta yeniden kullanılabildiği için bir liste kasaya birden çok kez yazılabilir
    op.drop_index('uq_savings_records_list_id', table_name='savings_records')


def downgrade() -> None:
    op.create_index(
        'uq_savings_records_list_id', 'savings_records', ['list_id'], unique=True,
        postgresql_where=sa.text('list_id IS NOT NULL'),
    )
    op.drop_constraint(
        op.f('fk_shopping_list_items_preferred_product_id_products'), 'shopping_list_items', type_='foreignkey'
    )
    op.drop_column('shopping_list_items', 'preferred_product_id')
