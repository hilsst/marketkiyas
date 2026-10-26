"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-25 21:07:27.419501

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MARKETS = [
    {"slug": "bim", "name": "BİM", "color": "#E30613", "website": "https://www.bim.com.tr"},
    {"slug": "a101", "name": "A101", "color": "#00A0E3", "website": "https://www.a101.com.tr"},
    {"slug": "sok", "name": "Şok", "color": "#FFD100", "website": "https://www.sokmarket.com.tr"},
    {"slug": "file", "name": "File", "color": "#00843D", "website": "https://www.file.com.tr"},
]

CATEGORIES = [
    ("sut-kahvaltilik", "Süt & Kahvaltılık", "🥛"),
    ("meyve-sebze", "Meyve & Sebze", "🥬"),
    ("et-tavuk-balik", "Et, Tavuk & Balık", "🍗"),
    ("temel-gida", "Temel Gıda", "🍝"),
    ("atistirmalik", "Atıştırmalık", "🍫"),
    ("icecek", "İçecek", "🥤"),
    ("firin", "Fırın & Unlu Mamul", "🍞"),
    ("dondurulmus", "Dondurulmuş", "🧊"),
    ("temizlik", "Temizlik", "🧽"),
    ("kisisel-bakim", "Kişisel Bakım", "🧴"),
    ("bebek", "Bebek", "🍼"),
]


