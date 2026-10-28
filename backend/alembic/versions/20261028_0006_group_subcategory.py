"""product group subcategory (alt kategori: Süt & Kahvaltılık > Peynir)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28 03:30:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('product_groups', sa.Column('subcategory_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_product_groups_subcategory_id'), 'product_groups', ['subcategory_id'], unique=False)
    op.create_foreign_key(
        op.f('fk_product_groups_subcategory_id_categories'), 'product_groups', 'categories',
        ['subcategory_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_product_groups_subcategory_id_categories'), 'product_groups', type_='foreignkey')
    op.drop_index(op.f('ix_product_groups_subcategory_id'), table_name='product_groups')
    op.drop_column('product_groups', 'subcategory_id')
