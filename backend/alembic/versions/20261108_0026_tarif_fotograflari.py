"""Kullanıcı yemek fotoğrafları (yönetici onaylı)

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-08 12:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0026'
down_revision: str | None = '0025'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'recipe_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credit_name', sa.String(length=60), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='pending', nullable=False),
        sa.Column('reject_reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], name=op.f('fk_recipe_photos_recipe_id_recipes'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_recipe_photos_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recipe_photos')),
    )
    op.create_index(op.f('ix_recipe_photos_recipe_id'), 'recipe_photos', ['recipe_id'], unique=False)
    op.create_index(op.f('ix_recipe_photos_user_id'), 'recipe_photos', ['user_id'], unique=False)
    op.create_index(op.f('ix_recipe_photos_status'), 'recipe_photos', ['status'], unique=False)
    op.add_column('recipes', sa.Column('photo_id', sa.Integer(), nullable=True))
    op.add_column('recipes', sa.Column('photo_credit', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('recipes', 'photo_credit')
    op.drop_column('recipes', 'photo_id')
    op.drop_table('recipe_photos')
