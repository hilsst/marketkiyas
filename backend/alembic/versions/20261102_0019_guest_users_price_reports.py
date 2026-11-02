"""guest users (account asked at save/share) and "this price is wrong" reports

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-02 13:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0019'
down_revision: str | None = '0018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_guest', sa.Boolean(), server_default='false', nullable=False))
    # Misafirin e-postası yok (benzersizlik NULL'ları karşılaştırmaz)
    op.alter_column('users', 'email', existing_type=sa.String(320), nullable=True)
    op.create_table(
        'price_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('store_id', sa.Integer(), nullable=True),
        sa.Column('shown_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('reported_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('note', sa.String(length=300), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='open', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_price_reports_user_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['group_id'], ['product_groups.id'], name=op.f('fk_price_reports_group_id_product_groups'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_price_reports_product_id_products'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], name=op.f('fk_price_reports_store_id_stores'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_price_reports')),
    )
    op.create_index(op.f('ix_price_reports_user_id'), 'price_reports', ['user_id'])
    op.create_index(op.f('ix_price_reports_product_id'), 'price_reports', ['product_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_price_reports_product_id'), table_name='price_reports')
    op.drop_index(op.f('ix_price_reports_user_id'), table_name='price_reports')
    op.drop_table('price_reports')
    op.execute("DELETE FROM users WHERE email IS NULL")
    op.alter_column('users', 'email', existing_type=sa.String(320), nullable=False)
    op.drop_column('users', 'is_guest')
