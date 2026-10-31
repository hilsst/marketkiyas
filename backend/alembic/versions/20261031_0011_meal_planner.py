"""meal planner: cuisines, recipes, ingredients, meal plans (+ 5 Anatolian recipes)

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-31 09:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Yeni bir mutfak eklemek için buraya (ya da yeni bir migration'a) satır ve tarifler eklenir.
CUISINES = [
    # slug, ad, simge, varsayılan mı, sıra
    ('anadolu', 'Anadolu (Türk) Mutfağı', '🇹🇷', True, 0),
]

# Arama ifadesi "|" ile alternatif alabilir; grup adı ifadenin bütün kelimelerini içermelidir.
# Malzeme: (ad, tarifteki ölçü, temel birimde miktar, birim, arama ifadesi, elenecek kelimeler, evde var mı)
# Miktarlar tarifin porsiyonu içindir; plan kişi sayısına göre orantılanır.
RECIPES = [
    {
        'slug': 'mercimek-corbasi',
        'name': 'Mercimek Çorbası',
        'course': 'Çorba',
        'meal_slots': 'ogle,aksam',
        'servings': 4,
        'prep_minutes': 10,
        'cook_minutes': 30,
        'icon': '🥣',
        'description': 'Kırmızı mercimek, soğan, havuç ve patatesle pürüzsüz, limonla servis edilen klasik çorba.',
        'steps': [
            'Mercimeği bol suda yıkayıp süzün.',
            'Tereyağını tencerede eritin, doğranmış soğanı pembeleşene kadar kavurun.',
            'Unu ekleyip kokusu çıkana kadar 1 dakika kavurun.',
            'Küp doğranmış havuç ve patatesi, ardından mercimeği ekleyip karıştırın.',
            '6 su bardağı sıcak su ve tuzu ekleyin; kapağı kapalı, kısık ateşte 25-30 dakika pişirin.',
            'Blenderdan geçirin; kıvamı koyuysa biraz sıcak su ekleyip bir taşım daha kaynatın.',
            'Üzerine pul biberli tereyağı gezdirip limonla servis edin.',
        ],
        'ingredients': [
            ('Kırmızı mercimek', '1 su bardağı', 200, 'g', 'kirmizi mercimek', None, False),
            ('Kuru soğan', '1 adet', 150, 'g', 'kuru sogan', 'toz,granul', False),
            ('Havuç', '1 adet', 100, 'g', 'havuc', 'suyu,bebek', False),
            ('Patates', '1 adet', 150, 'g', 'patates', 'cips,kizartma,dondurulmus,pure', False),
            ('Tereyağı', '2 yemek kaşığı', 30, 'g', 'tereyagi', None, False),
            ('Buğday unu', '1 yemek kaşığı', 15, 'g', 'bugday unu', None, False),
            ('Limon', '1 adet', 100, 'g', 'limon', 'sosu,kolonya,tuzu,suyu,aromali', False),
            ('Tuz', '1 tatlı kaşığı', 5, 'g', 'tuz', 'tuzsuz,tuzlu', True),
            ('Pul biber', '1 çay kaşığı', 2, 'g', 'pul biber', None, True),
        ],
    },
    {
        'slug': 'kuru-fasulye',
        'name': 'Kuru Fasulye',
        'course': 'Ana yemek',
        'meal_slots': 'ogle,aksam',
        'servings': 4,
        'prep_minutes': 15,
        'cook_minutes': 90,
        'icon': '🫘',
        'description': 'Bir gece önceden ıslatılan fasulyeyle salçalı, ağır ateşte pişen Anadolu klasiği.',
        'steps': [
            'Fasulyeyi bir gece önceden bol suda ıslatın.',
            'Ertesi gün süzüp haşlayın, ilk kaynama suyunu dökün.',
            'Tencerede sıvı yağı ısıtın, doğranmış soğanı kavurun.',
            'Salçayı ekleyip kokusu çıkana kadar kavurun.',
            'Fasulyeyi ve üzerini 2 parmak geçecek kadar sıcak su ekleyin.',
            'Kısık ateşte fasulyeler yumuşayana kadar 60-90 dakika pişirin; tuzu en son ekleyin.',
            'Tereyağında pul biber kızdırıp üzerine gezdirerek pilavla servis edin.',
        ],
        'ingredients': [
            ('Kuru fasulye', '2 su bardağı', 400, 'g', 'kuru fasulye', 'konserve,haslanmis', False),
            ('Kuru soğan', '1 adet', 150, 'g', 'kuru sogan', 'toz,granul', False),
            ('Domates salçası', '2 yemek kaşığı', 40, 'g', 'domates salcasi', None, False),
            ('Ayçiçek yağı', '3 yemek kaşığı', 45, 'ml', 'aycicek yagi', None, False),
            ('Tereyağı', '1 yemek kaşığı', 15, 'g', 'tereyagi', None, False),
            ('Tuz', '1 tatlı kaşığı', 5, 'g', 'tuz', 'tuzsuz,tuzlu', True),
            ('Pul biber', '1 çay kaşığı', 2, 'g', 'pul biber', None, True),
        ],
    },
    {
        'slug': 'karniyarik',
        'name': 'Karnıyarık',
        'course': 'Ana yemek',
        'meal_slots': 'aksam',
        'servings': 4,
        'prep_minutes': 20,
        'cook_minutes': 45,
        'icon': '🍆',
        'description': 'Kızarmış patlıcanların kıymalı, domatesli harçla doldurulup fırınlandığı yemek.',
        'steps': [
            'Patlıcanları alacalı soyun, tuzlu suda 20 dakika bekletip kurulayın.',
            'Patlıcanları kızgın yağda her tarafı kızarana kadar kızartın, kağıt havluya alın.',
            'Ayrı tavada doğranmış soğanı ve sarımsağı kavurun, kıymayı ekleyip suyunu çekene kadar pişirin.',
            'Doğranmış biberin yarısını ve domatesin yarısını, salçayı, tuz ve karabiberi ekleyip 5 dakika pişirin.',
            'Patlıcanların ortasını kaşıkla açıp harcı doldurun; üzerine domates ve biber dilimi koyun.',
            'Yarım su bardağı sıcak suya biraz salça açıp tepsiye dökün.',
            '180 derece fırında 25-30 dakika pişirin.',
        ],
        'ingredients': [
            ('Patlıcan', '6 adet', 1200, 'g', 'patlican', 'salata,kozlenmis,konserve,tursu', False),
            ('Dana kıyma', '250 g', 250, 'g', 'dana kiyma|kiyma', 'tavuk,hindi,kuzu', False),
            ('Kuru soğan', '1 adet', 150, 'g', 'kuru sogan', 'toz,granul', False),
            ('Sivri biber', '3 adet', 100, 'g', 'sivri biber', 'tursu,toz', False),
            ('Domates', '2 adet', 300, 'g', 'domates', 'salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl', False),
            ('Sarımsak', '2 diş', 10, 'g', 'sarimsak', 'toz,granul', False),
            ('Domates salçası', '1 yemek kaşığı', 20, 'g', 'domates salcasi', None, False),
            ('Ayçiçek yağı', '1 su bardağı (kızartma)', 200, 'ml', 'aycicek yagi', None, False),
            ('Tuz', '1 tatlı kaşığı', 5, 'g', 'tuz', 'tuzsuz,tuzlu', True),
            ('Karabiber', '1 çay kaşığı', 2, 'g', 'karabiber', None, True),
        ],
    },
    {
        'slug': 'menemen',
        'name': 'Menemen',
        'course': 'Kahvaltılık',
        'meal_slots': 'kahvalti',
        'servings': 2,
        'prep_minutes': 5,
        'cook_minutes': 15,
        'icon': '🍳',
        'description': 'Biber ve domatesin üzerine yumurta kırılarak sahanda pişen kahvaltı klasiği.',
        'steps': [
            'Biberleri ince doğrayın, domatesleri rendeleyin ya da küçük küp doğrayın.',
            'Tavada zeytinyağını ısıtın, biberleri yumuşayana kadar soteleyin.',
            'Domatesi ekleyip suyunu biraz çekene kadar pişirin; tuz ve pul biberi ekleyin.',
            'Yumurtaları kırın; dilerseniz karıştırın, dilerseniz bütün bırakın.',
            'Yumurtalar istediğiniz kıvama gelince ocaktan alıp sıcak servis edin.',
        ],
        'ingredients': [
            ('Yumurta', '4 adet', 4, 'adet', 'yumurta', 'cikolata,makarna,eriste', False),
            ('Domates', '3 adet', 450, 'g', 'domates', 'salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl', False),
            ('Sivri biber', '3 adet', 100, 'g', 'sivri biber', 'tursu,toz', False),
            ('Zeytinyağı', '2 yemek kaşığı', 30, 'ml', 'zeytinyagi', None, False),
            ('Tuz', '1 çay kaşığı', 3, 'g', 'tuz', 'tuzsuz,tuzlu', True),
            ('Pul biber', '1 çay kaşığı', 2, 'g', 'pul biber', None, True),
        ],
    },
    {
        'slug': 'tavuk-sote',
        'name': 'Tavuk Sote',
        'course': 'Ana yemek',
        'meal_slots': 'ogle,aksam',
        'servings': 4,
        'prep_minutes': 15,
        'cook_minutes': 25,
        'icon': '🍗',
        'description': 'Kuşbaşı tavuk göğsünün biber, domates ve salçayla tavada pişirildiği pratik yemek.',
        'steps': [
            'Tavuk göğsünü kuşbaşı doğrayın.',
            'Geniş tavada yağı kızdırın, tavukları suyunu salıp çekene kadar yüksek ateşte soteleyin.',
            'Doğranmış soğanı ekleyip pembeleşene kadar kavurun.',
            'Biberleri ekleyip 3-4 dakika pişirin.',
            'Salçayı ve küp doğranmış domatesleri ekleyin; tuz, karabiber ve kekiği serpin.',
            'Kapağı kapalı, kısık ateşte 10 dakika pişirip pilav ya da bulgurla servis edin.',
        ],
        'ingredients': [
            ('Tavuk göğsü', '500 g', 500, 'g', 'tavuk gogus|pilic gogus', 'fume,jambon,salam,doner,pane,haslanmis', False),
            ('Kuru soğan', '1 adet', 150, 'g', 'kuru sogan', 'toz,granul', False),
            ('Sivri biber', '2 adet', 70, 'g', 'sivri biber', 'tursu,toz', False),
            ('Domates', '2 adet', 300, 'g', 'domates', 'salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl', False),
            ('Domates salçası', '1 yemek kaşığı', 20, 'g', 'domates salcasi', None, False),
            ('Ayçiçek yağı', '3 yemek kaşığı', 45, 'ml', 'aycicek yagi', None, False),
            ('Tuz', '1 tatlı kaşığı', 5, 'g', 'tuz', 'tuzsuz,tuzlu', True),
            ('Karabiber', '1 çay kaşığı', 2, 'g', 'karabiber', None, True),
            ('Kekik', '1 çay kaşığı', 1, 'g', 'kekik', 'yagi,sabun,cay', True),
        ],
    },
]


def upgrade() -> None:
    cuisines = op.create_table(
        'cuisines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('icon', sa.String(length=16), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_cuisines')),
        sa.UniqueConstraint('slug', name=op.f('uq_cuisines_slug')),
    )
    recipes = op.create_table(
        'recipes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cuisine_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('course', sa.String(length=32), nullable=False),
        sa.Column('meal_slots', sa.String(length=64), nullable=False),
        sa.Column('servings', sa.Integer(), nullable=False),
        sa.Column('prep_minutes', sa.Integer(), nullable=False),
        sa.Column('cook_minutes', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('steps', sa.Text(), nullable=False),
        sa.Column('icon', sa.String(length=16), nullable=True),
        sa.Column('image_url', sa.String(length=1024), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['cuisine_id'], ['cuisines.id'], name=op.f('fk_recipes_cuisine_id_cuisines'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recipes')),
        sa.UniqueConstraint('slug', name=op.f('uq_recipes_slug')),
    )
    op.create_index(op.f('ix_recipes_cuisine_id'), 'recipes', ['cuisine_id'])
    ingredients = op.create_table(
        'recipe_ingredients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('amount_text', sa.String(length=64), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.Enum('ml', 'g', 'adet', name='unit', native_enum=False, length=8), nullable=False),
        sa.Column('search_term', sa.String(length=120), nullable=False),
        sa.Column('exclude_terms', sa.String(length=255), nullable=True),
        sa.Column('is_pantry', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], name=op.f('fk_recipe_ingredients_recipe_id_recipes'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recipe_ingredients')),
    )
    op.create_index(op.f('ix_recipe_ingredients_recipe_id'), 'recipe_ingredients', ['recipe_id'])
    op.create_table(
        'meal_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('period', sa.Enum('daily', 'weekly', name='planperiod', native_enum=False, length=16), nullable=False),
        sa.Column('cuisine_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('servings', sa.Integer(), nullable=False),
        sa.Column('meal_slots', sa.String(length=64), nullable=False),
        sa.Column('exported_list_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_meal_plans_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cuisine_id'], ['cuisines.id'], name=op.f('fk_meal_plans_cuisine_id_cuisines'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['exported_list_id'], ['shopping_lists.id'], name=op.f('fk_meal_plans_exported_list_id_shopping_lists'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_meal_plans')),
    )
    op.create_index(op.f('ix_meal_plans_user_id'), 'meal_plans', ['user_id'])
    op.create_table(
        'meal_plan_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('day_index', sa.Integer(), nullable=False),
        sa.Column('slot', sa.Enum('kahvalti', 'ogle', 'aksam', name='mealslot', native_enum=False, length=16), nullable=False),
        sa.Column('slot_order', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['meal_plans.id'], name=op.f('fk_meal_plan_entries_plan_id_meal_plans'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], name=op.f('fk_meal_plan_entries_recipe_id_recipes'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_meal_plan_entries')),
    )
    op.create_index(op.f('ix_meal_plan_entries_plan_id'), 'meal_plan_entries', ['plan_id'])

    # --- Başlangıç verisi ---
    conn = op.get_bind()
    op.bulk_insert(cuisines, [
        {'slug': slug, 'name': name, 'icon': icon, 'is_default': default, 'is_active': True, 'position': pos}
        for slug, name, icon, default, pos in CUISINES
    ])
    anadolu_id = conn.execute(sa.text("SELECT id FROM cuisines WHERE slug = 'anadolu'")).scalar_one()
    for recipe in RECIPES:
        recipe_id = conn.execute(
            recipes.insert().returning(recipes.c.id),
            {
                'cuisine_id': anadolu_id,
                **{k: recipe[k] for k in (
                    'slug', 'name', 'course', 'meal_slots', 'servings', 'prep_minutes', 'cook_minutes', 'description', 'icon',
                )},
                'steps': '\n'.join(recipe['steps']),
                'is_active': True,
            },
        ).scalar_one()
        op.bulk_insert(ingredients, [
            {
                'recipe_id': recipe_id, 'position': i, 'name': name, 'amount_text': amount, 'quantity': qty,
                'unit': unit, 'search_term': term, 'exclude_terms': exclude, 'is_pantry': pantry,
            }
            for i, (name, amount, qty, unit, term, exclude, pantry) in enumerate(recipe['ingredients'])
        ])


def downgrade() -> None:
    op.drop_index(op.f('ix_meal_plan_entries_plan_id'), table_name='meal_plan_entries')
    op.drop_table('meal_plan_entries')
    op.drop_index(op.f('ix_meal_plans_user_id'), table_name='meal_plans')
    op.drop_table('meal_plans')
    op.drop_index(op.f('ix_recipe_ingredients_recipe_id'), table_name='recipe_ingredients')
    op.drop_table('recipe_ingredients')
    op.drop_index(op.f('ix_recipes_cuisine_id'), table_name='recipes')
    op.drop_table('recipes')
    op.drop_table('cuisines')