def upgrade() -> None:
    # Ürün eşleştirme (fuzzy matching) için trigram desteği
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('icon', sa.String(length=16), nullable=True),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], name=op.f('fk_categories_parent_id_categories'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
    sa.UniqueConstraint('slug', name=op.f('uq_categories_slug'))
    )
    op.create_index(op.f('ix_categories_parent_id'), 'categories', ['parent_id'], unique=False)
    op.create_table('markets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('color', sa.String(length=16), nullable=True),
    sa.Column('logo_url', sa.String(length=512), nullable=True),
    sa.Column('website', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_markets')),
    sa.UniqueConstraint('slug', name=op.f('uq_markets_slug'))
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('product_groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('unit', sa.Enum('ml', 'g', 'adet', name='unit', native_enum=False, length=8), nullable=True),
    sa.Column('image_url', sa.String(length=1024), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_product_groups_category_id_categories'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_groups'))
    )
    op.create_index(op.f('ix_product_groups_category_id'), 'product_groups', ['category_id'], unique=False)
    op.create_index('ix_product_groups_normalized_name_trgm', 'product_groups', ['normalized_name'], unique=False, postgresql_using='gin', postgresql_ops={'normalized_name': 'gin_trgm_ops'})
    op.create_table('products',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('external_id', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('brand', sa.String(length=120), nullable=True),
    sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('unit', sa.Enum('ml', 'g', 'adet', name='unit', native_enum=False, length=8), nullable=True),
    sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('is_available', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('image_url', sa.String(length=1024), nullable=True),
    sa.Column('product_url', sa.String(length=1024), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_products_category_id_categories'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_products_market_id_markets'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
    sa.UniqueConstraint('market_id', 'external_id', name='uq_products_market_external')
    )
    op.create_index('ix_products_brand_lower', 'products', [sa.text("lower(brand)")], unique=False)
    op.create_index(op.f('ix_products_category_id'), 'products', ['category_id'], unique=False)
    op.create_index(op.f('ix_products_market_id'), 'products', ['market_id'], unique=False)
    op.create_index('ix_products_normalized_name_trgm', 'products', ['normalized_name'], unique=False, postgresql_using='gin', postgresql_ops={'normalized_name': 'gin_trgm_ops'})
    op.create_table('shopping_lists',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('icon', sa.String(length=16), nullable=True),
    sa.Column('status', sa.Enum('active', 'shopping', 'completed', name='liststatus', native_enum=False, length=16), server_default='active', nullable=False),
    sa.Column('applied_plan', sa.Enum('single_market', 'combination', 'opportunist', name='plantype', native_enum=False, length=16), nullable=True),
    sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_shopping_lists_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_shopping_lists'))
    )
    op.create_index('ix_shopping_lists_user_status', 'shopping_lists', ['user_id', 'status'], unique=False)
    op.create_table('group_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('match_score', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('is_manual', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['product_groups.id'], name=op.f('fk_group_members_group_id_product_groups'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_group_members_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_group_members')),
    sa.UniqueConstraint('product_id', name=op.f('uq_group_members_product_id'))
    )
    op.create_index(op.f('ix_group_members_group_id'), 'group_members', ['group_id'], unique=False)
    op.create_table('price_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('regular_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('is_campaign', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_price_history_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_price_history'))
    )
    op.create_index('ix_price_history_product_recorded', 'price_history', ['product_id', 'recorded_at'], unique=False)
    op.create_table('savings_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('list_id', sa.Integer(), nullable=True),
    sa.Column('list_name', sa.String(length=120), nullable=False),
    sa.Column('plan_type', sa.Enum('single_market', 'combination', 'opportunist', name='plantype', native_enum=False, length=16), nullable=False),
    sa.Column('preference_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('optimized_total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('saved_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('item_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('saved_amount >= 0', name=op.f('ck_savings_records_saved_amount_non_negative')),
    sa.ForeignKeyConstraint(['list_id'], ['shopping_lists.id'], name=op.f('fk_savings_records_list_id_shopping_lists'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_savings_records_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_savings_records'))
    )
    op.create_index('ix_savings_records_user_created', 'savings_records', ['user_id', 'created_at'], unique=False)
    op.create_index('uq_savings_records_list_id', 'savings_records', ['list_id'], unique=True, postgresql_where=sa.text('list_id IS NOT NULL'))
    op.create_table('shopping_list_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('list_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=8, scale=2), server_default='1', nullable=False),
    sa.Column('preferred_brand', sa.String(length=120), nullable=True),
    sa.Column('assigned_market_id', sa.Integer(), nullable=True),
    sa.Column('assigned_product_id', sa.Integer(), nullable=True),
    sa.Column('assigned_unit_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('is_checked', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('position', sa.Integer(), server_default='0', nullable=False),
    sa.Column('note', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['assigned_market_id'], ['markets.id'], name=op.f('fk_shopping_list_items_assigned_market_id_markets'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['assigned_product_id'], ['products.id'], name=op.f('fk_shopping_list_items_assigned_product_id_products'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['group_id'], ['product_groups.id'], name=op.f('fk_shopping_list_items_group_id_product_groups'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['list_id'], ['shopping_lists.id'], name=op.f('fk_shopping_list_items_list_id_shopping_lists'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_shopping_list_items'))
    )
    op.create_index(op.f('ix_shopping_list_items_list_id'), 'shopping_list_items', ['list_id'], unique=False)
    # ### end Alembic commands ###

    markets = sa.table(
        "markets",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("color", sa.String),
        sa.column("website", sa.String),
    )
    op.bulk_insert(markets, MARKETS)

    categories = sa.table(
        "categories",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("icon", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        categories,
        [
            {"slug": slug, "name": name, "icon": icon, "sort_order": i}
            for i, (slug, name, icon) in enumerate(CATEGORIES)
        ],
    )


def downgrade() -> None:

    op.drop_index(op.f('ix_shopping_list_items_list_id'), table_name='shopping_list_items')
    op.drop_table('shopping_list_items')
    op.drop_index('uq_savings_records_list_id', table_name='savings_records', postgresql_where=sa.text('list_id IS NOT NULL'))
    op.drop_index('ix_savings_records_user_created', table_name='savings_records')
    op.drop_table('savings_records')
    op.drop_index('ix_price_history_product_recorded', table_name='price_history')
    op.drop_table('price_history')
    op.drop_index(op.f('ix_group_members_group_id'), table_name='group_members')
    op.drop_table('group_members')
    op.drop_index('ix_shopping_lists_user_status', table_name='shopping_lists')
    op.drop_table('shopping_lists')
    op.drop_index('ix_products_normalized_name_trgm', table_name='products', postgresql_using='gin', postgresql_ops={'normalized_name': 'gin_trgm_ops'})
    op.drop_index(op.f('ix_products_market_id'), table_name='products')
    op.drop_index(op.f('ix_products_category_id'), table_name='products')
    op.drop_index('ix_products_brand_lower', table_name='products')
    op.drop_table('products')
    op.drop_index('ix_product_groups_normalized_name_trgm', table_name='product_groups', postgresql_using='gin', postgresql_ops={'normalized_name': 'gin_trgm_ops'})
    op.drop_index(op.f('ix_product_groups_category_id'), table_name='product_groups')
    op.drop_table('product_groups')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('markets')
    op.drop_index(op.f('ix_categories_parent_id'), table_name='categories')
    op.drop_table('categories')
    # ### end Alembic commands ###
