"""indirimden menü + haftalık menü bildirimi + tarif etiketleri

- recipes.tags: özel dönem etiketi ("ramazan").
- meal_plans.from_deals: plan indirimdeki malzemelere öncelik verdi.
- push_tokens, notification_settings, notifications: haftalık menü bildirimi altyapısı.

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-02 13:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0021'
down_revision: str | None = '0020'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Yan yemeğin eşleştiği ana yemek listesi 255 karakteri aşıyor (pilav onlarca yemeğe uyar)
    op.alter_column('recipes', 'pairs_with', type_=sa.String(length=2000), existing_nullable=True)
    op.add_column('recipes', sa.Column('tags', sa.String(length=64), server_default='', nullable=False))
    op.add_column('meal_plans', sa.Column('from_deals', sa.Boolean(), server_default='false', nullable=False))
    op.create_table(
        'push_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False, unique=True),
        sa.Column('platform', sa.String(length=16), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_push_tokens_user_id', 'push_tokens', ['user_id'])
    op.create_table(
        'notification_settings',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('weekly_menu_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('weekly_menu_weekday', sa.Integer(), server_default='6', nullable=False),
        sa.Column('weekly_menu_hour', sa.Integer(), server_default='10', nullable=False),
    )
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('body', sa.String(length=255), nullable=False),
        sa.Column('data', sa.Text(), server_default='{}', nullable=False),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('meal_plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('pushed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('user_id', 'kind', 'week_start', name='uq_notifications_user_kind_week'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_table('notification_settings')
    op.drop_index('ix_push_tokens_user_id', table_name='push_tokens')
    op.drop_table('push_tokens')
    op.drop_column('meal_plans', 'from_deals')
    op.drop_column('recipes', 'tags')
    op.alter_column('recipes', 'pairs_with', type_=sa.String(length=255), existing_nullable=True)
