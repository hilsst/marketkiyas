"""families: members see each other's lists without per-list codes

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-28 11:45:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'families',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('invite_code', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_families_owner_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_families')),
        sa.UniqueConstraint('invite_code', name=op.f('uq_families_invite_code')),
    )
    op.create_index(op.f('ix_families_owner_id'), 'families', ['owner_id'], unique=False)
    op.create_table(
        'family_members',
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], name=op.f('fk_family_members_family_id_families'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_family_members_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('family_id', 'user_id', name=op.f('pk_family_members')),
        sa.UniqueConstraint('user_id', name=op.f('uq_family_members_user_id')),
    )
    op.create_table(
        'family_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('invited_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], name=op.f('fk_family_invites_family_id_families'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], name=op.f('fk_family_invites_invited_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_family_invites')),
    )
    op.create_index(op.f('ix_family_invites_family_id'), 'family_invites', ['family_id'], unique=False)
    op.create_index(op.f('ix_family_invites_email'), 'family_invites', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_family_invites_email'), table_name='family_invites')
    op.drop_index(op.f('ix_family_invites_family_id'), table_name='family_invites')
    op.drop_table('family_invites')
    op.drop_table('family_members')
    op.drop_index(op.f('ix_families_owner_id'), table_name='families')
    op.drop_table('families')
