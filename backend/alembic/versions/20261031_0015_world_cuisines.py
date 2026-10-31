"""world cuisines (İtalyan, Uzak Doğu, Meksika) + multi-cuisine weekly plans + recipe availability

- meal_plans.cuisines: planda seçilen mutfaklar (slug, virgülle); cuisine_id ilk mutfak olarak kalır.
- recipes.missing_ingredients: uygulamadaki marketlerde bulunamayan malzemeler (virgülle). Boş = hepsi
  bulundu, NULL = henüz kontrol edilmedi. Malzemesi eksik tarif planlarda ve listelerde gösterilmez
  (bkz. services/meals.refresh_availability; senkronizasyondan sonra ve API açılışında çalışır).

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-31 20:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0015'
down_revision: str | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEBZE = 'meyve-sebze'
TEMEL = 'temel-gida'
SUT_K = 'sut-kahvaltilik'
ET = 'et-tavuk-balik'
ICECEK = 'icecek'
ATISTIRMALIK = 'atistirmalik'
FIRIN = 'firin'
DONDURULMUS = 'dondurulmus'

# (arama ifadesi, elenecek kelimeler, izin verilen kategoriler)
DOMATES = ('domates', 'salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl', SEBZE)
SOGAN = ('kuru sogan', 'toz,granul', SEBZE)
YESIL_SOGAN = ('yesil sogan|taze sogan', None, SEBZE)
SARIMSAK = ('sarimsak', 'toz,granul', SEBZE)
BIBER = ('sivri biber', 'tursu,toz', SEBZE)
KAPYA = ('kapya biber|kirmizi biber|renkli biber', 'pul,toz,salca,tursu,kozlenmis,konserve,sos', SEBZE)
HAVUC = ('havuc', 'suyu,rendesi,tursu', SEBZE)
KABAK = ('kabak', 'bal,cekirdek,tatlisi', SEBZE)
PATATES = ('patates', 'cips,kizartma,dondurulmus,pure', SEBZE)
MANTAR = ('mantar', 'konserve,tursu,sos,corba', SEBZE)
ROKA = ('roka', None, SEBZE)
MARUL = ('marul|kivircik|aysberg', None, SEBZE)
SALATALIK = ('salatalik', 'tursu', SEBZE)
LAHANA = ('beyaz lahana|lahana', 'tursu,kirmizi,bruksel', SEBZE)
BROKOLI = ('brokoli', None, f'{SEBZE},{DONDURULMUS}')
BEZELYE = ('bezelye', 'konserve', f'{SEBZE},{DONDURULMUS},{TEMEL}')
AVOKADO = ('avokado', None, SEBZE)
LIMON = ('limon', 'sosu,kolonya,tuzu,suyu,aromali', SEBZE)
MAYDANOZ = ('maydanoz', 'kurusu,kuru', SEBZE)
NANE = ('nane', 'sekeri,sakiz,cay', f'{SEBZE},{TEMEL}')
MUZ = ('muz', 'cips,kurusu,aromali,sut', SEBZE)
CILEK = ('cilek', 'recel,aromali,sut,kurusu', f'{SEBZE},{DONDURULMUS}')
ZENCEFIL = ('zencefil', 'cay,sakiz,gazoz,sekerleme', f'{SEBZE},{TEMEL}')
FESLEGEN = ('feslegen', 'sos,pesto', f'{SEBZE},{TEMEL}')

KIYMA = ('dana kiyma|kiyma', 'tavuk,hindi,kuzu', ET)
KUSBASI = ('dana bonfile|dana kusbasi|kusbasi', 'tavuk,hindi,kuzu', ET)
TAVUK = ('tavuk gogus|pilic gogus', None, ET)
YUMURTA = ('yumurta', 'cikolata,makarna,eriste', SUT_K)
SUT = ('sut', 'tozu,cikolatali,kakaolu,cilekli,muzlu,laktozsuz,keci,badem,soya,hindistan', SUT_K)
TEREYAGI = ('tereyagi', None, SUT_K)
KREMA = ('sivi krema|krema', 'sanitize,sekerli,kakaolu,kremasi,cikolata,kahve,sac,yuz,el', SUT_K)
KASAR = ('rende kasar|kasar peyniri|kasar', 'cubuk', SUT_K)
PARMESAN = ('parmesan|rende kasar', None, SUT_K)
MOZZARELLA = ('mozzarella|mozarella', None, SUT_K)
LABNE = ('labne', None, SUT_K)

SPAGETTI = ('spagetti', None, TEMEL)
PENNE = ('penne|kalem makarna', None, TEMEL)
LAZANYA = ('lazanya', None, f'{TEMEL},{DONDURULMUS}')
NOODLE = ('noodle', 'cup,bardak', TEMEL)
PIRINC = ('pirinc', 'unu,patlagi,sirkesi', TEMEL)
UN = ('bugday unu', None, TEMEL)
MAYA = ('instant maya|kuru maya|maya', 'kabartma', TEMEL)
NISASTA = ('misir nisastasi|nisasta', None, TEMEL)
SALCA = ('domates salcasi', None, TEMEL)
ZEYTINYAGI = ('zeytinyagi', None, TEMEL)
AYCICEK = ('aycicek yagi', None, TEMEL)
SEKER = ('toz seker', 'pudra,esmer,kup', TEMEL)
BAL = ('bal', 'balik,kabak,kabag,cekirdek', f'{SUT_K},{TEMEL}')
SOYA = ('soya sosu', None, TEMEL)
SIRKE = ('elma sirkesi|uzum sirkesi|sirke', None, TEMEL)
KETCAP = ('ketcap', None, TEMEL)
SUSAM = ('susam', 'yagi,tahin,simit,kraker,bar,helva', f'{TEMEL},{ATISTIRMALIK}')
YER_FISTIGI = ('yer fistigi|fistik', 'ezmesi,antep,cikolata,bar,sos', f'{ATISTIRMALIK},{TEMEL}')
KORI = ('kori|curry', 'sos', TEMEL)
HINDISTAN_SUTU = ('hindistan cevizi sutu', None, f'{TEMEL},{SUT_K},{ICECEK}')
MISIR = ('misir konservesi|konserve misir|tatli misir|misir', 'cips,patlak,patlamis,unu,nisasta,gevrek,yag,irmik', f'{TEMEL},{SEBZE}')
FASULYE = ('kirmizi fasulye|barbunya', 'tursu,pilaki', f'{TEMEL},{SEBZE}')
TORTILLA = ('tortilla|lavas', 'cips', f'{FIRIN},{TEMEL}')
EKMEK = ('baget ekmek|baget|ekmek', 'galeta,kirintisi,unu,kizarmis', FIRIN)
YUFKA = ('yufka', 'kadayif', f'{FIRIN},{TEMEL},{SUT_K}')
SEHRIYE = ('arpa sehriye|sehriye', 'tel', TEMEL)
KEDI_DILI = ('kedi dili biskuvi|kedi dili|kedidili', None, f'{ATISTIRMALIK},{TEMEL}')
KAHVE = ('granul kahve|hazir kahve|nescafe', 'kremasi,beyazlatici,kapsul,3u1,2si1,sutlu', f'{ICECEK},{TEMEL}')
KAKAO = ('kakao', 'kremasi,sutlu,icecek,gofret,findik', TEMEL)
JELATIN = ('jelatin', 'sekerleme,jole', TEMEL)
YESIL_CAY = ('yesil cay', 'aromali,soguk,icecek', f'{ICECEK},{TEMEL}')

TUZ = ('tuz', 'tuzsuz,tuzlu', TEMEL)
KARABIBER = ('karabiber', None, TEMEL)
PUL_BIBER = ('pul biber', None, TEMEL)
KIMYON = ('kimyon', None, TEMEL)
TARCIN = ('tarcin', 'sakiz,cay,kek', TEMEL)
KEKIK = ('kekik', 'yagi,sabun,cay', TEMEL)


def ing(name, amount, qty, unit, term, pantry=False):
    """term: (arama ifadesi, elenecek kelimeler, kategoriler)"""
    return (name, amount, qty, unit, term[0], term[1], term[2], pantry)


R = 'ogle,aksam'

CUISINES = [
    # slug, ad, simge, sıra
    ('italyan', 'İtalyan Mutfağı', '🍝', 1),
    ('uzakdogu', 'Uzak Doğu Mutfağı', '🥢', 2),
    ('meksika', 'Meksika Mutfağı', '🌮', 3),
]

ITALYAN_PASTA = 'spagetti-pomodoro,spagetti-bolonez,penne-arrabbiata,kremali-tavuklu-penne,firinda-lazanya,mantarli-risotto'


def recipe(slug, name, course, course_type, icon, servings, prep, cook, description, allergens, diets, nutrition,
           popularity, steps, ingredients, slots=R, pairs_with=None):
    return {
        'slug': slug, 'name': name, 'course': course, 'course_type': course_type, 'icon': icon,
        'servings': servings, 'prep_minutes': prep, 'cook_minutes': cook, 'description': description,
        'allergens': allergens, 'diets': diets, 'nutrition': nutrition, 'popularity': popularity,
        'steps': steps, 'ingredients': ingredients, 'meal_slots': slots, 'pairs_with': pairs_with,
    }


ITALYAN = [
    recipe(
        'spagetti-pomodoro', 'Domatesli Fesleğenli Spagetti', 'Ana yemek', 'ana', '🍝', 4, 10, 20,
        'Sarımsaklı, zeytinyağlı taze domates sosuyla İtalyanların en sade makarnası.',
        'gluten', 'vejetaryen,vegan', (480, 15, 82, 11), 88,
        [
            'Domateslerin kabuğunu soyup küp küp doğrayın.',
            'Zeytinyağında ezilmiş sarımsağı 1 dakika çevirin, domatesleri ekleyip 15 dakika koyulaşana kadar pişirin.',
            'Spagettiyi bol tuzlu suda paketteki süre kadar haşlayın, bir kepçe suyunu ayırıp süzün.',
            'Makarnayı sosa alın, ayırdığınız suyla karıştırın; fesleğen, tuz ve karabiberle servis edin.',
        ],
        [
            ing('Spagetti', '1 paket', 500, 'g', SPAGETTI),
            ing('Domates', '5 adet', 750, 'g', DOMATES),
            ing('Sarımsak', '3 diş', 12, 'g', SARIMSAK),
            ing('Zeytinyağı', '4 yemek kaşığı', 50, 'ml', ZEYTINYAGI),
            ing('Fesleğen', '1 avuç', 10, 'g', FESLEGEN),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', KARABIBER, True),
        ],
    ),
    recipe(
        'spagetti-bolonez', 'Spagetti Bolonez', 'Ana yemek', 'ana', '🍝', 4, 15, 45,
        'Kıymanın soğan, havuç ve domatesle uzun uzun piştiği klasik Bolonez soslu spagetti.',
        'gluten,sut', '', (640, 32, 78, 22), 94,
        [
            'Zeytinyağında ince doğranmış soğan ve rendelenmiş havucu 5 dakika soteleyin.',
            'Kıymayı ekleyip suyunu çekene kadar kavurun; salçayı ekleyip 1 dakika çevirin.',
            'Rendelenmiş domatesi ve 1 su bardağı sıcak suyu ekleyin, kısık ateşte 30 dakika pişirin.',
            'Spagettiyi haşlayıp süzün, sosla karıştırın; üzerine rende peynir serpip servis edin.',
        ],
        [
            ing('Spagetti', '1 paket', 500, 'g', SPAGETTI),
            ing('Dana kıyma', '400 g', 400, 'g', KIYMA),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Havuç', '1 adet', 100, 'g', HAVUC),
            ing('Domates', '3 adet', 450, 'g', DOMATES),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Zeytinyağı', '2 yemek kaşığı', 25, 'ml', ZEYTINYAGI),
            ing('Rende peynir (parmesan ya da kaşar)', '1/2 su bardağı', 50, 'g', PARMESAN),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', KARABIBER, True),
        ],
    ),
    recipe(
        'penne-arrabbiata', 'Penne Arrabbiata', 'Ana yemek', 'ana', '🌶️', 4, 10, 20,
        'Acı biberli, sarımsaklı domates soslu kalem makarna.',
        'gluten', 'vejetaryen,vegan', (470, 14, 80, 11), 80,
        [
            'Zeytinyağında sarımsak ve pul biberi kokusu çıkana kadar çevirin.',
            'Doğranmış domatesleri ekleyip 15 dakika pişirin, tuzunu ayarlayın.',
            'Penneyi haşlayıp süzün, sosla karıştırıp maydanozla servis edin.',
        ],
        [
            ing('Penne makarna', '1 paket', 500, 'g', PENNE),
            ing('Domates', '5 adet', 750, 'g', DOMATES),
            ing('Sarımsak', '4 diş', 15, 'g', SARIMSAK),
            ing('Zeytinyağı', '4 yemek kaşığı', 50, 'ml', ZEYTINYAGI),
            ing('Maydanoz', '1/2 demet', 1, 'adet', MAYDANOZ),
            ing('Pul biber', '1 tatlı kaşığı', 4, 'g', PUL_BIBER, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'kremali-tavuklu-penne', 'Kremalı Mantarlı Tavuklu Penne', 'Ana yemek', 'ana', '🍄', 4, 15, 25,
        'Tavuk ve mantarın kremalı, peynirli sosta buluştuğu doyurucu makarna.',
        'gluten,sut', '', (690, 40, 70, 27), 90,
        [
            'Tavuğu küp doğrayıp tereyağında suyunu çekene kadar soteleyin.',
            'Dilimlenmiş mantarı ve sarımsağı ekleyip 5 dakika pişirin.',
            'Kremayı ve rende peyniri ekleyip 3-4 dakika koyulaştırın; tuz ve karabiber ekleyin.',
            'Haşlanmış penneyi sosa alıp karıştırın, sıcak servis edin.',
        ],
        [
            ing('Penne makarna', '1 paket', 500, 'g', PENNE),
            ing('Tavuk göğsü', '400 g', 400, 'g', TAVUK),
            ing('Mantar', '250 g', 250, 'g', MANTAR),
            ing('Krema', '1 kutu', 200, 'ml', KREMA),
            ing('Rende peynir (parmesan ya da kaşar)', '1/2 su bardağı', 50, 'g', PARMESAN),
            ing('Sarımsak', '2 diş', 8, 'g', SARIMSAK),
            ing('Tereyağı', '1 yemek kaşığı', 20, 'g', TEREYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', KARABIBER, True),
        ],
    ),
    recipe(
        'firinda-lazanya', 'Fırında Lazanya', 'Ana yemek', 'ana', '🧀', 6, 30, 45,
        'Kıymalı domates sosu ve beşamelin lazanya yapraklarıyla kat kat fırınlandığı yemek.',
        'gluten,sut', '', (620, 30, 52, 32), 89,
        [
            'Kıymayı soğanla kavurun, salça ve rendelenmiş domatesi ekleyip 15 dakika pişirin.',
            'Beşamel: tereyağında unu kavurun, sütü yavaş yavaş ekleyip koyulaşana kadar karıştırın.',
            'Fırın kabına sırayla sos, lazanya yaprağı ve beşamel koyun; 3-4 kat yapın.',
            'Üzerine rende kaşar serpip 180°C fırında 35-40 dakika pişirin, 10 dakika dinlendirip kesin.',
        ],
        [
            ing('Lazanya yaprağı', '1 paket', 500, 'g', LAZANYA),
            ing('Dana kıyma', '500 g', 500, 'g', KIYMA),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Domates', '3 adet', 450, 'g', DOMATES),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Süt', '4 su bardağı', 800, 'ml', SUT),
            ing('Buğday unu', '4 yemek kaşığı', 50, 'g', UN),
            ing('Tereyağı', '3 yemek kaşığı', 50, 'g', TEREYAGI),
            ing('Rende kaşar', '1,5 su bardağı', 150, 'g', KASAR),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'mantarli-risotto', 'Mantarlı Risotto', 'Ana yemek', 'ana', '🍚', 4, 10, 30,
        'Pirincin sıcak suyla yavaş yavaş pişip mantar ve peynirle kremamsı olduğu İtalyan pilavı.',
        'sut', 'vejetaryen', (430, 12, 62, 14), 76,
        [
            'Tereyağında ince doğranmış soğanı yumuşatın, mantarları ekleyip suyunu çekene kadar pişirin.',
            'Yıkanmamış pirinci ekleyip 2 dakika kavurun.',
            'Sıcak suyu kepçe kepçe ekleyin; her seferinde çekmesini bekleyip karıştırarak 20 dakika pişirin.',
            'Ocaktan alırken rende peyniri ve bir parça tereyağını karıştırın.',
        ],
        [
            ing('Pirinç', '1,5 su bardağı', 300, 'g', PIRINC),
            ing('Mantar', '300 g', 300, 'g', MANTAR),
            ing('Kuru soğan', '1 adet', 120, 'g', SOGAN),
            ing('Tereyağı', '3 yemek kaşığı', 50, 'g', TEREYAGI),
            ing('Rende peynir (parmesan ya da kaşar)', '1/2 su bardağı', 50, 'g', PARMESAN),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', KARABIBER, True),
        ],
    ),
    recipe(
        'margarita-pizza', 'Ev Yapımı Margarita Pizza', 'Ana yemek', 'ana', '🍕', 4, 80, 15,
        'Mayalı ince hamur, domates sosu, mozzarella ve fesleğenle evde pizza.',
        'gluten,sut', 'vejetaryen', (610, 24, 82, 20), 91,
        [
            'Un, maya, tuz, 1 su bardağı ılık su ve 2 kaşık zeytinyağıyla yumuşak bir hamur yoğurun; 1 saat mayalandırın.',
            'Domatesleri rendeleyip sarımsak ve tuzla 10 dakika koyulaştırın.',
            'Hamuru iki parçaya bölüp ince açın, tepsiye alın; sosu sürüp mozzarellayı dağıtın.',
            'En yüksek ısıdaki fırında 10-12 dakika pişirin, fesleğen yapraklarıyla servis edin.',
        ],
        [
            ing('Buğday unu', '3 su bardağı', 400, 'g', UN),
            ing('Kuru maya', '1 paket', 10, 'g', MAYA),
            ing('Domates', '3 adet', 450, 'g', DOMATES),
            ing('Mozzarella', '250 g', 250, 'g', MOZZARELLA),
            ing('Zeytinyağı', '3 yemek kaşığı', 40, 'ml', ZEYTINYAGI),
            ing('Sarımsak', '1 diş', 4, 'g', SARIMSAK),
            ing('Fesleğen', '1 avuç', 10, 'g', FESLEGEN),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'sebzeli-frittata', 'Sebzeli Frittata', 'Kahvaltılık', 'ana', '🍳', 2, 10, 15,
        'Patates, biber ve peynirle tavada pişen kalın İtalyan omleti.',
        'yumurta,sut', 'vejetaryen', (390, 20, 22, 25), 74,
        [
            'Küp doğranmış patatesi zeytinyağında yumuşayana kadar kavurun, soğan ve biberi ekleyin.',
            'Yumurtaları tuz ve karabiberle çırpıp rende kaşarı ekleyin.',
            'Karışımı tavaya dökün, kapağı kapalı kısık ateşte 10 dakika pişirin; dilimleyip servis edin.',
        ],
        [
            ing('Yumurta', '5 adet', 5, 'adet', YUMURTA),
            ing('Patates', '1 adet', 150, 'g', PATATES),
            ing('Kuru soğan', '1/2 adet', 60, 'g', SOGAN),
            ing('Kapya biber', '1 adet', 100, 'g', KAPYA),
            ing('Rende kaşar', '1/2 su bardağı', 50, 'g', KASAR),
            ing('Zeytinyağı', '2 yemek kaşığı', 25, 'ml', ZEYTINYAGI),
            ing('Tuz', '1 çay kaşığı', 3, 'g', TUZ, True),
        ],
        slots='kahvalti',
    ),
    recipe(
        'minestrone', 'Minestrone Çorbası', 'Çorba', 'corba', '🥣', 6, 15, 35,
        'Havuç, kabak, patates ve şehriyeyle bol sebzeli İtalyan çorbası.',
        'gluten', 'vejetaryen,vegan', (190, 6, 32, 5), 72,
        [
            'Zeytinyağında doğranmış soğan ve havucu 5 dakika soteleyin.',
            'Küp doğranmış patates, kabak ve rendelenmiş domatesi ekleyip birkaç dakika çevirin.',
            '6 su bardağı sıcak su ekleyip sebzeler yumuşayana kadar 20 dakika pişirin.',
            'Şehriyeyi ekleyip 8 dakika daha pişirin; tuz, karabiber ve fesleğenle tatlandırın.',
        ],
        [
            ing('Havuç', '2 adet', 200, 'g', HAVUC),
            ing('Kabak', '1 adet', 200, 'g', KABAK),
            ing('Patates', '2 adet', 300, 'g', PATATES),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Domates', '2 adet', 300, 'g', DOMATES),
            ing('Arpa şehriye', '1/2 su bardağı', 80, 'g', SEHRIYE),
            ing('Zeytinyağı', '3 yemek kaşığı', 40, 'ml', ZEYTINYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', KARABIBER, True),
        ],
    ),
    recipe(
        'caprese-salata', 'Caprese Salatası', 'Salata', 'salata', '🍅', 4, 10, 0,
        'Dilim domates, mozzarella ve fesleğenin zeytinyağıyla buluştuğu salata.',
        'sut', 'vejetaryen', (210, 10, 6, 16), 78,
        [
            'Domatesleri ve mozzarellayı yuvarlak dilimleyin.',
            'Tabağa domates, mozzarella ve fesleğen yaprağını sırayla dizin.',
            'Zeytinyağı, tuz ve karabiber gezdirip servis edin.',
        ],
        [
            ing('Domates', '3 adet', 450, 'g', DOMATES),
            ing('Mozzarella', '200 g', 200, 'g', MOZZARELLA),
            ing('Fesleğen', '1 avuç', 10, 'g', FESLEGEN),
            ing('Zeytinyağı', '3 yemek kaşığı', 40, 'ml', ZEYTINYAGI),
            ing('Tuz', '1 çay kaşığı', 2, 'g', TUZ, True),
        ],
    ),
    recipe(
        'parmesanli-roka', 'Parmesanlı Roka Salatası', 'Salata', 'salata', '🥗', 4, 10, 0,
        'Roka, peynir rendesi, limon ve zeytinyağıyla hafif bir yan salata.',
        'sut', 'vejetaryen', (130, 6, 4, 10), 70,
        [
            'Rokaları yıkayıp kurulayın.',
            'Limon suyu, zeytinyağı ve tuzu çırpıp rokaların üzerine dökün.',
            'Üzerine rende peyniri serpip hemen servis edin.',
        ],
        [
            ing('Roka', '2 demet', 2, 'adet', ROKA),
            ing('Rende peynir (parmesan ya da kaşar)', '1/3 su bardağı', 40, 'g', PARMESAN),
            ing('Limon', '1 adet', 120, 'g', LIMON),
            ing('Zeytinyağı', '3 yemek kaşığı', 40, 'ml', ZEYTINYAGI),
            ing('Tuz', '1 çay kaşığı', 2, 'g', TUZ, True),
        ],
    ),
    recipe(
        'sarimsakli-ekmek', 'Sarımsaklı Ekmek', 'Yanında', 'yan', '🥖', 4, 5, 10,
        'Tereyağı, sarımsak ve maydanozla fırında kızaran baget; makarnanın yanına.',
        'gluten,sut', 'vejetaryen', (260, 6, 34, 11), 80,
        [
            'Yumuşak tereyağını ezilmiş sarımsak, kıyılmış maydanoz ve tuzla karıştırın.',
            'Bageti çapraz dilimleyip her dilime sürün.',
            '200°C fırında kenarları kızarana kadar 8-10 dakika pişirin.',
        ],
        [
            ing('Baget ekmek', '1 adet', 1, 'adet', EKMEK),
            ing('Tereyağı', '3 yemek kaşığı', 50, 'g', TEREYAGI),
            ing('Sarımsak', '3 diş', 12, 'g', SARIMSAK),
            ing('Maydanoz', '1/4 demet', 1, 'adet', MAYDANOZ),
            ing('Tuz', '1 tutam', 1, 'g', TUZ, True),
        ],
        pairs_with=ITALYAN_PASTA,
    ),
    recipe(
        'tiramisu', 'Tiramisu', 'Tatlı', 'tatli', '☕', 6, 30, 0,
        'Kahveye batırılmış kedi dili bisküvi ve labneli kremayla soğuk İtalyan tatlısı.',
        'gluten,sut,yumurta', 'vejetaryen', (430, 8, 40, 26), 92,
        [
            'Kahveyi 1,5 su bardağı sıcak suda eritip soğutun.',
            'Labne, krema ve şekeri mikserle kabarana kadar çırpın.',
            'Kedi dililerini kahveye hızlıca batırıp kabın tabanına dizin, üzerine kremanın yarısını yayın.',
            'Bir kat daha yapın, üzerine kakao eleyin; buzdolabında en az 4 saat bekletin.',
        ],
        [
            ing('Kedi dili bisküvi', '1 paket', 200, 'g', KEDI_DILI),
            ing('Labne', '1 kutu', 400, 'g', LABNE),
            ing('Krema', '1 kutu', 200, 'ml', KREMA),
            ing('Granül kahve', '2 yemek kaşığı', 10, 'g', KAHVE),
            ing('Kakao', '2 yemek kaşığı', 15, 'g', KAKAO),
            ing('Toz şeker', '1/2 su bardağı', 90, 'g', SEKER),
        ],
    ),
    recipe(
        'panna-cotta', 'Çilekli Panna Cotta', 'Tatlı', 'tatli', '🍓', 4, 15, 5,
        'Kremanın jelatinle hafifçe donduğu, çilek soslu İtalyan tatlısı.',
        'sut', '', (360, 4, 30, 25), 74,
        [
            'Jelatini 3 yemek kaşığı soğuk suda 5 dakika bekletin.',
            'Krema, süt ve şekeri kaynamaya yakın ısıtın, ocaktan alıp jelatini eritin.',
            'Kaselere paylaştırıp buzdolabında 4 saat dondurun.',
            'Çilekleri biraz şekerle ezip sos yapın, servis ederken üzerine dökün.',
        ],
        [
            ing('Krema', '2 kutu', 400, 'ml', KREMA),
            ing('Süt', '1 su bardağı', 200, 'ml', SUT),
            ing('Toz jelatin', '1 paket', 10, 'g', JELATIN),
            ing('Çilek', '250 g', 250, 'g', CILEK),
            ing('Toz şeker', '1/2 su bardağı', 90, 'g', SEKER),
        ],
    ),
    recipe(
        'ev-limonatasi', 'Ev Limonatası', 'İçecek', 'icecek', '🍋', 4, 15, 0,
        'Taze limon ve naneyle hazırlanan, şekeri ayarlanabilen soğuk limonata.',
        '', 'vejetaryen,vegan', (110, 0, 28, 0), 70,
        [
            'Limonların kabuğunu rendeleyip şekerle ezin, 15 dakika bekletin.',
            'Limonların suyunu sıkın, 1 litre soğuk suyla birlikte şekere ekleyip eritin.',
            'Süzüp nane yapraklarıyla buz üstünde servis edin.',
        ],
        [
            ing('Limon', '4 adet', 480, 'g', LIMON),
            ing('Toz şeker', '3/4 su bardağı', 130, 'g', SEKER),
            ing('Taze nane', '3-4 dal', 1, 'adet', NANE),
        ],
    ),
]

UZAKDOGU_MAINS = 'tavuk-teriyaki,tatli-eksi-tavuk,etli-brokoli,tavuk-kori,kung-pao-tavuk'

UZAKDOGU = [
    recipe(
        'sebzeli-tavuklu-noodle', 'Sebzeli Tavuklu Noodle', 'Ana yemek', 'ana', '🍜', 4, 15, 15,
        'Wok usulü yüksek ateşte sotelenmiş tavuk, sebze ve soya soslu noodle.',
        'gluten,soya', '', (520, 32, 66, 14), 90,
        [
            'Noodle\'ı paketteki gibi haşlayıp süzün.',
            'Tavuğu ince şeritler hâlinde doğrayıp çok kızgın yağda soteleyin.',
            'Jülyen havuç, lahana, sarımsak ve zencefili ekleyip 3-4 dakika çevirin.',
            'Noodle ve soya sosunu ekleyip karıştırın, yeşil soğanla servis edin.',
        ],
        [
            ing('Noodle', '2 paket', 300, 'g', NOODLE),
            ing('Tavuk göğsü', '400 g', 400, 'g', TAVUK),
            ing('Havuç', '1 adet', 100, 'g', HAVUC),
            ing('Beyaz lahana', '1/4 adet', 300, 'g', LAHANA),
            ing('Yeşil soğan', '1/2 demet', 1, 'adet', YESIL_SOGAN),
            ing('Soya sosu', '4 yemek kaşığı', 60, 'ml', SOYA),
            ing('Sarımsak', '2 diş', 8, 'g', SARIMSAK),
            ing('Zencefil', '1 parça', 10, 'g', ZENCEFIL),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
        ],
    ),
    recipe(
        'tavuk-teriyaki', 'Tavuk Teriyaki', 'Ana yemek', 'ana', '🍗', 4, 10, 20,
        'Soya sosu, bal ve zencefille parlak bir sosa bulanmış Japon usulü tavuk.',
        'gluten,soya,susam', '', (380, 36, 20, 16), 88,
        [
            'Soya sosu, bal, rendelenmiş zencefil ve sarımsağı karıştırıp sos hazırlayın.',
            'Tavuğu kuşbaşı doğrayıp yağda kızarana kadar pişirin.',
            'Sosu ekleyip 3-4 dakika, sos koyulaşıp tavuğu kaplayana kadar pişirin.',
            'Üzerine susam ve yeşil soğan serpip pilavla servis edin.',
        ],
        [
            ing('Tavuk göğsü', '600 g', 600, 'g', TAVUK),
            ing('Soya sosu', '5 yemek kaşığı', 75, 'ml', SOYA),
            ing('Bal', '2 yemek kaşığı', 40, 'g', BAL),
            ing('Zencefil', '1 parça', 10, 'g', ZENCEFIL),
            ing('Sarımsak', '2 diş', 8, 'g', SARIMSAK),
            ing('Susam', '1 yemek kaşığı', 10, 'g', SUSAM),
            ing('Yeşil soğan', '1/2 demet', 1, 'adet', YESIL_SOGAN),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
        ],
    ),
    recipe(
        'tatli-eksi-tavuk', 'Tatlı Ekşi Soslu Tavuk', 'Ana yemek', 'ana', '🥡', 4, 20, 20,
        'Nişastaya bulanıp kızartılan tavuğun renkli biberli tatlı ekşi sosla buluştuğu Çin yemeği.',
        'yumurta,gluten,soya', '', (480, 34, 42, 18), 86,
        [
            'Küp doğranmış tavuğu çırpılmış yumurtaya, sonra nişastaya bulayıp kızgın yağda kızartın.',
            'Ketçap, sirke, şeker, soya sosu ve yarım su bardağı suyu karıştırın.',
            'Biber ve soğanı iri doğrayıp 3 dakika soteleyin, sosu ekleyip koyulaşana kadar pişirin.',
            'Tavukları sosa alıp karıştırın, hemen servis edin.',
        ],
        [
            ing('Tavuk göğsü', '500 g', 500, 'g', TAVUK),
            ing('Yumurta', '1 adet', 1, 'adet', YUMURTA),
            ing('Mısır nişastası', '4 yemek kaşığı', 40, 'g', NISASTA),
            ing('Kapya biber', '2 adet', 200, 'g', KAPYA),
            ing('Kuru soğan', '1 adet', 120, 'g', SOGAN),
            ing('Ketçap', '4 yemek kaşığı', 60, 'g', KETCAP),
            ing('Sirke', '2 yemek kaşığı', 30, 'ml', SIRKE),
            ing('Soya sosu', '1 yemek kaşığı', 15, 'ml', SOYA),
            ing('Toz şeker', '2 yemek kaşığı', 25, 'g', SEKER),
            ing('Ayçiçek yağı', '1 su bardağı', 200, 'ml', AYCICEK),
        ],
    ),
    recipe(
        'etli-brokoli', 'Etli Brokoli (Wok)', 'Ana yemek', 'ana', '🥦', 4, 15, 15,
        'İnce dilimlenmiş dana etin brokoliyle soya soslu, sarımsaklı sotesi.',
        'gluten,soya', '', (410, 34, 16, 22), 78,
        [
            'Eti ince şeritler hâlinde dilimleyip soya sosu ve nişastayla 15 dakika marine edin.',
            'Brokoliyi çiçeklerine ayırıp 2 dakika haşlayın, soğuk suya alın.',
            'Kızgın yağda eti 3-4 dakika soteleyin, sarımsak ve zencefili ekleyin.',
            'Brokoliyi ve kalan soya sosunu ekleyip 2 dakika çevirin.',
        ],
        [
            ing('Dana eti (bonfile ya da kuşbaşı)', '500 g', 500, 'g', KUSBASI),
            ing('Brokoli', '1 adet', 500, 'g', BROKOLI),
            ing('Soya sosu', '4 yemek kaşığı', 60, 'ml', SOYA),
            ing('Mısır nişastası', '1 yemek kaşığı', 10, 'g', NISASTA),
            ing('Sarımsak', '3 diş', 12, 'g', SARIMSAK),
            ing('Zencefil', '1 parça', 10, 'g', ZENCEFIL),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
        ],
    ),
    recipe(
        'tavuk-kori', 'Hindistan Cevizli Tavuk Köri', 'Ana yemek', 'ana', '🍛', 4, 15, 25,
        'Tay usulü, hindistan cevizi sütüyle kremamsı ve hafif acı köri soslu tavuk.',
        '', '', (460, 34, 14, 30), 82,
        [
            'Doğranmış soğanı yağda yumuşatın, sarımsak, zencefil ve köriyi ekleyip 1 dakika çevirin.',
            'Kuşbaşı tavuğu ekleyip rengi dönene kadar pişirin.',
            'Hindistan cevizi sütü ve küp doğranmış kapya biberi ekleyip 15 dakika kısık ateşte pişirin.',
            'Tuzunu ayarlayıp yasemin pilavıyla servis edin.',
        ],
        [
            ing('Tavuk göğsü', '600 g', 600, 'g', TAVUK),
            ing('Hindistan cevizi sütü', '1 kutu', 400, 'ml', HINDISTAN_SUTU),
            ing('Köri', '2 tatlı kaşığı', 8, 'g', KORI),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Kapya biber', '1 adet', 100, 'g', KAPYA),
            ing('Sarımsak', '2 diş', 8, 'g', SARIMSAK),
            ing('Zencefil', '1 parça', 10, 'g', ZENCEFIL),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'kung-pao-tavuk', 'Kung Pao Tavuk', 'Ana yemek', 'ana', '🥜', 4, 15, 15,
        'Yer fıstığı, acı biber ve soya soslu, Sichuan usulü tavuk sote.',
        'gluten,soya,kuruyemis', '', (450, 38, 16, 26), 80,
        [
            'Küp tavuğu soya sosu ve nişastayla karıştırıp 10 dakika bekletin.',
            'Kızgın yağda tavuğu kızartın, kenara alın.',
            'Aynı tavada sarımsak, pul biber ve kapya biberi çevirin; sirke, şeker ve kalan soya sosunu ekleyin.',
            'Tavuğu ve yer fıstığını ekleyip karıştırın, yeşil soğanla servis edin.',
        ],
        [
            ing('Tavuk göğsü', '500 g', 500, 'g', TAVUK),
            ing('Yer fıstığı', '1/2 su bardağı', 80, 'g', YER_FISTIGI),
            ing('Kapya biber', '1 adet', 100, 'g', KAPYA),
            ing('Yeşil soğan', '1/2 demet', 1, 'adet', YESIL_SOGAN),
            ing('Soya sosu', '4 yemek kaşığı', 60, 'ml', SOYA),
            ing('Sirke', '1 yemek kaşığı', 15, 'ml', SIRKE),
            ing('Mısır nişastası', '1 yemek kaşığı', 10, 'g', NISASTA),
            ing('Sarımsak', '3 diş', 12, 'g', SARIMSAK),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
            ing('Pul biber', '1 tatlı kaşığı', 4, 'g', PUL_BIBER, True),
            ing('Toz şeker', '1 tatlı kaşığı', 5, 'g', SEKER, True),
        ],
    ),
    recipe(
        'yumurtali-fried-rice', 'Yumurtalı Sebzeli Fried Rice', 'Ana yemek', 'ana', '🍳', 4, 10, 15,
        'Önceden pişmiş pirincin yumurta, bezelye ve havuçla wokta kavrulduğu Çin pilavı.',
        'yumurta,gluten,soya', 'vejetaryen', (420, 13, 64, 12), 84,
        [
            'Pirinci haşlayıp süzün ve soğumaya bırakın (bir gün önceden pişmiş pilav en iyisidir).',
            'Kızgın yağda küp havuç ve bezelyeyi 3 dakika soteleyin.',
            'Sebzeleri kenara itip yumurtaları kırın, karıştırarak pişirin.',
            'Pirinci ve soya sosunu ekleyip yüksek ateşte 3-4 dakika kavurun, yeşil soğanla servis edin.',
        ],
        [
            ing('Pirinç', '2 su bardağı', 400, 'g', PIRINC),
            ing('Yumurta', '3 adet', 3, 'adet', YUMURTA),
            ing('Havuç', '1 adet', 100, 'g', HAVUC),
            ing('Bezelye', '1 su bardağı', 150, 'g', BEZELYE),
            ing('Yeşil soğan', '1/2 demet', 1, 'adet', YESIL_SOGAN),
            ing('Soya sosu', '3 yemek kaşığı', 45, 'ml', SOYA),
            ing('Ayçiçek yağı', '3 yemek kaşığı', 40, 'ml', AYCICEK),
        ],
    ),
    recipe(
        'tamagoyaki', 'Tamagoyaki (Japon Omleti)', 'Kahvaltılık', 'ana', '🥚', 2, 5, 10,
        'Hafif tatlı, soya soslu yumurtanın kat kat sarılarak piştiği Japon kahvaltılığı.',
        'yumurta,gluten,soya', 'vejetaryen', (230, 15, 6, 15), 66,
        [
            'Yumurtaları şeker ve soya sosuyla çırpın.',
            'Yağlanmış tavaya ince bir kat dökün, yarı pişince rulo yapıp tavanın kenarına itin.',
            'Kalan karışımı kat kat ekleyip her seferinde ruloyu sarın; dilimleyip servis edin.',
        ],
        [
            ing('Yumurta', '4 adet', 4, 'adet', YUMURTA),
            ing('Soya sosu', '1 tatlı kaşığı', 5, 'ml', SOYA),
            ing('Ayçiçek yağı', '1 yemek kaşığı', 15, 'ml', AYCICEK),
            ing('Toz şeker', '1 tatlı kaşığı', 5, 'g', SEKER, True),
        ],
        slots='kahvalti',
    ),
    recipe(
        'tavuklu-noodle-corbasi', 'Tavuklu Noodle Çorbası', 'Çorba', 'corba', '🍜', 4, 10, 25,
        'Zencefilli, soya soslu berrak tavuk suyunda noodle ve sebze.',
        'gluten,soya', '', (260, 22, 28, 6), 80,
        [
            'Tavuğu 6 su bardağı suda 15 dakika haşlayıp didikleyin, suyunu saklayın.',
            'Suya ince doğranmış havuç, zencefil ve soya sosunu ekleyip 5 dakika kaynatın.',
            'Noodle\'ı ve tavuğu ekleyip 3-4 dakika pişirin, yeşil soğanla servis edin.',
        ],
        [
            ing('Tavuk göğsü', '300 g', 300, 'g', TAVUK),
            ing('Noodle', '1 paket', 150, 'g', NOODLE),
            ing('Havuç', '1 adet', 100, 'g', HAVUC),
            ing('Yeşil soğan', '1/2 demet', 1, 'adet', YESIL_SOGAN),
            ing('Zencefil', '1 parça', 10, 'g', ZENCEFIL),
            ing('Soya sosu', '3 yemek kaşığı', 45, 'ml', SOYA),
        ],
    ),
    recipe(
        'misir-corbasi-cin', 'Çin Usulü Mısır Çorbası', 'Çorba', 'corba', '🌽', 4, 5, 15,
        'Mısır tanelerinin yumurta şeritleriyle koyulaştığı hafif Çin çorbası.',
        'yumurta', 'vejetaryen', (170, 7, 26, 5), 64,
        [
            'Mısırı 5 su bardağı suyla 10 dakika kaynatın.',
            'Nişastayı az soğuk suyla açıp ekleyin, koyulaşana kadar karıştırın.',
            'Çırpılmış yumurtayı ince bir akışla dökerken çatalla yavaşça karıştırın.',
            'Tuz, karabiber ve yeşil soğanla servis edin.',
        ],
        [
            ing('Mısır (konserve)', '2 kutu', 400, 'g', MISIR),
            ing('Yumurta', '2 adet', 2, 'adet', YUMURTA),
            ing('Mısır nişastası', '2 yemek kaşığı', 20, 'g', NISASTA),
            ing('Yeşil soğan', '1/4 demet', 1, 'adet', YESIL_SOGAN),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', KARABIBER, True),
        ],
    ),
    recipe(
        'susamli-salatalik', 'Susamlı Salatalık Salatası', 'Salata', 'salata', '🥒', 4, 10, 0,
        'Sirke, soya sosu ve susamla Japon usulü ferah salatalık salatası.',
        'gluten,soya,susam', 'vejetaryen,vegan', (70, 2, 7, 4), 70,
        [
            'Salatalıkları ince halka doğrayıp biraz tuzla 10 dakika bekletin, suyunu süzün.',
            'Sirke, soya sosu ve şekeri karıştırın.',
            'Salatalıklara dökün, kavrulmuş susam serpip soğuk servis edin.',
        ],
        [
            ing('Salatalık', '4 adet', 500, 'g', SALATALIK),
            ing('Sirke', '3 yemek kaşığı', 45, 'ml', SIRKE),
            ing('Soya sosu', '1 yemek kaşığı', 15, 'ml', SOYA),
            ing('Susam', '1 yemek kaşığı', 10, 'g', SUSAM),
            ing('Toz şeker', '1 tatlı kaşığı', 5, 'g', SEKER, True),
        ],
    ),
    recipe(
        'asya-lahana-salatasi', 'Asya Usulü Lahana Salatası', 'Salata', 'salata', '🥬', 4, 15, 0,
        'İnce kıyılmış lahana ve havucun limonlu soya sosuyla çıtır salatası.',
        'gluten,soya,susam', 'vejetaryen,vegan', (90, 3, 12, 4), 62,
        [
            'Lahanayı ince kıyın, havucu jülyen doğrayın, yeşil soğanı halka kesin.',
            'Limon suyu, soya sosu ve şekeri çırpın.',
            'Sebzelerle karıştırıp üzerine susam serpin.',
        ],
        [
            ing('Beyaz lahana', '1/4 adet', 400, 'g', LAHANA),
            ing('Havuç', '1 adet', 100, 'g', HAVUC),
            ing('Yeşil soğan', '1/2 demet', 1, 'adet', YESIL_SOGAN),
            ing('Limon', '1 adet', 120, 'g', LIMON),
            ing('Soya sosu', '2 yemek kaşığı', 30, 'ml', SOYA),
            ing('Susam', '1 yemek kaşığı', 10, 'g', SUSAM),
        ],
    ),
    recipe(
        'yasemin-pilavi', 'Buharda Beyaz Pirinç', 'Yanında', 'yan', '🍚', 4, 5, 20,
        'Yağsız, tuzsuz pişen yapışkan beyaz pirinç; soslu Uzak Doğu yemeklerinin eşi.',
        '', 'vejetaryen,vegan', (260, 5, 58, 0), 78,
        [
            'Pirinci suyu berraklaşana kadar yıkayın.',
            'Pirincin 1,25 katı suyla kaynatın, kapağı kapalı kısık ateşte 15 dakika pişirin.',
            'Ocaktan alıp 10 dakika demlendirin.',
        ],
        [ing('Pirinç', '2 su bardağı', 400, 'g', PIRINC)],
        pairs_with=UZAKDOGU_MAINS,
    ),
    recipe(
        'muzlu-yufka-rulo', 'Ballı Muzlu Spring Roll', 'Tatlı', 'tatli', '🍌', 4, 15, 10,
        'Muzun yufkaya sarılıp kızartıldığı, ballı tarçınlı Asya sokak tatlısı.',
        'gluten', 'vejetaryen', (320, 4, 48, 13), 66,
        [
            'Yufkayı üçgen dilimlere kesin; geniş kenara muz dilimi koyup tarçın serpin.',
            'Kenarları içe katlayıp rulo yapın, ucunu suyla yapıştırın.',
            'Kızgın yağda altın rengi olana kadar kızartın, üzerine bal gezdirin.',
        ],
        [
            ing('Yufka', '2 yaprak', 1, 'adet', YUFKA),
            ing('Muz', '3 adet', 450, 'g', MUZ),
            ing('Bal', '3 yemek kaşığı', 60, 'g', BAL),
            ing('Ayçiçek yağı', '1 su bardağı', 200, 'ml', AYCICEK),
            ing('Tarçın', '1 çay kaşığı', 2, 'g', TARCIN, True),
        ],
    ),
    recipe(
        'soguk-yesil-cay', 'Limonlu Soğuk Yeşil Çay', 'İçecek', 'icecek', '🍵', 4, 10, 5,
        'Demlenip soğutulmuş yeşil çay, limon ve bal; hafif ve ferah.',
        '', 'vejetaryen', (40, 0, 10, 0), 64,
        [
            '1 litre suyu kaynatıp 80°C\'ye soğumaya bırakın, yeşil çayı 3 dakika demleyin.',
            'Süzüp balı eritin, limon suyunu ekleyin.',
            'Buzdolabında soğutup buzla servis edin.',
        ],
        [
            ing('Yeşil çay', '4 poşet', 8, 'g', YESIL_CAY),
            ing('Limon', '1 adet', 120, 'g', LIMON),
            ing('Bal', '2 yemek kaşığı', 40, 'g', BAL),
        ],
    ),
]

MEKSIKA_MAINS = 'tavuk-fajita,chili-con-carne,etli-taco'

MEKSIKA = [
    recipe(
        'tavuk-fajita', 'Tavuk Fajita', 'Ana yemek', 'ana', '🌯', 4, 15, 15,
        'Baharatlı tavuk ve renkli biberlerin tortillaya sarıldığı Meksika klasiği.',
        'gluten', '', (540, 38, 48, 20), 90,
        [
            'Tavuğu şerit doğrayıp kimyon, pul biber, tuz ve limon suyuyla 15 dakika marine edin.',
            'Kızgın tavada tavuğu soteleyip kenara alın.',
            'Şerit biber ve soğanı aynı tavada 4-5 dakika soteleyin, tavuğu geri ekleyin.',
            'Isıtılmış tortillalara paylaştırıp sarın.',
        ],
        [
            ing('Tavuk göğsü', '500 g', 500, 'g', TAVUK),
            ing('Kapya biber', '2 adet', 200, 'g', KAPYA),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Tortilla (ya da lavaş)', '8 adet', 8, 'adet', TORTILLA),
            ing('Limon', '1 adet', 120, 'g', LIMON),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
            ing('Kimyon', '1 tatlı kaşığı', 3, 'g', KIMYON, True),
            ing('Pul biber', '1 tatlı kaşığı', 4, 'g', PUL_BIBER, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'chili-con-carne', 'Chili Con Carne', 'Ana yemek', 'ana', '🌶️', 4, 15, 40,
        'Kıyma, kırmızı fasulye ve mısırın kimyonlu, acılı domates sosunda piştiği yahni.',
        '', '', (520, 34, 42, 22), 84,
        [
            'Doğranmış soğan ve sarımsağı yağda yumuşatın, kıymayı ekleyip kavurun.',
            'Salça, kimyon ve pul biberi ekleyip 1 dakika çevirin.',
            'Rendelenmiş domates, haşlanmış kırmızı fasulye, mısır ve 1 su bardağı su ekleyin.',
            'Kısık ateşte 30 dakika pişirin; pilavla ya da tortillayla servis edin.',
        ],
        [
            ing('Dana kıyma', '400 g', 400, 'g', KIYMA),
            ing('Kırmızı fasulye (haşlanmış)', '1 kavanoz', 400, 'g', FASULYE),
            ing('Mısır (konserve)', '1 kutu', 200, 'g', MISIR),
            ing('Domates', '3 adet', 450, 'g', DOMATES),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Sarımsak', '2 diş', 8, 'g', SARIMSAK),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
            ing('Kimyon', '1 tatlı kaşığı', 3, 'g', KIMYON, True),
            ing('Pul biber', '1 tatlı kaşığı', 4, 'g', PUL_BIBER, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'etli-taco', 'Kıymalı Taco', 'Ana yemek', 'ana', '🌮', 4, 15, 15,
        'Baharatlı kıyma, marul, domates ve peynirle doldurulmuş tortillalar.',
        'gluten,sut', '', (560, 30, 40, 30), 88,
        [
            'Kıymayı ince doğranmış soğanla kavurun; kimyon, pul biber ve tuzla tatlandırın.',
            'Marulu ince kıyın, domatesi küp doğrayın.',
            'Tortillaları kuru tavada ısıtın, kıyma, marul, domates ve rende kaşarla doldurup katlayın.',
        ],
        [
            ing('Dana kıyma', '400 g', 400, 'g', KIYMA),
            ing('Tortilla (ya da lavaş)', '8 adet', 8, 'adet', TORTILLA),
            ing('Marul', '1/2 adet', 200, 'g', MARUL),
            ing('Domates', '2 adet', 300, 'g', DOMATES),
            ing('Kuru soğan', '1 adet', 120, 'g', SOGAN),
            ing('Rende kaşar', '1 su bardağı', 100, 'g', KASAR),
            ing('Kimyon', '1 tatlı kaşığı', 3, 'g', KIMYON, True),
            ing('Pul biber', '1 tatlı kaşığı', 4, 'g', PUL_BIBER, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'peynirli-quesadilla', 'Peynirli Quesadilla', 'Ana yemek', 'ana', '🧀', 2, 10, 10,
        'Kaşar, biber ve mısırla doldurulup tavada kızartılan tortilla.',
        'gluten,sut', 'vejetaryen', (520, 22, 50, 26), 80,
        [
            'Biberi küçük küp doğrayın, mısırın suyunu süzün.',
            'Tortillanın yarısına rende kaşar, biber ve mısır koyup kapatın.',
            'Tavada iki yüzü de kızarıp peynir eriyene kadar pişirin, üçgen kesip servis edin.',
        ],
        [
            ing('Tortilla (ya da lavaş)', '4 adet', 4, 'adet', TORTILLA),
            ing('Rende kaşar', '1,5 su bardağı', 150, 'g', KASAR),
            ing('Kapya biber', '1 adet', 100, 'g', KAPYA),
            ing('Mısır (konserve)', '1/2 kutu', 100, 'g', MISIR),
        ],
        slots='kahvalti,ogle,aksam',
    ),
    recipe(
        'burrito-bowl', 'Tavuklu Burrito Kasesi', 'Ana yemek', 'ana', '🥙', 4, 20, 25,
        'Pilav, kırmızı fasulye, mısır, tavuk ve avokadonun bir kasede buluştuğu Meksika tabağı.',
        '', '', (610, 38, 74, 16), 82,
        [
            'Pirinci haşlayıp süzün, limon suyuyla karıştırın.',
            'Tavuğu kimyon, pul biber ve tuzla tavada pişirip dilimleyin.',
            'Fasulye ve mısırı ısıtın; domatesi ve avokadoyu küp doğrayın.',
            'Kaselere pilavı koyup üzerine diğer malzemeleri dizin.',
        ],
        [
            ing('Pirinç', '1,5 su bardağı', 300, 'g', PIRINC),
            ing('Tavuk göğsü', '500 g', 500, 'g', TAVUK),
            ing('Kırmızı fasulye (haşlanmış)', '1 kavanoz', 400, 'g', FASULYE),
            ing('Mısır (konserve)', '1 kutu', 200, 'g', MISIR),
            ing('Avokado', '1 adet', 200, 'g', AVOKADO),
            ing('Domates', '2 adet', 300, 'g', DOMATES),
            ing('Limon', '1 adet', 120, 'g', LIMON),
            ing('Kimyon', '1 tatlı kaşığı', 3, 'g', KIMYON, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'huevos-rancheros', 'Huevos Rancheros', 'Kahvaltılık', 'ana', '🍳', 2, 10, 15,
        'Acılı domates sosunda pişen yumurtalar, sıcak tortillanın üzerinde; Meksika kahvaltısı.',
        'yumurta,gluten', 'vejetaryen', (420, 20, 34, 22), 72,
        [
            'Soğan ve biberi yağda yumuşatın, rendelenmiş domates ve pul biberi ekleyip 8 dakika pişirin.',
            'Sosta çukurlar açıp yumurtaları kırın, kapağı kapalı beyazları pişene kadar bekleyin.',
            'Isıtılmış tortillaların üzerine alıp servis edin.',
        ],
        [
            ing('Yumurta', '4 adet', 4, 'adet', YUMURTA),
            ing('Domates', '3 adet', 450, 'g', DOMATES),
            ing('Kuru soğan', '1/2 adet', 60, 'g', SOGAN),
            ing('Sivri biber', '2 adet', 70, 'g', BIBER),
            ing('Tortilla (ya da lavaş)', '2 adet', 2, 'adet', TORTILLA),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
            ing('Pul biber', '1 çay kaşığı', 2, 'g', PUL_BIBER, True),
            ing('Tuz', '1 çay kaşığı', 3, 'g', TUZ, True),
        ],
        slots='kahvalti',
    ),
    recipe(
        'tortilla-corbasi', 'Tavuklu Tortilla Çorbası', 'Çorba', 'corba', '🍲', 4, 15, 25,
        'Domatesli, kimyonlu tavuk çorbası; üzerine kızarmış tortilla şeritleri.',
        'gluten', '', (290, 24, 26, 10), 70,
        [
            'Soğan ve sarımsağı yağda yumuşatın, rendelenmiş domates ve kimyonu ekleyin.',
            'Küp tavuk ve 5 su bardağı su ekleyip 15 dakika pişirin.',
            'Mısırı ve fasulyeyi ekleyip 5 dakika daha kaynatın, limon suyu sıkın.',
            'Tortillayı şerit kesip tavada kızartın, çorbanın üzerine koyup servis edin.',
        ],
        [
            ing('Tavuk göğsü', '300 g', 300, 'g', TAVUK),
            ing('Domates', '3 adet', 450, 'g', DOMATES),
            ing('Kuru soğan', '1 adet', 120, 'g', SOGAN),
            ing('Sarımsak', '2 diş', 8, 'g', SARIMSAK),
            ing('Mısır (konserve)', '1/2 kutu', 100, 'g', MISIR),
            ing('Kırmızı fasulye (haşlanmış)', '1/2 kavanoz', 200, 'g', FASULYE),
            ing('Tortilla (ya da lavaş)', '2 adet', 2, 'adet', TORTILLA),
            ing('Limon', '1/2 adet', 60, 'g', LIMON),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 25, 'ml', AYCICEK),
            ing('Kimyon', '1 tatlı kaşığı', 3, 'g', KIMYON, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    ),
    recipe(
        'guacamole', 'Guacamole', 'Salata', 'salata', '🥑', 4, 10, 0,
        'Ezilmiş avokado, domates, soğan ve limonla yapılan Meksika mezesi.',
        '', 'vejetaryen,vegan', (170, 2, 10, 15), 84,
        [
            'Avokadoları çatalla ezin, hemen limon suyunu ekleyin.',
            'Çok ince doğranmış soğan, domates ve maydanozu karıştırın.',
            'Tuzunu ayarlayıp tortilla ya da sebzeyle servis edin.',
        ],
        [
            ing('Avokado', '2 adet', 400, 'g', AVOKADO),
            ing('Domates', '1 adet', 150, 'g', DOMATES),
            ing('Kuru soğan', '1/2 adet', 60, 'g', SOGAN),
            ing('Limon', '1 adet', 120, 'g', LIMON),
            ing('Maydanoz', '1/4 demet', 1, 'adet', MAYDANOZ),
            ing('Tuz', '1 çay kaşığı', 3, 'g', TUZ, True),
        ],
    ),
    recipe(
        'meksika-fasulye-salatasi', 'Mısırlı Kırmızı Fasulye Salatası', 'Salata', 'salata', '🫘', 4, 15, 0,
        'Kırmızı fasulye, mısır ve renkli biberle limonlu doyurucu salata.',
        '', 'vejetaryen,vegan', (210, 9, 30, 7), 68,
        [
            'Fasulye ve mısırın suyunu süzüp durulayın.',
            'Biber ve soğanı küçük küp doğrayın.',
            'Hepsini limon suyu, zeytinyağı, kimyon ve tuzla karıştırın.',
        ],
        [
            ing('Kırmızı fasulye (haşlanmış)', '1 kavanoz', 400, 'g', FASULYE),
            ing('Mısır (konserve)', '1 kutu', 200, 'g', MISIR),
            ing('Kapya biber', '1 adet', 100, 'g', KAPYA),
            ing('Kuru soğan', '1/2 adet', 60, 'g', SOGAN),
            ing('Limon', '1 adet', 120, 'g', LIMON),
            ing('Zeytinyağı', '2 yemek kaşığı', 25, 'ml', ZEYTINYAGI),
            ing('Kimyon', '1 çay kaşığı', 2, 'g', KIMYON, True),
            ing('Tuz', '1 çay kaşığı', 3, 'g', TUZ, True),
        ],
    ),
    recipe(
        'meksika-pilavi', 'Meksika Pilavı', 'Yanında', 'yan', '🍅', 4, 10, 25,
        'Domates, soğan ve sarımsakla kırmızımsı renk alan baharatlı pirinç pilavı.',
        '', 'vejetaryen,vegan', (290, 5, 56, 6), 74,
        [
            'Yağda soğan ve sarımsağı yumuşatın, yıkanmış pirinci ekleyip 3 dakika kavurun.',
            'Salça ve rendelenmiş domatesi ekleyip 2 dakika çevirin.',
            '2,5 su bardağı sıcak su, kimyon ve tuzu ekleyip suyunu çekene kadar pişirin.',
        ],
        [
            ing('Pirinç', '2 su bardağı', 400, 'g', PIRINC),
            ing('Domates', '1 adet', 150, 'g', DOMATES),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Kuru soğan', '1/2 adet', 60, 'g', SOGAN),
            ing('Sarımsak', '1 diş', 4, 'g', SARIMSAK),
            ing('Ayçiçek yağı', '3 yemek kaşığı', 40, 'ml', AYCICEK),
            ing('Kimyon', '1 çay kaşığı', 2, 'g', KIMYON, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
        pairs_with=MEKSIKA_MAINS,
    ),
    recipe(
        'churros', 'Tarçınlı Churros', 'Tatlı', 'tatli', '🍩', 4, 15, 15,
        'Sıcak hamurun sıkılıp kızartıldığı, tarçınlı şekere bulanmış çıtır çubuklar.',
        'gluten,sut', 'vejetaryen', (380, 5, 50, 18), 80,
        [
            '1 su bardağı su, tereyağı ve bir tutam tuzu kaynatın; unu ekleyip top olana kadar karıştırın.',
            'Hamuru yıldız uçlu sıkma torbasına alın.',
            'Kızgın yağa 10 cm\'lik parçalar sıkıp altın rengi olana kadar kızartın.',
            'Sıcakken tarçınlı şekere bulayın.',
        ],
        [
            ing('Buğday unu', '1 su bardağı', 130, 'g', UN),
            ing('Tereyağı', '2 yemek kaşığı', 30, 'g', TEREYAGI),
            ing('Toz şeker', '1/2 su bardağı', 90, 'g', SEKER),
            ing('Ayçiçek yağı', '2 su bardağı', 400, 'ml', AYCICEK),
            ing('Tarçın', '1 tatlı kaşığı', 3, 'g', TARCIN, True),
        ],
    ),
    recipe(
        'horchata', 'Horchata (Tarçınlı Pirinç İçeceği)', 'İçecek', 'icecek', '🥛', 4, 10, 0,
        'Bir gece bekletilen pirincin süt ve tarçınla çekildiği tatlı, soğuk Meksika içeceği.',
        'sut', 'vejetaryen', (180, 5, 32, 4), 62,
        [
            'Pirinci 3 su bardağı suyla bir gece bekletin.',
            'Pirinci suyuyla birlikte blenderdan geçirip süzün.',
            'Süt, şeker ve tarçınla karıştırıp buzla servis edin.',
        ],
        [
            ing('Pirinç', '1/2 su bardağı', 100, 'g', PIRINC),
            ing('Süt', '2 su bardağı', 400, 'ml', SUT),
            ing('Toz şeker', '1/3 su bardağı', 60, 'g', SEKER),
            ing('Tarçın', '1 tatlı kaşığı', 3, 'g', TARCIN, True),
        ],
    ),
]

RECIPES = {'italyan': ITALYAN, 'uzakdogu': UZAKDOGU, 'meksika': MEKSIKA}

INGREDIENT_COLS = (
    'recipe_id', 'position', 'name', 'amount_text', 'quantity', 'unit', 'search_term', 'exclude_terms',
    'categories', 'is_pantry',
)


def upgrade() -> None:
    op.add_column('meal_plans', sa.Column('cuisines', sa.String(length=255), server_default='', nullable=False))
    op.add_column('recipes', sa.Column('missing_ingredients', sa.String(length=512), nullable=True))
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE meal_plans SET cuisines = c.slug FROM cuisines c WHERE c.id = meal_plans.cuisine_id"
    ))
    conn.execute(sa.text("UPDATE cuisines SET name = 'Türk Mutfağı' WHERE slug = 'anadolu'"))

    cuisines = sa.table('cuisines', *(sa.column(c) for c in ('slug', 'name', 'icon', 'is_default', 'is_active', 'position')))
    conn.execute(cuisines.insert(), [
        {'slug': s, 'name': n, 'icon': i, 'is_default': False, 'is_active': True, 'position': p}
        for s, n, i, p in CUISINES
    ])

    recipes = sa.table('recipes', *(sa.column(c) for c in (
        'id', 'cuisine_id', 'slug', 'name', 'course', 'course_type', 'pairs_with', 'meal_slots', 'servings',
        'prep_minutes', 'cook_minutes', 'description', 'steps', 'icon', 'is_active', 'allergens', 'diets',
        'kcal', 'protein_g', 'carbs_g', 'fat_g', 'popularity',
    )))
    ingredients = sa.table('recipe_ingredients', *(sa.column(c) for c in INGREDIENT_COLS))
    for cuisine_slug, rows in RECIPES.items():
        cuisine_id = conn.execute(sa.text('SELECT id FROM cuisines WHERE slug = :s'), {'s': cuisine_slug}).scalar_one()
        for r in rows:
            k, p, c, f = r['nutrition']
            recipe_id = conn.execute(
                recipes.insert().returning(recipes.c.id),
                {
                    'cuisine_id': cuisine_id,
                    **{key: r[key] for key in (
                        'slug', 'name', 'course', 'course_type', 'meal_slots', 'servings', 'prep_minutes',
                        'cook_minutes', 'description', 'icon', 'allergens', 'diets', 'popularity', 'pairs_with',
                    )},
                    'steps': '\n'.join(r['steps']),
                    'is_active': True,
                    'kcal': k, 'protein_g': p, 'carbs_g': c, 'fat_g': f,
                },
            ).scalar_one()
            conn.execute(ingredients.insert(), [
                dict(zip(INGREDIENT_COLS, (recipe_id, i, *row))) for i, row in enumerate(r['ingredients'])
            ])


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [s for s, *_ in CUISINES]
    conn.execute(sa.text(
        'DELETE FROM meal_plans WHERE cuisine_id IN (SELECT id FROM cuisines WHERE slug = ANY(:s))'
    ), {'s': slugs})
    conn.execute(sa.text(
        'DELETE FROM meal_plan_entries WHERE recipe_id IN '
        '(SELECT r.id FROM recipes r JOIN cuisines c ON c.id = r.cuisine_id WHERE c.slug = ANY(:s))'
    ), {'s': slugs})
    conn.execute(sa.text('DELETE FROM cuisines WHERE slug = ANY(:s)'), {'s': slugs})
    conn.execute(sa.text("UPDATE cuisines SET name = 'Anadolu (Türk) Mutfağı' WHERE slug = 'anadolu'"))
    op.drop_column('recipes', 'missing_ingredients')
    op.drop_column('meal_plans', 'cuisines')
