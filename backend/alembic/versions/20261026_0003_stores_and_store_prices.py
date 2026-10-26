"""stores and store prices

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-26 09:44:29.430719

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('stores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market_id', sa.Integer(), nullable=False),
    sa.Column('external_id', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('latitude', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('longitude', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_stores_market_id_markets'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stores')),
    sa.UniqueConstraint('external_id', name=op.f('uq_stores_external_id'))
    )
    op.create_index(op.f('ix_stores_market_id'), 'stores', ['market_id'], unique=False)
    op.create_table('store_prices',
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('store_id', sa.Integer(), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit_price', sa.String(length=64), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_store_prices_product_id_products'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], name=op.f('fk_store_prices_store_id_stores'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('product_id', 'store_id', name=op.f('pk_store_prices'))
    )
    op.create_index('ix_store_prices_store_id', 'store_prices', ['store_id'], unique=False)
    op.create_table('user_stores',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('store_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], name=op.f('fk_user_stores_store_id_stores'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_stores_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'store_id', name=op.f('pk_user_stores'))
    )
    op.add_column('shopping_list_items', sa.Column('assigned_store_id', sa.Integer(), nullable=True))
    op.create_foreign_key(op.f('fk_shopping_list_items_assigned_store_id_stores'), 'shopping_list_items', 'stores', ['assigned_store_id'], ['id'], ondelete='SET NULL')
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_constraint(op.f('fk_shopping_list_items_assigned_store_id_stores'), 'shopping_list_items', type_='foreignkey')
    op.drop_column('shopping_list_items', 'assigned_store_id')
    op.drop_table('user_stores')
    op.drop_index('ix_store_prices_store_id', table_name='store_prices')
    op.drop_table('store_prices')
    op.drop_index(op.f('ix_stores_market_id'), table_name='stores')
    op.drop_table('stores')
    # ### end Alembic commands ###
