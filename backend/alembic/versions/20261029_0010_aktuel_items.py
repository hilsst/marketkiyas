"""weekly aktüel (brochure) items of the chains

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-29 10:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'aktuel_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('market_slug', sa.String(length=32), nullable=False),
        sa.Column('source_key', sa.String(length=128), nullable=False),
        sa.Column('period_key', sa.String(length=64), nullable=False),
        sa.Column('period_label', sa.String(length=64), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=True),
        sa.Column('ends_on', sa.Date(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('brand', sa.String(length=120), nullable=True),
        sa.Column('quantity_text', sa.String(length=64), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('old_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('image_url', sa.String(length=1024), nullable=True),
        sa.Column('source_url', sa.String(length=1024), nullable=True),
        sa.Column('seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_aktuel_items')),
        sa.UniqueConstraint('market_slug', 'source_key', name='uq_aktuel_items_market_source'),
    )
    op.create_index('ix_aktuel_items_market_starts', 'aktuel_items', ['market_slug', 'starts_on'])


def downgrade() -> None:
    op.drop_index('ix_aktuel_items_market_starts', table_name='aktuel_items')
    op.drop_table('aktuel_items')
