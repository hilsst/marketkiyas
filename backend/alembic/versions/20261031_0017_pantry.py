"""pantry: leftovers from bought packages carried into the next meal plans

- pantry_items: kullanıcının dolabı (artan malzeme, miktar, birim, son kullanma günü).
- meal_plans.stock_used: plan listeye aktarılınca dolaptan kullandıkları (JSON); NULL = aktarılmadı.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-31 23:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0017'
down_revision: str | None = '0016'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'pantry_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(length=120), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit', sa.Enum('ml', 'g', 'adet', name='unit', native_enum=False, length=8), nullable=False),
        sa.Column('expires_on', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'key', 'unit', name='uq_pantry_user_key_unit'),
    )
    op.create_index('ix_pantry_items_user_id', 'pantry_items', ['user_id'])
    op.add_column('meal_plans', sa.Column('stock_used', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('meal_plans', 'stock_used')
    op.drop_index('ix_pantry_items_user_id', table_name='pantry_items')
    op.drop_table('pantry_items')
