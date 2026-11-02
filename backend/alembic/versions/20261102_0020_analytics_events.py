"""analytics_events: funnel measurement (plan -> list -> shopping, week-4 return)

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-02 13:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0020'
down_revision: str | None = '0019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('source', sa.String(8), nullable=False),
        sa.Column('device_id', sa.String(64), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL',
                                                         name='fk_analytics_events_user_id_users'), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('props', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_analytics_events'),
    )
    op.create_index('ix_analytics_events_name_occurred_at', 'analytics_events', ['name', 'occurred_at'])
    op.create_index('ix_analytics_events_device_id', 'analytics_events', ['device_id'])
    op.create_index('ix_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('ix_analytics_events_occurred_at', 'analytics_events', ['occurred_at'])


def downgrade() -> None:
    op.drop_table('analytics_events')
