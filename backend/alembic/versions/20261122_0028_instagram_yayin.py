"""Fotoğraflar: Instagram rızası ve yayın durumu

Revision ID: 0028
Revises: 0027
Create Date: 2026-11-22 18:30:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0028'
down_revision: str | None = '0027'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLS = ['ig_consent_at', 'ig_status', 'ig_container_id', 'ig_media_id', 'ig_permalink', 'ig_error',
        'ig_started_at', 'ig_published_at', 'ig_published_by']


def upgrade() -> None:
    # Eski fotoğraflar için rıza yok (false): yayınlanamazlar
    op.add_column('recipe_photos', sa.Column('ig_consent', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('recipe_photos', sa.Column('ig_consent_at', sa.DateTime(timezone=True)))
    op.add_column('recipe_photos', sa.Column('ig_status', sa.String(16)))
    op.add_column('recipe_photos', sa.Column('ig_container_id', sa.String(64)))
    op.add_column('recipe_photos', sa.Column('ig_media_id', sa.String(64)))
    op.add_column('recipe_photos', sa.Column('ig_permalink', sa.String(300)))
    op.add_column('recipe_photos', sa.Column('ig_error', sa.Text()))
    op.add_column('recipe_photos', sa.Column('ig_started_at', sa.DateTime(timezone=True)))
    op.add_column('recipe_photos', sa.Column('ig_published_at', sa.DateTime(timezone=True)))
    op.add_column('recipe_photos', sa.Column('ig_published_by', sa.Integer()))


def downgrade() -> None:
    for c in reversed(COLS):
        op.drop_column('recipe_photos', c)
    op.drop_column('recipe_photos', 'ig_consent')
