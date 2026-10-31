"""meal courses: soup/main/salad/dessert/drink/snack per meal, drink pairing (+ new recipes)

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-31 10:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0012'
down_revision: str | None = '0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOMATES_EXCLUDE = 'salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl'
ALL_MAINS = 'kuru-fasulye,karniyarik,tavuk-sote'

# 0011'deki tariflerin yemek türü
EXISTING_COURSES = {
    'mercimek-corbasi': 'corba',
    'kuru-fasulye': 'ana',
    'karniyarik': 'ana',
    'menemen': 'ana',
    'tavuk-sote': 'ana',
}

# Malzeme: (ad, tarifteki ölçü, temel birimde miktar, birim, arama ifadesi, elenecek kelimeler, evde var mı)
RECIPES = [
    # --- Çorbalar ---
    {
        'slug': 'ezogelin-corbasi', 'name': 'Ezogelin Çorbası', 'course': 'Çorba', 'course_type': 'corba',
        'meal_slots': 'ogle,aksam', 'servings': 4, 'prep_minutes': 10, 'cook_minutes': 35, 'icon': '🍲',
        'description': 'Mercimek, bulgur ve pirinçle, salçalı ve naneli Gaziantep usulü çorba.',
        'steps': [
            'Mercimek, bulgur ve pirinci yıkayıp süzün.',
            'Tereyağında doğranmış soğanı kavurun, salçayı ekleyip 1 dakika daha kavurun.',
            'Mercimek, bulgur ve pirinci ekleyip 7 su bardağı sıcak su ilave edin.',
            'Kısık ateşte bakliyatlar dağılana kadar 30 dakika pişirin; tuzu ekleyin.',
            'Kızdırılmış tereyağına nane ve pul biber ekleyip çorbanın üzerine gezdirin.',
        ],
        'ingredients': [
            ('Kırmızı mercimek', '1 çay bardağı', 150, 'g', 'kirmizi mercimek', None, False),
            ('Pilavlık bulgur', '2 yemek kaşığı', 50, 'g', 'bulgur', 'koftelik,kofte', False),
            ('Pirinç', '1 yemek kaşığı', 30, 'g', 'pirinc', 'unu,patlagi,sirkesi', False),
            ('Kuru soğan', '1 adet', 100, 'g', 'kuru sogan', 'toz,granul', False),
            ('Domates salçası', '1 yemek kaşığı', 20, 'g', 'domates salcasi', None, False),
            ('Tereyağı', '2 yemek kaşığı', 30, 'g', 'tereyagi', None, False),
            ('Tuz', '1 tatlı kaşığı', 5, 'g', 'tuz', 'tuzsuz,tuzlu', True),
            ('Kuru nane', '1 tatlı kaşığı', 2, 'g', 'nane', None, True),
            ('Pul biber', '1 çay kaşığı', 2, 'g', 'pul biber', None, True),
        ],
    },
    {
        'slug': 'yayla-corbasi', 'name': 'Yayla Çorbası', 'course': 'Çorba', 'course_type': 'corba',
        'meal_slots': 'ogle,aksam', 'servings': 4, 'prep_minutes': 10, 'cook_minutes': 25, 'icon': '🥛',
        'description': 'Yoğurt ve pirinçle yapılan, naneli tereyağıyla servis edilen hafif çorba.',
        'steps': [
            'Pirinci 5 su bardağı suda yumuşayana kadar haşlayın.',
            'Ayrı bir kapta yoğurt, yumurta sarısı ve unu çırpın.',
            'Pirinç suyundan birkaç kepçe alıp yoğurtlu karışıma azar azar ekleyerek ılıştırın.',
            'Karışımı sürekli karıştırarak tencereye dökün, kaynayınca 5 dakika pişirip tuzlayın.',
            'Tereyağında naneyi kızdırıp çorbanın üzerine gezdirin.',
        ],
        'ingredients': [
            ('Yoğurt', '2 su bardağı', 500, 'g', 'yogurt', 'icecek,meyveli,suzme,cilekli,kakaolu', False),
            ('Pirinç', '1 çay bardağı', 80, 'g', 'pirinc', 'unu,patlagi,sirkesi', False),
            ('Yumurta', '1 adet', 1, 'adet', 'yumurta', 'cikolata,makarna,eriste', False),
            ('Buğday unu', '1 yemek kaşığı', 15, 'g', 'bugday unu', None, False),
            ('Tereyağı', '1 yemek kaşığı', 20, 'g', 'tereyagi', None, False),
            ('Tuz', '1 tatlı kaşığı', 5, 'g', 'tuz', 'tuzsuz,tuzlu', True),
            ('Kuru nane', '1 tatlı kaşığı', 2, 'g', 'nane', None, True),
        ],
    },
    # --- Salatalar ---
    {
        'slug': 'coban-salatasi', 'name': 'Çoban Salatası', 'course': 'Salata', 'course_type': 'salata',
        'meal_slots': 'ogle,aksam', 'servings': 4, 'prep_minutes': 15, 'cook_minutes': 0, 'icon': '🥗',
        'description': 'Domates, salatalık, biber ve soğanın limon ve zeytinyağıyla buluştuğu klasik salata.',
        'steps': [
            'Domates, salatalık ve biberi küçük küp doğrayın.',
            'Soğanı ince doğrayıp tuzla ovun, suyunu sıkıp ekleyin.',
            'Kıyılmış maydanozu ekleyin.',
            'Zeytinyağı, limon suyu ve tuzla harmanlayıp hemen servis edin.',
        ],
        'ingredients': [
            ('Domates', '2 adet', 300, 'g', 'domates', DOMATES_EXCLUDE, False),
            ('Salatalık', '2 adet', 300, 'g', 'salatalik', 'tursu,kornison', False),
            ('Sivri biber', '2 adet', 70, 'g', 'sivri biber', 'tursu,toz', False),
            ('Kuru soğan', '1 küçük', 80, 'g', 'kuru sogan', 'toz,granul', False),
            ('Maydanoz', '1 demet', 1, 'adet', 'maydanoz', 'kurusu,kuru', False),
            ('Limon', '1/2 adet', 50, 'g', 'limon', 'sosu,kolonya,tuzu,suyu,aromali', False),
            ('Zeytinyağı', '2 yemek kaşığı', 30, 'ml', 'zeytinyagi', None, False),
            ('Tuz', '1 çay kaşığı', 3, 'g', 'tuz', 'tuzsuz,tuzlu', True),
        ],
    },
    {
        'slug': 'mevsim-salatasi', 'name': 'Mevsim Salatası', 'course': 'Salata', 'course_type': 'salata',
        'meal_slots': 'ogle,aksam', 'servings': 4, 'prep_minutes': 15, 'cook_minutes': 0, 'icon': '🥬',
        'description': 'Marul, havuç ve roka ile nar ekşili, zeytinyağlı yeşil salata.',
        'steps': [
            'Marulu ve rokayı yıkayıp ince doğrayın.',
            'Havucu rendeleyin, salatalığı yarım ay doğrayın.',
            'Hepsini geniş bir kapta karıştırın.',
            'Zeytinyağı, nar ekşisi, limon ve tuzla soslayıp servis edin.',
        ],
        'ingredients': [
            ('Marul', '1 adet', 1, 'adet', 'marul|kivircik', 'tohum', False),
            ('Havuç', '1 adet', 100, 'g', 'havuc', 'suyu,bebek', False),
            ('Salatalık', '1 adet', 150, 'g', 'salatalik', 'tursu,kornison', False),
            ('Roka', '1 demet', 1, 'adet', 'roka', 'tohum', False),
            ('Nar ekşisi', '1 yemek kaşığı', 20, 'ml', 'nar eksisi', None, False),
            ('Zeytinyağı', '2 yemek kaşığı', 30, 'ml', 'zeytinyagi', None, False),
            ('Tuz', '1 çay kaşığı', 3, 'g', 'tuz', 'tuzsuz,tuzlu', True),
        ],
    },
    # --- Tatlılar ---
    {
        'slug': 'sutlac', 'name': 'Sütlaç', 'course': 'Tatlı', 'course_type': 'tatli',
        'meal_slots': 'ogle,aksam', 'servings': 4, 'prep_minutes': 10, 'cook_minutes': 40, 'icon': '🍮',
        'description': 'Pirinç ve sütle ağır ateşte pişen, tarçınla servis edilen sütlü tatlı.',
        'steps': [
            'Pirinci 1 su bardağı suyla, suyunu çekene kadar haşlayın.',
            'Sütü ekleyip kaynayınca kısık ateşte 15 dakika pişirin.',
            'Nişastayı az soğuk sütte açıp ekleyin; şekeri ilave edip 10 dakika daha karıştırarak pişirin.',
            'Kaselere paylaştırıp soğutun, tarçınla servis edin.',
        ],
        'ingredients': [
            ('Süt', '1 litre', 1000, 'ml', 'sut', 'tozu,cikolatali,kakaolu,cilekli,muzlu,laktozsuz,keci,badem,soya', False),
            ('Pirinç', '1/2 su bardağı', 100, 'g', 'pirinc', 'unu,patlagi,sirkesi', False),
            ('Toz şeker', '1 su bardağı', 150, 'g', 'toz seker', 'pudra,esmer,kup', False),
            ('Buğday nişastası', '2 yemek kaşığı', 20, 'g', 'nisasta', None, False),
            ('Tarçın', 'servis için', 2, 'g', 'tarcin', None, True),
        ],
    },
    {
        'slug': 'irmik-helvasi', 'name': 'İrmik Helvası', 'course': 'Tatlı', 'course_type': 'tatli',
        'meal_slots': 'ogle,aksam', 'servings': 4, 'prep_minutes': 5, 'cook_minutes': 25, 'icon': '🍯',
        'description': 'Tereyağında kavrulan irmiğin sütlü şerbetle demlendiği geleneksel helva.',
        'steps': [
            'Süt, su ve şekeri bir tencerede kaynatıp şerbeti hazırlayın.',
            'Tereyağını eritip irmiği ekleyin; kısık ateşte rengi dönene kadar 15 dakika kavurun.',
            'Sıcak şerbeti dikkatlice irmiğe ekleyip karıştırın.',
            'Kapağını kapatıp kısık ateşte suyunu çektirin, 10 dakika demlendirip servis edin.',
        ],
        'ingredients': [
            ('İrmik', '1 su bardağı', 170, 'g', 'irmik', 'tatlisi,helva', False),
            ('Tereyağı', '2 yemek kaşığı', 40, 'g', 'tereyagi', None, False),
            ('Süt', '1 su bardağı', 200, 'ml', 'sut', 'tozu,cikolatali,kakaolu,cilekli,muzlu,laktozsuz,keci,badem,soya', False),
            ('Toz şeker', '1 su bardağı', 150, 'g', 'toz seker', 'pudra,esmer,kup', False),
        ],
    },
    # --- Hazır içecekler (porsiyon = 1 kişi) ---
    {
        'slug': 'ayran', 'name': 'Ayran', 'course': 'İçecek', 'course_type': 'icecek',
        'meal_slots': 'ogle,aksam', 'servings': 1, 'prep_minutes': 0, 'cook_minutes': 0, 'icon': '🥛',
        'pairs_with': ALL_MAINS,
        'description': 'Kuru fasulye, karnıyarık ve tavuk soteyle en çok yakışan hazır içecek.',
        'steps': ['Soğuk servis edin.'],
        'ingredients': [('Ayran', '1 bardak', 250, 'ml', 'ayran', None, False)],
    },
    {
        'slug': 'salgam', 'name': 'Şalgam Suyu', 'course': 'İçecek', 'course_type': 'icecek',
        'meal_slots': 'ogle,aksam', 'servings': 1, 'prep_minutes': 0, 'cook_minutes': 0, 'icon': '🍷',
        'pairs_with': 'kuru-fasulye,karniyarik',
        'description': 'Acılı ya da acısız; bakliyat ve kıymalı yemeklerin yanında ferahlatır.',
        'steps': ['Soğuk servis edin; isteğe göre yanında turşuyla.'],
        'ingredients': [('Şalgam suyu', '1 bardak', 250, 'ml', 'salgam', None, False)],
    },
    {
        'slug': 'maden-suyu', 'name': 'Maden Suyu', 'course': 'İçecek', 'course_type': 'icecek',
        'meal_slots': 'ogle,aksam', 'servings': 1, 'prep_minutes': 0, 'cook_minutes': 0, 'icon': '🫧',
        'pairs_with': 'tavuk-sote,karniyarik',
        'description': 'Sade ya da limonlu; yağlı yemeklerin ardından hazmı kolaylaştırır.',
        'steps': ['Soğuk, isteğe göre bir dilim limonla servis edin.'],
        'ingredients': [('Maden suyu', '1 şişe', 200, 'ml', 'maden suyu|soda', 'aromali,meyveli', False)],
    },
    {
        'slug': 'portakal-suyu', 'name': 'Portakal Suyu', 'course': 'İçecek', 'course_type': 'icecek',
        'meal_slots': 'kahvalti', 'servings': 1, 'prep_minutes': 0, 'cook_minutes': 0, 'icon': '🍊',
        'pairs_with': 'menemen',
        'description': 'Kahvaltıda menemenin yanına hazır portakal suyu.',
        'steps': ['Soğuk servis edin.'],
        'ingredients': [('Portakal suyu', '1 bardak', 200, 'ml', 'portakal suyu', 'toz,aromali', False)],
    },
    # --- Ara öğünler (ikindi) ---
    {
        'slug': 'meyve-tabagi', 'name': 'Meyve Tabağı', 'course': 'Ara öğün', 'course_type': 'ara',
        'meal_slots': 'ara', 'servings': 2, 'prep_minutes': 5, 'cook_minutes': 0, 'icon': '🍎',
        'description': 'Elma, mandalina ve muzdan hafif bir ara öğün.',
        'steps': ['Meyveleri yıkayıp dilimleyin, tabağa dizip servis edin.'],
        'ingredients': [
            ('Elma', '1 adet', 200, 'g', 'elma', 'suyu,sirkesi,kurusu,cips,kek,turta,aromali', False),
            ('Mandalina', '2 adet', 250, 'g', 'mandalina', 'suyu', False),
            ('Muz', '1 adet', 150, 'g', 'muz', 'cips,kurusu,aromali,sut', False),
        ],
    },
    {
        'slug': 'cevizli-yogurt', 'name': 'Ballı Cevizli Yoğurt', 'course': 'Ara öğün', 'course_type': 'ara',
        'meal_slots': 'ara', 'servings': 2, 'prep_minutes': 5, 'cook_minutes': 0, 'icon': '🥣',
        'description': 'Yoğurt, ceviz ve balla tok tutan pratik ara öğün.',
        'steps': ['Yoğurdu kaselere paylaştırın.', 'Üzerine kırılmış ceviz ve bal gezdirip servis edin.'],
        'ingredients': [
            ('Yoğurt', '1,5 su bardağı', 300, 'g', 'yogurt', 'icecek,meyveli,cilekli,kakaolu', False),
            ('Ceviz içi', '1 avuç', 40, 'g', 'ceviz ici|ceviz', 'yagi,kabuklu', False),
            ('Bal', '2 yemek kaşığı', 30, 'g', 'bal', 'balik,kabak', False),
        ],
    },
]


def upgrade() -> None:
    op.add_column('recipes', sa.Column('course_type', sa.String(length=16), server_default='ana', nullable=False))
    op.add_column('recipes', sa.Column('pairs_with', sa.String(length=255), nullable=True))
    op.add_column('meal_plans', sa.Column('courses', sa.String(length=64), server_default='corba,ana,salata,tatli,icecek', nullable=False))
    op.add_column('meal_plan_entries', sa.Column('course', sa.String(length=16), server_default='ana', nullable=False))

    conn = op.get_bind()
    for slug, course in EXISTING_COURSES.items():
        conn.execute(sa.text('UPDATE recipes SET course_type = :c WHERE slug = :s'), {'c': course, 's': slug})
    # Eski planlardaki öğünler tarifin türünü alır; sıralama öğün x 10 + tür
    conn.execute(sa.text(
        "UPDATE meal_plan_entries e SET course = r.course_type FROM recipes r WHERE r.id = e.recipe_id"
    ))
    conn.execute(sa.text(
        "UPDATE meal_plan_entries SET slot_order = (CASE slot WHEN 'kahvalti' THEN 0 WHEN 'ogle' THEN 1 "
        "WHEN 'ara' THEN 2 ELSE 3 END) * 10 + (CASE course WHEN 'corba' THEN 0 WHEN 'ana' THEN 1 "
        "WHEN 'salata' THEN 2 WHEN 'tatli' THEN 3 WHEN 'icecek' THEN 4 ELSE 5 END)"
    ))

    recipes = sa.table(
        'recipes', *(sa.column(c) for c in (
            'id', 'cuisine_id', 'slug', 'name', 'course', 'course_type', 'pairs_with', 'meal_slots', 'servings',
            'prep_minutes', 'cook_minutes', 'description', 'steps', 'icon', 'is_active',
        ))
    )
    ingredients = sa.table(
        'recipe_ingredients', *(sa.column(c) for c in (
            'recipe_id', 'position', 'name', 'amount_text', 'quantity', 'unit', 'search_term', 'exclude_terms', 'is_pantry',
        ))
    )
    anadolu_id = conn.execute(sa.text("SELECT id FROM cuisines WHERE slug = 'anadolu'")).scalar_one()
    for recipe in RECIPES:
        recipe_id = conn.execute(
            recipes.insert().returning(recipes.c.id),
            {
                'cuisine_id': anadolu_id,
                **{k: recipe[k] for k in (
                    'slug', 'name', 'course', 'course_type', 'meal_slots', 'servings', 'prep_minutes', 'cook_minutes',
                    'description', 'icon',
                )},
                'pairs_with': recipe.get('pairs_with'),
                'steps': '\n'.join(recipe['steps']),
                'is_active': True,
            },
        ).scalar_one()
        conn.execute(ingredients.insert(), [
            {
                'recipe_id': recipe_id, 'position': i, 'name': name, 'amount_text': amount, 'quantity': qty,
                'unit': unit, 'search_term': term, 'exclude_terms': exclude, 'is_pantry': pantry,
            }
            for i, (name, amount, qty, unit, term, exclude, pantry) in enumerate(recipe['ingredients'])
        ])


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [r['slug'] for r in RECIPES]
    conn.execute(sa.text(
        'DELETE FROM meal_plan_entries WHERE recipe_id IN (SELECT id FROM recipes WHERE slug = ANY(:s))'
    ), {'s': slugs})
    conn.execute(sa.text('DELETE FROM recipes WHERE slug = ANY(:s)'), {'s': slugs})
    conn.execute(sa.text("DELETE FROM meal_plan_entries WHERE slot = 'ara'"))
    op.drop_column('meal_plan_entries', 'course')
    op.drop_column('meal_plans', 'courses')
    op.drop_column('recipes', 'pairs_with')
    op.drop_column('recipes', 'course_type')
