"""account recovery and social login: password reset codes, google/apple subject ids

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28 08:10:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Google/Apple ile giren kullanıcının şifresi olmaz
    op.alter_column('users', 'password_hash', existing_type=sa.String(255), nullable=True)
    op.add_column('users', sa.Column('google_sub', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('apple_sub', sa.String(255), nullable=True))
    op.create_unique_constraint(op.f('uq_users_google_sub'), 'users', ['google_sub'])
    op.create_unique_constraint(op.f('uq_users_apple_sub'), 'users', ['apple_sub'])
    op.create_table(
        'password_resets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_resets_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_password_resets')),
    )
    op.create_index(op.f('ix_password_resets_user_id'), 'password_resets', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_password_resets_user_id'), table_name='password_resets')
    op.drop_table('password_resets')
    op.drop_constraint(op.f('uq_users_apple_sub'), 'users', type_='unique')
    op.drop_constraint(op.f('uq_users_google_sub'), 'users', type_='unique')
    op.drop_column('users', 'apple_sub')
    op.drop_column('users', 'google_sub')
    op.execute("UPDATE users SET password_hash = '!' WHERE password_hash IS NULL")
    op.alter_column('users', 'password_hash', existing_type=sa.String(255), nullable=False)
