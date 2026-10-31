"""recipe ingredients: allowed product categories (limon only from Meyve & Sebze, not "Ice Tea Limon")

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-31 18:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0014'
down_revision: str | None = '0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEBZE = 'meyve-sebze'
TEMEL = 'temel-gida'
SUT = 'sut-kahvaltilik'
ET = 'et-tavuk-balik'
ICECEK = 'icecek'
ATISTIRMALIK = 'atistirmalik'
FIRIN = 'firin'
DONDURULMUS = 'dondurulmus'

# Malzemenin arama ifadesi -> ürünün olabileceği kategoriler. Kategorisi bilinen bir ürün bu listede
# değilse malzeme sayılmaz ("Ice Tea Limon" İçecek'te, limon yalnız Meyve & Sebze'den gelir).
# Kategorisi bilinmeyen ürünlerde yalnız kelime kuralları geçerlidir.
CATEGORIES = {
    'arpa sehriye|sehriye': [TEMEL],
    'aycicek yagi': [TEMEL],
    'ayran': [ICECEK, SUT],
    'bal': [SUT, TEMEL],
    'bal kabagi|balkabagi': [SEBZE],
    'beyaz peynir': [SUT],
    'bugday unu': [TEMEL],
    'bulgur': [TEMEL],
    'cay': [ICECEK, TEMEL],
    'ceviz ici|ceviz': [ATISTIRMALIK, TEMEL, SEBZE],
    'dana kiyma|kiyma': [ET],
    'dana kusbasi|kusbasi': [ET],
    'domates': [SEBZE],
    'domates salcasi': [TEMEL],
    'ekmek': [FIRIN],
    'elma': [SEBZE],
    'galeta unu': [TEMEL, FIRIN],
    'havuc': [SEBZE],
    'irmik': [TEMEL],
    'ispanak': [SEBZE],
    'kabartma tozu': [TEMEL],
    'karabiber': [TEMEL],
    'kasar peyniri|kasar': [SUT],
    'kekik': [TEMEL],
    'kimyon': [TEMEL],
    'kirmizi mercimek': [TEMEL],
    'koftelik bulgur|ince bulgur': [TEMEL],
    'kuru fasulye': [TEMEL],
    'kuru sogan': [SEBZE],
    'kuzu kusbasi|dana kusbasi|kusbasi': [ET],
    'limon': [SEBZE],
    'maden suyu|soda': [ICECEK],
    'makarna|spagetti|penne': [TEMEL],
    'mandalina': [SEBZE],
    'manti': [TEMEL, DONDURULMUS],
    'marul|kivircik': [SEBZE],
    'maydanoz': [SEBZE],
    'misir nisastasi|nisasta': [TEMEL],
    'muz': [SEBZE],
    'nane': [TEMEL],
    'nar eksisi': [TEMEL],
    'nisasta': [TEMEL],
    'nohut': [TEMEL],
    'patates': [SEBZE],
    'patlican': [SEBZE],
    'pilavlik bulgur|bulgur': [TEMEL],
    'pirinc': [TEMEL],
    'pirinc unu': [TEMEL],
    'portakal suyu': [ICECEK],
    'pul biber': [TEMEL],
    'roka': [SEBZE],
    'salatalik': [SEBZE],
    'salgam suyu|salgam': [ICECEK],
    'sarimsak': [SEBZE],
    'sivri biber': [SEBZE],
    'siyah zeytin|zeytin': [SUT, TEMEL],
    'sucuk': [ET, SUT],
    'sut': [SUT],
    'tarcin': [TEMEL],
    'tarhana': [TEMEL],
    'tavuk baget|pilic baget|baget': [ET],
    'tavuk gogus|pilic gogus': [ET],
    'taze fasulye|ayse fasulye': [SEBZE],
    'tereyagi': [SUT],
    'toz seker': [TEMEL],
    'tuz': [TEMEL],
    'yesil sogan|taze sogan': [SEBZE],
    'yogurt': [SUT],
    'yumurta': [SUT],
    'zeytinyagi': [TEMEL],
}


def upgrade() -> None:
    op.add_column('recipe_ingredients', sa.Column('categories', sa.String(length=128), nullable=True))
    conn = op.get_bind()
    for term, slugs in CATEGORIES.items():
        conn.execute(
            sa.text('UPDATE recipe_ingredients SET categories = :c WHERE search_term = :t'),
            {'c': ','.join(slugs), 't': term},
        )


def downgrade() -> None:
    op.drop_column('recipe_ingredients', 'categories')
