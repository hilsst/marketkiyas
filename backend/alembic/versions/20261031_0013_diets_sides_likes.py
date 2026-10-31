"""recipes: allergens, diets, nutrition, popularity, likes; side dishes (pilav, makarna, püre) + 25 popular recipes

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-31 15:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0013'
down_revision: str | None = '0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOMATES = ('domates', 'salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl')
SOGAN = ('kuru sogan', 'toz,granul')
BIBER = ('sivri biber', 'tursu,toz')
SALCA = ('domates salcasi', None)
TEREYAGI = ('tereyagi', None)
ZEYTINYAGI = ('zeytinyagi', None)
AYCICEK = ('aycicek yagi', None)
TUZ = ('tuz', 'tuzsuz,tuzlu')
SUT = ('sut', 'tozu,cikolatali,kakaolu,cilekli,muzlu,laktozsuz,keci,badem,soya')
YOGURT = ('yogurt', 'icecek,meyveli,suzme,cilekli,kakaolu')
LIMON = ('limon', 'sosu,kolonya,tuzu,suyu,aromali')
PATATES = ('patates', 'cips,kizartma,dondurulmus,pure')
KUSBASI = ('dana kusbasi|kusbasi', 'tavuk,hindi,kuzu')
KIYMA = ('dana kiyma|kiyma', 'tavuk,hindi,kuzu')
PIRINC = ('pirinc', 'unu,patlagi,sirkesi')
MAYDANOZ = ('maydanoz', 'kurusu,kuru')
YUMURTA = ('yumurta', 'cikolata,makarna,eriste')
UN = ('bugday unu', None)
SEKER = ('toz seker', 'pudra,esmer,kup')


def ing(name, amount, qty, unit, term, pantry=False):
    """term: (arama ifadesi, elenecek kelimeler)"""
    return (name, amount, qty, unit, term[0], term[1], pantry)


# Mevcut tariflerin alerjenleri, diyetleri, kişi başı yaklaşık besin değerleri (kcal, protein, karbonhidrat,
# yağ gram) ve başlangıç sevilme puanı. Puan, Türk tarif sitelerinde en çok aranan / yapılan klasiklere
# göre verilmiş bir başlangıç tahminidir; kullanıcı beğenileri üstüne eklenir.
EXISTING = {
    'mercimek-corbasi': ('sut,gluten', 'vejetaryen', (290, 14, 42, 7), 96),
    'kuru-fasulye': ('sut', 'vejetaryen', (470, 22, 64, 14), 95),
    'karniyarik': ('', '', (520, 15, 25, 40), 92),
    'menemen': ('yumurta', 'vejetaryen', (320, 14, 12, 24), 93),
    'tavuk-sote': ('', '', (300, 32, 12, 14), 84),
    'ezogelin-corbasi': ('sut,gluten', 'vejetaryen', (262, 11, 40, 7), 86),
    'yayla-corbasi': ('sut,gluten,yumurta', 'vejetaryen', (220, 8, 25, 10), 72),
    'coban-salatasi': ('', 'vejetaryen,vegan', (110, 2, 9, 8), 88),
    'mevsim-salatasi': ('', 'vejetaryen,vegan', (100, 2, 8, 7), 66),
    'sutlac': ('sut,gluten', 'vejetaryen', (405, 10, 75, 8), 86),
    'irmik-helvasi': ('sut,gluten', 'vejetaryen', (400, 6, 68, 11), 72),
    'ayran': ('sut', 'vejetaryen', (90, 5, 7, 5), 90),
    'salgam': ('', 'vejetaryen,vegan', (20, 1, 4, 0), 62),
    'maden-suyu': ('', 'vejetaryen,vegan', (0, 0, 0, 0), 55),
    'portakal-suyu': ('', 'vejetaryen,vegan', (90, 1, 21, 0), 60),
    'meyve-tabagi': ('', 'vejetaryen,vegan', (185, 2, 45, 1), 62),
    'cevizli-yogurt': ('sut,kuruyemis', 'vejetaryen', (270, 9, 22, 18), 58),
}

# İçeceklerin uyumlu ana yemekleri (yeni ana yemeklerle genişletildi); boş = hepsi
DRINK_PAIRS = {
    'ayran': 'kuru-fasulye,karniyarik,tavuk-sote,izmir-kofte,etli-nohut,manti,tas-kebabi,hunkar-begendi,taze-fasulye,'
             'firinda-tavuk-patates,ispanak-yemegi,mercimek-koftesi',
    'salgam': 'kuru-fasulye,karniyarik,etli-nohut,mercimek-koftesi,izmir-kofte',
    'maden-suyu': 'tavuk-sote,karniyarik,hunkar-begendi,firinda-tavuk-patates,izmir-kofte,imam-bayildi',
    'portakal-suyu': '',
}

PILAV_MAINS = 'kuru-fasulye,etli-nohut,tavuk-sote,karniyarik,tas-kebabi,taze-fasulye'
BULGUR_MAINS = 'kuru-fasulye,etli-nohut,karniyarik,imam-bayildi,tas-kebabi,tavuk-sote'

R = 'ogle,aksam'

RECIPES = [
    # --- Ana yemekler ---
    {
        'slug': 'izmir-kofte', 'name': 'Fırında İzmir Köfte', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 25, 'cook_minutes': 40, 'icon': '🧆',
        'description': 'Patates, domates ve biberle fırında pişen, salçalı soslu köfte.',
        'allergens': 'gluten,yumurta', 'diets': '', 'nutrition': (520, 30, 35, 28), 'popularity': 92,
        'steps': [
            'Kıymayı rendelenmiş soğan, galeta unu, yumurta, tuz, karabiber ve kimyonla yoğurun; parmak köfteler yapın.',
            'Patatesleri elma dilimi doğrayıp hafifçe kızartın ya da fırında yarı pişirin; köfteleri tavada mühürleyin.',
            'Fırın kabına köfte, patates, domates ve biberi sırayla dizin.',
            'Salçayı 2 su bardağı sıcak suyla açıp üzerine dökün.',
            '200°C fırında 30-35 dakika pişirin.',
        ],
        'ingredients': [
            ing('Dana kıyma', '500 g', 500, 'g', KIYMA),
            ing('Galeta unu', '3 yemek kaşığı', 40, 'g', ('galeta unu', None)),
            ing('Kuru soğan', '1 adet', 100, 'g', SOGAN),
            ing('Yumurta', '1 adet', 1, 'adet', YUMURTA),
            ing('Patates', '4 adet', 600, 'g', PATATES),
            ing('Domates', '2 adet', 300, 'g', DOMATES),
            ing('Sivri biber', '3 adet', 100, 'g', BIBER),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', ('karabiber', None), True),
            ing('Kimyon', '1 çay kaşığı', 2, 'g', ('kimyon', None), True),
        ],
    },
    {
        'slug': 'etli-nohut', 'name': 'Etli Nohut', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 15, 'cook_minutes': 75, 'icon': '🫘',
        'description': 'Bir gece önceden ıslatılan nohutun kuşbaşı etle salçalı sosta piştiği klasik.',
        'allergens': 'sut', 'diets': '', 'nutrition': (430, 28, 40, 17), 'popularity': 88,
        'steps': [
            'Nohudu bir gece önceden ıslatın, süzün.',
            'Tereyağında kuşbaşı eti suyunu salıp çekene kadar kavurun.',
            'Doğranmış soğanı ekleyip pembeleştirin, salçayı ekleyip 1 dakika kavurun.',
            'Nohudu ve üzerini 2 parmak geçecek kadar sıcak su ekleyin.',
            'Kısık ateşte nohutlar yumuşayana kadar 60-75 dakika pişirin, tuzunu ekleyin.',
        ],
        'ingredients': [
            ing('Nohut', '1,5 su bardağı', 300, 'g', ('nohut', 'konserve,haslanmis,leblebi,unu')),
            ing('Dana kuşbaşı', '300 g', 300, 'g', KUSBASI),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Domates salçası', '2 yemek kaşığı', 40, 'g', SALCA),
            ing('Tereyağı', '1 yemek kaşığı', 20, 'g', TEREYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Pul biber', '1 çay kaşığı', 2, 'g', ('pul biber', None), True),
        ],
    },
    {
        'slug': 'taze-fasulye', 'name': 'Zeytinyağlı Taze Fasulye', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 20, 'cook_minutes': 45, 'icon': '🫛',
        'description': 'Domates ve soğanla kendi suyunda pişen, ılık ya da soğuk yenen zeytinyağlı.',
        'allergens': '', 'diets': 'vejetaryen,vegan', 'nutrition': (230, 5, 22, 14), 'popularity': 85,
        'steps': [
            'Fasulyelerin uçlarını ve kılçıklarını alıp ikiye bölün.',
            'Zeytinyağında doğranmış soğanı yumuşatın.',
            'Fasulyeleri ekleyip 5 dakika çevirin; rendelenmiş domates, şeker ve tuzu ekleyin.',
            'Yarım su bardağı sıcak su ekleyip kapağı kapalı, kısık ateşte 40 dakika pişirin.',
            'Tenceresinde ılıyınca servis edin.',
        ],
        'ingredients': [
            ing('Taze fasulye', '750 g', 750, 'g', ('taze fasulye|ayse fasulye', 'konserve,dondurulmus')),
            ing('Domates', '2 adet', 300, 'g', DOMATES),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Zeytinyağı', '1/3 su bardağı', 80, 'ml', ZEYTINYAGI),
            ing('Toz şeker', '1 çay kaşığı', 5, 'g', SEKER, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'imam-bayildi', 'name': 'İmam Bayıldı', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 25, 'cook_minutes': 40, 'icon': '🍆',
        'description': 'Bol soğanlı, sarımsaklı iç harçla doldurulmuş zeytinyağlı patlıcan.',
        'allergens': '', 'diets': 'vejetaryen,vegan', 'nutrition': (290, 4, 24, 20), 'popularity': 82,
        'steps': [
            'Patlıcanları alacalı soyup tuzlu suda 20 dakika bekletin, kurulayın ve zeytinyağında hafifçe kızartın.',
            'Kalan yağda piyazlık soğanı, sarımsağı ve biberi yumuşatın; doğranmış domatesi ekleyin.',
            'Harcı tuz, şeker ve kıyılmış maydanozla tatlandırın.',
            'Patlıcanları ortadan yarıp harçla doldurun, fırın kabına dizin, yarım su bardağı su ekleyin.',
            '180°C fırında 30-40 dakika pişirin; ılık ya da soğuk servis edin.',
        ],
        'ingredients': [
            ing('Patlıcan', '4 adet', 1000, 'g', ('patlican', 'salata,kozlenmis,konserve,tursu')),
            ing('Kuru soğan', '2 adet', 300, 'g', SOGAN),
            ing('Domates', '2 adet', 300, 'g', DOMATES),
            ing('Sivri biber', '3 adet', 100, 'g', BIBER),
            ing('Sarımsak', '4 diş', 15, 'g', ('sarimsak', 'toz,granul')),
            ing('Zeytinyağı', '1/2 su bardağı', 120, 'ml', ZEYTINYAGI),
            ing('Maydanoz', '1/2 demet', 1, 'adet', MAYDANOZ),
            ing('Toz şeker', '1 çay kaşığı', 5, 'g', SEKER, True),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'tas-kebabi', 'name': 'Tas Kebabı', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 15, 'cook_minutes': 70, 'icon': '🥘',
        'description': 'Kuşbaşı etin soğan, domates ve biberle ağır ateşte yumuşayana kadar piştiği yemek.',
        'allergens': 'sut', 'diets': '', 'nutrition': (380, 32, 10, 23), 'popularity': 80,
        'steps': [
            'Tereyağında kuşbaşı eti suyunu salıp çekene kadar kavurun.',
            'Doğranmış soğanı ve biberi ekleyip yumuşatın.',
            'Salçayı ve küp doğranmış domatesi ekleyip birkaç dakika çevirin.',
            '2 su bardağı sıcak su ekleyip kapağı kapalı, kısık ateşte et yumuşayana kadar 60 dakika pişirin.',
            'Tuz, karabiber ve kekikle tatlandırıp servis edin.',
        ],
        'ingredients': [
            ing('Dana kuşbaşı', '500 g', 500, 'g', KUSBASI),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Domates', '2 adet', 300, 'g', DOMATES),
            ing('Sivri biber', '2 adet', 70, 'g', BIBER),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Tereyağı', '1 yemek kaşığı', 20, 'g', TEREYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', ('karabiber', None), True),
            ing('Kekik', '1 çay kaşığı', 1, 'g', ('kekik', 'yagi,sabun,cay'), True),
        ],
    },
    {
        'slug': 'hunkar-begendi', 'name': 'Hünkar Beğendi', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 30, 'cook_minutes': 70, 'icon': '👑',
        'description': 'Közlenmiş patlıcanlı, kaşarlı beğendi üzerinde domatesli et yahnisi.',
        'allergens': 'sut,gluten', 'diets': '', 'nutrition': (560, 34, 25, 36), 'popularity': 78,
        'steps': [
            'Eti tereyağında kavurun, soğan ve domatesi ekleyip sıcak suyla kısık ateşte 60 dakika pişirin.',
            'Patlıcanları közleyip kabuklarını soyun ve ince kıyın.',
            'Tereyağında unu kokusu çıkana kadar kavurun, patlıcanı ekleyin.',
            'Sıcak sütü azar azar ekleyip koyulaşana kadar karıştırın; rendelenmiş kaşarı ve tuzu ekleyin.',
            'Beğendiyi tabağa yayıp ortasına et yahnisini koyarak servis edin.',
        ],
        'ingredients': [
            ing('Kuzu ya da dana kuşbaşı', '500 g', 500, 'g', ('kuzu kusbasi|dana kusbasi|kusbasi', 'tavuk,hindi')),
            ing('Patlıcan', '5 adet', 1000, 'g', ('patlican', 'salata,konserve,tursu')),
            ing('Süt', '1,5 su bardağı', 300, 'ml', SUT),
            ing('Tereyağı', '3 yemek kaşığı', 40, 'g', TEREYAGI),
            ing('Buğday unu', '2 yemek kaşığı', 30, 'g', UN),
            ing('Kaşar peyniri', '1 avuç rende', 50, 'g', ('kasar peyniri|kasar', 'tost')),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Domates', '1 adet', 200, 'g', DOMATES),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'manti', 'name': 'Kayseri Mantısı', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 5, 'cook_minutes': 20, 'icon': '🥟',
        'description': 'Hazır mantının sarımsaklı yoğurt ve salçalı tereyağı sosla servis edildiği pratik hali.',
        'allergens': 'gluten,sut,yumurta', 'diets': '', 'nutrition': (520, 20, 70, 18), 'popularity': 90,
        'steps': [
            'Mantıyı kaynayan tuzlu suda paketteki süre kadar haşlayıp süzün.',
            'Yoğurdu ezilmiş sarımsakla çırpın.',
            'Tereyağını eritip salçayı ve pul biberi ekleyip köpürtün.',
            'Mantıyı tabağa alın, üzerine sarımsaklı yoğurt ve sosu gezdirin, naneyle servis edin.',
        ],
        'ingredients': [
            ing('Mantı', '500 g', 500, 'g', ('manti', None)),
            ing('Yoğurt', '2 su bardağı', 500, 'g', YOGURT),
            ing('Sarımsak', '2 diş', 10, 'g', ('sarimsak', 'toz,granul')),
            ing('Tereyağı', '3 yemek kaşığı', 40, 'g', TEREYAGI),
            ing('Domates salçası', '1 tatlı kaşığı', 15, 'g', SALCA),
            ing('Pul biber', '1 çay kaşığı', 2, 'g', ('pul biber', None), True),
            ing('Kuru nane', '1 çay kaşığı', 1, 'g', ('nane', None), True),
        ],
    },
    {
        'slug': 'firinda-tavuk-patates', 'name': 'Fırında Patatesli Tavuk', 'course': 'Ana yemek',
        'course_type': 'ana', 'meal_slots': R, 'servings': 4, 'prep_minutes': 15, 'cook_minutes': 50, 'icon': '🍗',
        'description': 'Salçalı sosla harmanlanan tavuk baget ve patatesin tek tepside piştiği yemek.',
        'allergens': '', 'diets': '', 'nutrition': (540, 38, 38, 26), 'popularity': 86,
        'steps': [
            'Patates ve soğanı iri doğrayın, biber ve domatesi dilimleyin.',
            'Yağ, salça, tuz, karabiber, kekik ve yarım su bardağı suyla sos hazırlayın.',
            'Tavuk ve sebzeleri sosla harmanlayıp tepsiye yayın.',
            '200°C fırında tavuklar kızarana kadar 45-50 dakika pişirin.',
        ],
        'ingredients': [
            ing('Tavuk baget', '1 kg', 1000, 'g', ('tavuk baget|pilic baget|baget', 'pane,haslanmis,fume')),
            ing('Patates', '5 adet', 800, 'g', PATATES),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Domates', '1 adet', 200, 'g', DOMATES),
            ing('Sivri biber', '3 adet', 100, 'g', BIBER),
            ing('Ayçiçek yağı', '4 yemek kaşığı', 60, 'ml', AYCICEK),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Karabiber', '1 çay kaşığı', 2, 'g', ('karabiber', None), True),
            ing('Kekik', '1 çay kaşığı', 1, 'g', ('kekik', 'yagi,sabun,cay'), True),
        ],
    },
    {
        'slug': 'ispanak-yemegi', 'name': 'Kıymalı Ispanak', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 20, 'cook_minutes': 25, 'icon': '🥬',
        'description': 'Az kıyma ve bir avuç pirinçle pişen, yoğurtla yenen ıspanak yemeği.',
        'allergens': '', 'diets': '', 'nutrition': (250, 16, 18, 13), 'popularity': 72,
        'steps': [
            'Ispanağı bol suda yıkayıp iri doğrayın.',
            'Yağda soğanı yumuşatın, kıymayı ekleyip kavurun.',
            'Salçayı ve yıkanmış pirinci ekleyip 1 dakika çevirin.',
            'Ispanağı ve yarım su bardağı sıcak suyu ekleyip kısık ateşte pirinç pişene kadar 20 dakika pişirin.',
        ],
        'ingredients': [
            ing('Ispanak', '1 kg', 1000, 'g', ('ispanak', 'dondurulmus,konserve')),
            ing('Dana kıyma', '200 g', 200, 'g', KIYMA),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Pirinç', '2 yemek kaşığı', 40, 'g', PIRINC),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Ayçiçek yağı', '2 yemek kaşığı', 30, 'ml', AYCICEK),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'mercimek-koftesi', 'name': 'Mercimek Köftesi', 'course': 'Ana yemek', 'course_type': 'ana',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 30, 'cook_minutes': 20, 'icon': '🥙',
        'description': 'Kırmızı mercimek ve köftelik bulgurla yoğrulan, marul yaprağında yenen etsiz köfte.',
        'allergens': 'gluten', 'diets': 'vejetaryen,vegan', 'nutrition': (380, 15, 58, 11), 'popularity': 88,
        'steps': [
            'Mercimeği 3 su bardağı suyla dağılana kadar haşlayın; ocaktan alıp bulguru ekleyin, kapağını kapatıp 20 dakika demlendirin.',
            'Zeytinyağında ince doğranmış soğanı yumuşatın, salçayı ekleyip kavurun.',
            'Soğanlı harcı mercimeğe ekleyip tuz, kimyon ve pul biberle iyice yoğurun.',
            'Yeşil soğan ve maydanozu ekleyip yoğurun; avuçta sıkarak şekil verin.',
            'Marul yapraklarıyla ve limonla servis edin.',
        ],
        'ingredients': [
            ing('Kırmızı mercimek', '1 su bardağı', 200, 'g', ('kirmizi mercimek', None)),
            ing('Köftelik bulgur', '1 su bardağı', 200, 'g', ('koftelik bulgur|ince bulgur', None)),
            ing('Kuru soğan', '1 adet', 150, 'g', SOGAN),
            ing('Zeytinyağı', '4 yemek kaşığı', 60, 'ml', ZEYTINYAGI),
            ing('Domates salçası', '2 yemek kaşığı', 30, 'g', SALCA),
            ing('Yeşil soğan', '1 demet', 1, 'adet', ('yesil sogan|taze sogan', None)),
            ing('Maydanoz', '1 demet', 1, 'adet', MAYDANOZ),
            ing('Marul', '1 adet', 1, 'adet', ('marul|kivircik', 'tohum')),
            ing('Limon', '1 adet', 100, 'g', LIMON),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
            ing('Kimyon', '1 çay kaşığı', 2, 'g', ('kimyon', None), True),
            ing('Pul biber', '1 tatlı kaşığı', 3, 'g', ('pul biber', None), True),
        ],
    },
    # --- Yan yemekler: yalnız pairs_with'teki ana yemeklerin yanında önerilir ---
    {
        'slug': 'pirinc-pilavi', 'name': 'Tereyağlı Pirinç Pilavı', 'course': 'Yanında', 'course_type': 'yan',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 30, 'cook_minutes': 20, 'icon': '🍚',
        'pairs_with': PILAV_MAINS,
        'description': 'Tane tane, tereyağlı klasik pirinç pilavı; kuru fasulyenin ayrılmaz eşi.',
        'allergens': 'sut', 'diets': 'vejetaryen', 'nutrition': (330, 6, 62, 8), 'popularity': 90,
        'steps': [
            'Pirinci ılık tuzlu suda 20 dakika bekletip suyu berraklaşana kadar yıkayın.',
            'Tereyağını eritip süzülmüş pirinci 3-4 dakika kavurun.',
            'Pirincin 1,5 katı sıcak su ve tuzu ekleyin.',
            'Kısık ateşte suyunu çekene kadar pişirin, kağıt havlu örtüp 10 dakika demlendirin.',
        ],
        'ingredients': [
            ing('Pirinç', '2 su bardağı', 300, 'g', PIRINC),
            ing('Tereyağı', '2 yemek kaşığı', 40, 'g', TEREYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'bulgur-pilavi', 'name': 'Domatesli Bulgur Pilavı', 'course': 'Yanında', 'course_type': 'yan',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 10, 'cook_minutes': 25, 'icon': '🌾',
        'pairs_with': BULGUR_MAINS,
        'description': 'Soğan, biber ve domatesle pişen, zeytinyağlı bulgur pilavı.',
        'allergens': 'gluten', 'diets': 'vejetaryen,vegan', 'nutrition': (300, 9, 55, 7), 'popularity': 82,
        'steps': [
            'Zeytinyağında soğan ve biberi yumuşatın.',
            'Salçayı ve rendelenmiş domatesi ekleyip 2 dakika pişirin.',
            'Bulguru ekleyip çevirin, 2,5 su bardağı sıcak su ve tuzu ekleyin.',
            'Kısık ateşte suyunu çekene kadar pişirip 10 dakika demlendirin.',
        ],
        'ingredients': [
            ing('Pilavlık bulgur', '2 su bardağı', 300, 'g', ('pilavlik bulgur|bulgur', 'koftelik,kofte,ince')),
            ing('Kuru soğan', '1 küçük', 100, 'g', SOGAN),
            ing('Sivri biber', '2 adet', 70, 'g', BIBER),
            ing('Domates', '1 adet', 200, 'g', DOMATES),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Zeytinyağı', '3 yemek kaşığı', 40, 'ml', ZEYTINYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'patates-puresi', 'name': 'Patates Püresi', 'course': 'Yanında', 'course_type': 'yan',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 10, 'cook_minutes': 25, 'icon': '🥔',
        'pairs_with': 'tavuk-sote,tas-kebabi',
        'description': 'Sütlü, tereyağlı yumuşacık püre; sulu et ve tavuk yemeklerinin yanına.',
        'allergens': 'sut', 'diets': 'vejetaryen', 'nutrition': (230, 5, 32, 9), 'popularity': 75,
        'steps': [
            'Patatesleri soyup doğrayın, tuzlu suda yumuşayana kadar haşlayın.',
            'Süzüp sıcakken ezin.',
            'Sıcak süt ve tereyağını ekleyip pürüzsüz olana kadar karıştırın; tuzunu ayarlayın.',
        ],
        'ingredients': [
            ing('Patates', '6 adet', 1000, 'g', PATATES),
            ing('Süt', '1 su bardağı', 200, 'ml', SUT),
            ing('Tereyağı', '2 yemek kaşığı', 40, 'g', TEREYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'tereyagli-makarna', 'name': 'Tereyağlı Makarna', 'course': 'Yanında', 'course_type': 'yan',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 2, 'cook_minutes': 12, 'icon': '🍝',
        'pairs_with': 'tavuk-sote,tas-kebabi',
        'description': 'Haşlanıp tereyağıyla harmanlanan sade makarna; tavuk sote ve tas kebabıyla.',
        'allergens': 'gluten,sut', 'diets': 'vejetaryen', 'nutrition': (450, 15, 85, 10), 'popularity': 70,
        'steps': [
            'Makarnayı kaynayan tuzlu suda paketteki süre kadar haşlayın.',
            'Süzüp sıcakken tereyağıyla harmanlayın.',
        ],
        'ingredients': [
            ing('Makarna', '1 paket', 500, 'g', ('makarna|spagetti|penne', None)),
            ing('Tereyağı', '2 yemek kaşığı', 40, 'g', TEREYAGI),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    # --- Çorbalar ---
    {
        'slug': 'domates-corbasi', 'name': 'Domates Çorbası', 'course': 'Çorba', 'course_type': 'corba',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 10, 'cook_minutes': 25, 'icon': '🍅',
        'description': 'Taze domatesle, sütle inceltilmiş kremamsı çorba.',
        'allergens': 'sut,gluten', 'diets': 'vejetaryen', 'nutrition': (160, 4, 16, 9), 'popularity': 84,
        'steps': [
            'Tereyağında unu kokusu çıkana kadar kavurun.',
            'Rendelenmiş domatesi ekleyip 5 dakika pişirin.',
            '4 su bardağı sıcak su ekleyip 15 dakika kaynatın, blenderdan geçirin.',
            'Sıcak sütü ekleyip bir taşım kaynatın, tuzunu ayarlayın.',
        ],
        'ingredients': [
            ing('Domates', '5 adet', 800, 'g', DOMATES),
            ing('Tereyağı', '2 yemek kaşığı', 30, 'g', TEREYAGI),
            ing('Buğday unu', '2 yemek kaşığı', 30, 'g', UN),
            ing('Süt', '1 su bardağı', 200, 'ml', SUT),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'tarhana-corbasi', 'name': 'Tarhana Çorbası', 'course': 'Çorba', 'course_type': 'corba',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 5, 'cook_minutes': 15, 'icon': '🥣',
        'description': 'Ev tarhanasıyla, salçalı ve naneli kış çorbası.',
        'allergens': 'gluten,sut', 'diets': 'vejetaryen', 'nutrition': (140, 4, 18, 6), 'popularity': 76,
        'steps': [
            'Tarhanayı 1 su bardağı soğuk suda 10 dakika ıslatın.',
            'Tereyağında salçayı kavurun, 4 su bardağı sıcak su ekleyin.',
            'Tarhanayı ekleyip sürekli karıştırarak 10 dakika pişirin, tuz ve naneyle tatlandırın.',
        ],
        'ingredients': [
            ing('Tarhana', '4 yemek kaşığı', 80, 'g', ('tarhana', None)),
            ing('Tereyağı', '2 yemek kaşığı', 30, 'g', TEREYAGI),
            ing('Domates salçası', '1 yemek kaşığı', 20, 'g', SALCA),
            ing('Tuz', '1 çay kaşığı', 3, 'g', TUZ, True),
            ing('Kuru nane', '1 tatlı kaşığı', 2, 'g', ('nane', None), True),
        ],
    },
    {
        'slug': 'tavuk-corbasi', 'name': 'Şehriyeli Tavuk Çorbası', 'course': 'Çorba', 'course_type': 'corba',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 10, 'cook_minutes': 35, 'icon': '🐔',
        'description': 'Didiklenmiş tavuk, havuç ve arpa şehriyeyle limonlu çorba.',
        'allergens': 'gluten,sut', 'diets': '', 'nutrition': (190, 16, 18, 6), 'popularity': 74,
        'steps': [
            'Tavuğu 6 su bardağı suda 25 dakika haşlayın, çıkarıp didikleyin.',
            'Tereyağında rendelenmiş havucu çevirin, şehriyeyi ekleyip 1 dakika kavurun.',
            'Tavuk suyunu ve didiklenmiş tavuğu ekleyip şehriye pişene kadar 10 dakika kaynatın.',
            'Tuz ve limon suyuyla servis edin.',
        ],
        'ingredients': [
            ing('Tavuk göğsü', '250 g', 250, 'g', ('tavuk gogus|pilic gogus', 'fume,jambon,salam,doner,pane,haslanmis')),
            ing('Arpa şehriye', '1/2 su bardağı', 80, 'g', ('arpa sehriye|sehriye', None)),
            ing('Havuç', '1 adet', 80, 'g', ('havuc', 'suyu,bebek')),
            ing('Tereyağı', '1 yemek kaşığı', 20, 'g', TEREYAGI),
            ing('Limon', '1/2 adet', 50, 'g', LIMON),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    # --- Kahvaltı ---
    {
        'slug': 'sucuklu-yumurta', 'name': 'Sucuklu Yumurta', 'course': 'Kahvaltılık', 'course_type': 'ana',
        'meal_slots': 'kahvalti', 'servings': 2, 'prep_minutes': 2, 'cook_minutes': 8, 'icon': '🍳',
        'description': 'Tereyağında çevrilen sucuğun üzerine kırılan yumurtalarla sahan.',
        'allergens': 'yumurta,sut', 'diets': '', 'nutrition': (380, 22, 2, 31), 'popularity': 88,
        'steps': [
            'Sucuğu ince dilimleyin.',
            'Sahanda tereyağını eritip sucukları iki yüzü hafif kızarana kadar çevirin.',
            'Yumurtaları üzerine kırın, beyazı pişene kadar kısık ateşte pişirin.',
        ],
        'ingredients': [
            ing('Sucuk', '100 g', 100, 'g', ('sucuk', 'tost,pizza,cips')),
            ing('Yumurta', '4 adet', 4, 'adet', YUMURTA),
            ing('Tereyağı', '1 tatlı kaşığı', 10, 'g', TEREYAGI),
        ],
    },
    {
        'slug': 'kahvalti-tabagi', 'name': 'Serpme Kahvaltı Tabağı', 'course': 'Kahvaltılık', 'course_type': 'ana',
        'meal_slots': 'kahvalti', 'servings': 2, 'prep_minutes': 10, 'cook_minutes': 0, 'icon': '🧀',
        'description': 'Beyaz peynir, zeytin, domates, salatalık, bal ve tereyağıyla klasik Türk kahvaltısı.',
        'allergens': 'sut,gluten', 'diets': 'vejetaryen', 'nutrition': (520, 20, 50, 27), 'popularity': 85,
        'steps': [
            'Peyniri dilimleyin, domates ve salatalığı doğrayın.',
            'Zeytin, bal ve tereyağıyla tabağa dizin; taze ekmekle servis edin.',
        ],
        'ingredients': [
            ing('Beyaz peynir', '100 g', 100, 'g', ('beyaz peynir', 'light,yarim')),
            ing('Siyah zeytin', '1 avuç', 80, 'g', ('siyah zeytin|zeytin', 'ezmesi')),
            ing('Domates', '1 adet', 200, 'g', DOMATES),
            ing('Salatalık', '1 adet', 150, 'g', ('salatalik', 'tursu,kornison')),
            ing('Bal', '2 yemek kaşığı', 30, 'g', ('bal', 'balik,kabak,kabag,cekirdek')),
            ing('Tereyağı', '1 yemek kaşığı', 20, 'g', TEREYAGI),
            ing('Ekmek', '1/2 adet', 1, 'adet', ('ekmek', 'galeta,kirintisi,kadayif')),
        ],
    },
    {
        'slug': 'cay', 'name': 'Demlik Çay', 'course': 'İçecek', 'course_type': 'icecek',
        'meal_slots': 'kahvalti', 'servings': 1, 'prep_minutes': 2, 'cook_minutes': 15, 'icon': '🫖',
        'description': 'Kahvaltının olmazsa olmazı demlik çay.',
        'allergens': '', 'diets': 'vejetaryen,vegan', 'nutrition': (2, 0, 0, 0), 'popularity': 98,
        'steps': ['Demliğe çayı koyup kaynar suyu ekleyin, kısık ateşte 15 dakika demleyin.'],
        'ingredients': [
            ing('Siyah çay', '2 çay kaşığı', 5, 'g', ('cay', 'bitki,yesil,ada,ihlamur,soguk,kupa,bardak,demlik,makinesi,kasigi')),
        ],
    },
    # --- Salatalar ---
    {
        'slug': 'kisir', 'name': 'Kısır', 'course': 'Salata', 'course_type': 'salata',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 25, 'cook_minutes': 0, 'icon': '🥗',
        'description': 'İnce bulgurun salça, nar ekşisi ve bol yeşillikle buluştuğu salata.',
        'allergens': 'gluten', 'diets': 'vejetaryen,vegan', 'nutrition': (280, 6, 42, 11), 'popularity': 87,
        'steps': [
            'Bulguru 1 su bardağı sıcak suyla ıslatıp kapağını kapatın, 15 dakika şişirin.',
            'Salçayı, zeytinyağını ve tuzu ekleyip iyice yoğurun.',
            'İnce doğranmış domates, yeşil soğan ve maydanozu ekleyin.',
            'Nar ekşisi ve limon suyuyla tatlandırıp servis edin.',
        ],
        'ingredients': [
            ing('İnce bulgur', '1 su bardağı', 200, 'g', ('koftelik bulgur|ince bulgur', None)),
            ing('Domates salçası', '2 yemek kaşığı', 30, 'g', SALCA),
            ing('Domates', '1 adet', 200, 'g', DOMATES),
            ing('Yeşil soğan', '1 demet', 1, 'adet', ('yesil sogan|taze sogan', None)),
            ing('Maydanoz', '1 demet', 1, 'adet', MAYDANOZ),
            ing('Nar ekşisi', '2 yemek kaşığı', 30, 'ml', ('nar eksisi', None)),
            ing('Zeytinyağı', '4 yemek kaşığı', 60, 'ml', ZEYTINYAGI),
            ing('Limon', '1/2 adet', 50, 'g', LIMON),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    {
        'slug': 'piyaz', 'name': 'Piyaz', 'course': 'Salata', 'course_type': 'salata',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 15, 'cook_minutes': 60, 'icon': '🫘',
        'description': 'Haşlanmış kuru fasulye, soğan ve maydanozla limonlu salata; köftenin yanına.',
        'allergens': '', 'diets': 'vejetaryen,vegan', 'nutrition': (250, 11, 30, 10), 'popularity': 78,
        'steps': [
            'Kuru fasulyeyi bir gece ıslatıp yumuşayana kadar haşlayın, soğutun.',
            'Soğanı piyazlık doğrayıp tuzla ovun.',
            'Fasulye, soğan, doğranmış domates ve maydanozu karıştırın.',
            'Zeytinyağı, limon suyu ve tuzla soslayın.',
        ],
        'ingredients': [
            ing('Kuru fasulye', '1 su bardağı', 250, 'g', ('kuru fasulye', 'konserve,haslanmis')),
            ing('Kuru soğan', '1 adet', 100, 'g', SOGAN),
            ing('Domates', '1 adet', 150, 'g', DOMATES),
            ing('Maydanoz', '1 demet', 1, 'adet', MAYDANOZ),
            ing('Zeytinyağı', '3 yemek kaşığı', 50, 'ml', ZEYTINYAGI),
            ing('Limon', '1/2 adet', 50, 'g', LIMON),
            ing('Tuz', '1 tatlı kaşığı', 5, 'g', TUZ, True),
        ],
    },
    # --- Tatlılar ---
    {
        'slug': 'revani', 'name': 'Revani', 'course': 'Tatlı', 'course_type': 'tatli',
        'meal_slots': R, 'servings': 8, 'prep_minutes': 15, 'cook_minutes': 35, 'icon': '🍰',
        'description': 'İrmikli, yoğurtlu kekin limonlu şerbetle buluştuğu şerbetli tatlı.',
        'allergens': 'gluten,sut,yumurta', 'diets': 'vejetaryen', 'nutrition': (380, 6, 68, 10), 'popularity': 80,
        'steps': [
            '400 g şeker, 3 su bardağı su ve limon dilimiyle şerbeti kaynatıp soğutun.',
            'Yumurta ve 150 g şekeri çırpın; yoğurt ve yağı ekleyin.',
            'İrmik, un ve kabartma tozunu ekleyip karıştırın.',
            'Yağlanmış tepsiye döküp 180°C fırında 30-35 dakika pişirin.',
            'Sıcak revaniye soğuk şerbeti dökün, şerbeti çekince dilimleyin.',
        ],
        'ingredients': [
            ing('İrmik', '1 su bardağı', 200, 'g', ('irmik', 'tatlisi,helva')),
            ing('Buğday unu', '1 su bardağı', 120, 'g', UN),
            ing('Yoğurt', '1 su bardağı', 200, 'g', YOGURT),
            ing('Yumurta', '3 adet', 3, 'adet', YUMURTA),
            ing('Toz şeker', '3,5 su bardağı', 550, 'g', SEKER),
            ing('Ayçiçek yağı', '1/2 su bardağı', 80, 'ml', AYCICEK),
            ing('Limon', '1/2 adet', 50, 'g', LIMON),
            ing('Kabartma tozu', '1 paket', 10, 'g', ('kabartma tozu', None), True),
        ],
    },
    {
        'slug': 'muhallebi', 'name': 'Muhallebi', 'course': 'Tatlı', 'course_type': 'tatli',
        'meal_slots': R, 'servings': 4, 'prep_minutes': 5, 'cook_minutes': 20, 'icon': '🍮',
        'description': 'Pirinç unu ve mısır nişastasıyla, glutensiz sütlü tatlı.',
        'allergens': 'sut', 'diets': 'vejetaryen', 'nutrition': (270, 9, 46, 7), 'popularity': 76,
        'steps': [
            'Süt, şeker, pirinç unu ve nişastayı soğukken tencerede çırpın.',
            'Orta ateşte sürekli karıştırarak koyulaşana kadar pişirin.',
            'Kaselere paylaştırıp soğutun, tarçınla servis edin.',
        ],
        'ingredients': [
            ing('Süt', '1 litre', 1000, 'ml', SUT),
            ing('Toz şeker', '1 su bardağı', 150, 'g', SEKER),
            ing('Pirinç unu', '3 yemek kaşığı', 40, 'g', ('pirinc unu', None)),
            ing('Mısır nişastası', '2 yemek kaşığı', 30, 'g', ('misir nisastasi|nisasta', 'bugday')),
            ing('Tarçın', 'servis için', 2, 'g', ('tarcin', None), True),
        ],
    },
    {
        'slug': 'kabak-tatlisi', 'name': 'Kabak Tatlısı', 'course': 'Tatlı', 'course_type': 'tatli',
        'meal_slots': R, 'servings': 6, 'prep_minutes': 15, 'cook_minutes': 45, 'icon': '🎃',
        'description': 'Şekerle kendi suyunda pişen bal kabağı, cevizle; sonbaharın tatlısı.',
        'allergens': 'kuruyemis', 'diets': 'vejetaryen,vegan', 'nutrition': (260, 3, 52, 6), 'popularity': 74,
        'steps': [
            'Kabağı soyup iri dilimleyin, tencereye dizip üzerine şekeri serpin.',
            'Bir gece bekletip suyunu salmasını sağlayın.',
            'Kapağı kapalı, kısık ateşte kabaklar yumuşayana kadar 40-45 dakika pişirin.',
            'Soğuyunca dövülmüş cevizle servis edin.',
        ],
        'ingredients': [
            ing('Bal kabağı', '1 kg', 1000, 'g', ('bal kabagi|balkabagi', 'cekirdek,tatlisi')),
            ing('Toz şeker', '1,5 su bardağı', 250, 'g', SEKER),
            ing('Ceviz içi', '1 avuç', 50, 'g', ('ceviz ici|ceviz', 'yagi,kabuklu')),
        ],
    },
]

INGREDIENT_COLS = ('recipe_id', 'position', 'name', 'amount_text', 'quantity', 'unit', 'search_term', 'exclude_terms', 'is_pantry')


def upgrade() -> None:
    op.add_column('recipes', sa.Column('allergens', sa.String(length=128), server_default='', nullable=False))
    op.add_column('recipes', sa.Column('diets', sa.String(length=64), server_default='', nullable=False))
    for col in ('kcal', 'protein_g', 'carbs_g', 'fat_g'):
        op.add_column('recipes', sa.Column(col, sa.Integer(), nullable=True))
    op.add_column('recipes', sa.Column('popularity', sa.Integer(), server_default='0', nullable=False))
    op.add_column('recipes', sa.Column('like_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('meal_plans', sa.Column('diets', sa.String(length=64), server_default='', nullable=False))
    op.add_column('meal_plans', sa.Column('avoid_allergens', sa.String(length=128), server_default='', nullable=False))
    op.create_table(
        'recipe_likes',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_recipe_likes_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], name=op.f('fk_recipe_likes_recipe_id_recipes'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'recipe_id', name=op.f('pk_recipe_likes')),
    )
    op.create_index(op.f('ix_recipe_likes_recipe_id'), 'recipe_likes', ['recipe_id'], unique=False)

    conn = op.get_bind()
    meta_sql = sa.text(
        'UPDATE recipes SET allergens = :a, diets = :d, kcal = :k, protein_g = :p, carbs_g = :c, fat_g = :f, '
        'popularity = :pop WHERE slug = :s'
    )
    for slug, (allergens, diets, (k, p, c, f), pop) in EXISTING.items():
        conn.execute(meta_sql, {'a': allergens, 'd': diets, 'k': k, 'p': p, 'c': c, 'f': f, 'pop': pop, 's': slug})
    for slug, pairs in DRINK_PAIRS.items():
        conn.execute(sa.text('UPDATE recipes SET pairs_with = :p WHERE slug = :s'), {'p': pairs or None, 's': slug})
    # "salgam" araması "Şalgam Suyu"nu "suyu" yüzünden elemesin; "bal" "Bal Kabağı"nı bulmasın
    conn.execute(sa.text("UPDATE recipe_ingredients SET search_term = 'salgam suyu|salgam' WHERE search_term = 'salgam'"))
    conn.execute(sa.text(
        "UPDATE recipe_ingredients SET exclude_terms = 'balik,kabak,kabag,cekirdek' WHERE search_term = 'bal'"
    ))
    # Yan yemek ana yemekten sonra gelir: sıralama öğün x 10 + tür (çorba 0, ana 1, yan 2, salata 3...)
    conn.execute(sa.text(
        "UPDATE meal_plan_entries SET slot_order = (CASE slot WHEN 'kahvalti' THEN 0 WHEN 'ogle' THEN 1 "
        "WHEN 'ara' THEN 2 ELSE 3 END) * 10 + (CASE course WHEN 'corba' THEN 0 WHEN 'ana' THEN 1 "
        "WHEN 'yan' THEN 2 WHEN 'salata' THEN 3 WHEN 'tatli' THEN 4 WHEN 'icecek' THEN 5 ELSE 6 END)"
    ))

    recipes = sa.table('recipes', *(sa.column(c) for c in (
        'id', 'cuisine_id', 'slug', 'name', 'course', 'course_type', 'pairs_with', 'meal_slots', 'servings',
        'prep_minutes', 'cook_minutes', 'description', 'steps', 'icon', 'is_active', 'allergens', 'diets',
        'kcal', 'protein_g', 'carbs_g', 'fat_g', 'popularity',
    )))
    ingredients = sa.table('recipe_ingredients', *(sa.column(c) for c in INGREDIENT_COLS))
    anadolu_id = conn.execute(sa.text("SELECT id FROM cuisines WHERE slug = 'anadolu'")).scalar_one()
    for recipe in RECIPES:
        k, p, c, f = recipe['nutrition']
        recipe_id = conn.execute(
            recipes.insert().returning(recipes.c.id),
            {
                'cuisine_id': anadolu_id,
                **{key: recipe[key] for key in (
                    'slug', 'name', 'course', 'course_type', 'meal_slots', 'servings', 'prep_minutes', 'cook_minutes',
                    'description', 'icon', 'allergens', 'diets', 'popularity',
                )},
                'pairs_with': recipe.get('pairs_with'),
                'steps': '\n'.join(recipe['steps']),
                'is_active': True,
                'kcal': k, 'protein_g': p, 'carbs_g': c, 'fat_g': f,
            },
        ).scalar_one()
        conn.execute(ingredients.insert(), [
            dict(zip(INGREDIENT_COLS, (recipe_id, i, *row)))
            for i, row in enumerate(recipe['ingredients'])
        ])


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [r['slug'] for r in RECIPES]
    conn.execute(sa.text(
        'DELETE FROM meal_plan_entries WHERE recipe_id IN (SELECT id FROM recipes WHERE slug = ANY(:s))'
    ), {'s': slugs})
    conn.execute(sa.text('DELETE FROM recipes WHERE slug = ANY(:s)'), {'s': slugs})
    conn.execute(sa.text("UPDATE recipe_ingredients SET search_term = 'salgam' WHERE search_term = 'salgam suyu|salgam'"))
    conn.execute(sa.text("UPDATE recipe_ingredients SET exclude_terms = 'balik,kabak' WHERE search_term = 'bal'"))
    conn.execute(sa.text(
        "UPDATE meal_plan_entries SET slot_order = (CASE slot WHEN 'kahvalti' THEN 0 WHEN 'ogle' THEN 1 "
        "WHEN 'ara' THEN 2 ELSE 3 END) * 10 + (CASE course WHEN 'corba' THEN 0 WHEN 'ana' THEN 1 "
        "WHEN 'salata' THEN 2 WHEN 'tatli' THEN 3 WHEN 'icecek' THEN 4 ELSE 5 END)"
    ))
    op.drop_index(op.f('ix_recipe_likes_recipe_id'), table_name='recipe_likes')
    op.drop_table('recipe_likes')
    op.drop_column('meal_plans', 'avoid_allergens')
    op.drop_column('meal_plans', 'diets')
    for col in ('like_count', 'popularity', 'fat_g', 'carbs_g', 'protein_g', 'kcal', 'diets', 'allergens'):
        op.drop_column('recipes', col)
