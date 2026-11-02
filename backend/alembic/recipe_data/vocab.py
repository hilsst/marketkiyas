"""Faz 1 tarif kataloğu için malzeme sözlüğü ve tarif oluşturucu.

Her malzemenin arama ifadesi, elenecek kelimeleri, izin verilen kategorileri, alerjeni, türü ve 100 g/ml
başına besin değeri burada bir kez tanımlanır. Tarifler yalnızca "anahtar miktar" yazar; alerjen, diyet
(vejetaryen/vegan) ve kişi başı besin değeri buradan hesaplanır, böylece 200+ tarifte elle tutarsızlık olmaz.

Bu modül bir göç (migration) verisidir: tarifler yayımlandıktan sonra değiştirilmemelidir; yeni tarif için
yeni bir göç yazılır.
"""

CATS = {
    "S": "meyve-sebze", "T": "temel-gida", "M": "sut-kahvaltilik", "E": "et-tavuk-balik",
    "I": "icecek", "A": "atistirmalik", "F": "firin", "D": "dondurulmus",
}
ALLERGEN_ORDER = ["gluten", "sut", "yumurta", "kuruyemis", "susam", "soya", "balik", "kereviz", "hardal"]

# anahtar;görünen ad;arama ifadesi;elenecek kelimeler;kategoriler;alerjen;tür;kcal,protein,karb,yağ;birim;P
# tür: plant / meat / fish / dairy / egg / honey.  birim: g (varsayılan), ml, adet:<gram>.  P = evde var sayılır
_VOCAB = """
domates;Domates;domates;salca,sos,ketcap,kurutulmus,konserve,rendesi,suyu,cherry,kokteyl;S;;plant;18,1,4,0
sogan;Kuru soğan;kuru sogan;toz,granul;S;;plant;40,1,9,0
yesilsogan;Taze soğan;yesil sogan|taze sogan;;S;;plant;32,2,7,0
sarimsak;Sarımsak;sarimsak;toz,granul;S;;plant;149,6,33,1
sivribiber;Sivri biber;sivri biber;tursu,toz;S;;plant;27,1,6,0
kapya;Kapya biber;kapya biber|kirmizi biber|renkli biber;pul,toz,salca,tursu,kozlenmis,konserve,sos;S;;plant;31,1,6,0
dolmabiber;Dolmalık biber;dolmalik biber|dolma biber;tursu,toz,salca,konserve;S;;plant;27,1,6,0
havuc;Havuç;havuc;suyu,rendesi,tursu;S;;plant;41,1,10,0
kabak;Kabak;kabak;bal,cekirde,tatlisi;S;;plant;17,1,3,0
balkabagi;Bal kabağı;bal kabagi|balkabagi;cekirde,tatlisi;S;;plant;45,1,11,0
patates;Patates;patates;cips,kizartma,dondurulmus,pure;S;;plant;77,2,17,0
tatlipatates;Tatlı patates;tatli patates;;S;;plant;86,2,20,0
patlican;Patlıcan;patlican;salata,kozlenmis,konserve,tursu,kuru,kizartma;S;;plant;25,1,6,0
mantar;Mantar;mantar;konserve,tursu,sos,corba;S;;plant;22,3,3,0
ispanak;Ispanak;ispanak;dondurulmus,konserve;S;;plant;23,3,4,0
marul;Marul;marul|kivircik|aysberg;tohum;S;;plant;15,1,3,0
roka;Roka;roka;tohum;S;;plant;25,3,4,1
salatalik;Salatalık;salatalik;tursu,kornison;S;;plant;15,1,4,0
lahana;Beyaz lahana;beyaz lahana|lahana;tursu,kirmizi,bruksel;S;;plant;25,1,6,0
kirmizilahana;Kırmızı lahana;kirmizi lahana;tursu;S;;plant;31,1,7,0
karnabahar;Karnabahar;karnabahar;dondurulmus,tursu;S;;plant;25,2,5,0
brokoli;Brokoli;brokoli;;S,D;;plant;34,3,7,0
bezelye;Bezelye;bezelye;konserve;S,D,T;;plant;81,5,14,0
tazefasulye;Taze fasulye;taze fasulye|ayse fasulye;konserve,dondurulmus;S;;plant;31,2,7,0
pirasa;Pırasa;pirasa;;S;;plant;31,2,7,0
kereviz;Kereviz;kereviz;tohum;S;kereviz;plant;42,1,9,0
bamya;Bamya;bamya;konserve;S,D;;plant;33,2,7,0
limon;Limon;limon;sosu,kolonya,tuzu,suyu,aromali;S;;plant;29,1,9,0
portakal;Portakal;portakal;suyu,aromali;S;;plant;47,1,12,0
elma;Elma;elma;suyu,sirkesi,kurusu,cips,kek,turta,aromali;S;;plant;52,0,14,0
muz;Muz;muz;cips,kurusu,aromali,sut;S;;plant;89,1,23,0
ayva;Ayva;ayva;recel,tatlisi;S;;plant;57,0,15,0
visne;Vişne;visne;suyu,recel,komposto,sekerleme;S,D;;plant;50,1,12,0
cilek;Çilek;cilek;recel,aromali,sut,kurusu;S,D;;plant;32,1,8,0
avokado;Avokado;avokado;;S;;plant;160,2,9,15
maydanoz;Maydanoz;maydanoz;kurusu,kuru;S;;plant;36,3,6,1
dereotu;Dereotu;dereotu|dere otu;kurusu,kuru;S;;plant;43,3,7,1
feslegen;Fesleğen;feslegen;sos,pesto;S,T;;plant;23,3,3,1
zencefil;Zencefil;zencefil;cay,sakiz,gazoz,sekerleme;S,T;;plant;80,2,18,1
nane;Nane;nane;sekeri,sakiz,cay;S,T;;plant;44,3,8,1;P
pancar;Pancar;pancar;seker,tursu;S;;plant;43,2,10,0
asmayapragi;Asma yaprağı;asma yapragi|salamura yaprak;;T,S;;plant;93,5,17,2
misir;Mısır;misir konservesi|konserve misir|tatli misir|misir;cips,patlak,patlamis,unu,nisasta,gevrek,yag,irmik;T,S;;plant;86,3,19,1
kayisi;Kuru kayısı;kuru kayisi;;A,T;;plant;241,3,63,1
hurma;Hurma;hurma;trabzon;A,T,S;;plant;282,2,75,0
uzum;Kuru üzüm;kuru uzum|sultaniye;;A,T;;plant;299,3,79,0
incir;Kuru incir;kuru incir;;A,T;;plant;249,3,64,1
ceviz;Ceviz içi;ceviz ici|ceviz;yagi,kabuklu;A,T,S;kuruyemis;plant;654,15,14,65
findik;Fındık;findik;ezmesi,cikolata,kakaolu,sutlu,kremasi;A,T;kuruyemis;plant;628,15,17,61
badem;Badem;badem;ezmesi,sutu,yagi,cikolata;A,T;kuruyemis;plant;579,21,22,50
fistik;Antep fıstığı;antep fistigi|fistik ici;ezmesi,cikolata;A,T;kuruyemis;plant;560,20,28,45
yerfistigi;Yer fıstığı;yer fistigi|fistik;ezmesi,antep,cikolata,bar,sos;A,T;kuruyemis;plant;567,26,16,49
nohut;Nohut;nohut;konserve,haslanmis,leblebi,unu;T;;plant;364,19,61,6
kirmizimercimek;Kırmızı mercimek;kirmizi mercimek;;T;;plant;352,24,60,1
yesilmercimek;Yeşil mercimek;yesil mercimek;;T;;plant;352,24,60,1
kurufasulye;Kuru fasulye;kuru fasulye;konserve,haslanmis;T;;plant;333,23,60,1
barbunya;Barbunya;kirmizi fasulye|barbunya;tursu,pilaki;T,S;;plant;333,23,60,1
un;Buğday unu;bugday unu|un;kurabiye,manti,makarna,helva,biskuvi,galeta,misir,pirinc,nohut,cavdar,patlagi,elegi;T;gluten;plant;364,10,76,1
misirunu;Mısır unu;misir unu;;T;;plant;361,7,77,4
irmik;İrmik;irmik;tatlisi,helva;T;gluten;plant;360,13,73,1
nisasta;Mısır nişastası;misir nisastasi|nisasta;;T;;plant;381,0,91,0
pirinc;Pirinç;pirinc;unu,patlagi,sirkesi;T;;plant;360,7,80,1
bulgur;Pilavlık bulgur;pilavlik bulgur|bulgur;koftelik,kofte,ince;T;gluten;plant;342,12,76,1
koftelikbulgur;Köftelik bulgur;koftelik bulgur|ince bulgur;;T;gluten;plant;342,12,76,1
makarna;Makarna;makarna|spagetti|penne;;T;gluten;plant;371,13,75,2
sehriye;Arpa şehriye;arpa sehriye|sehriye;tel;T;gluten;plant;360,12,74,2
telsehriye;Tel şehriye;tel sehriye|sehriye;;T;gluten;plant;360,12,74,2
eriste;Erişte;eriste;;T;gluten;plant;360,12,74,2
noodle;Noodle;noodle;cup,bardak;T;gluten;plant;350,10,68,5
yulaf;Yulaf ezmesi;yulaf ezmesi|yulaf;;T;gluten;plant;389,17,66,7
gullac;Güllaç;gullac;;T,F;;plant;330,1,80,0
seker;Toz şeker;toz seker;pudra,esmer,kup;T;;plant;400,0,100,0;P
pudraseker;Pudra şeker;pudra seker;;T;;plant;400,0,100,0;P
bal;Bal;bal;balik,kabak,kabag,cekirdek;M,T;;honey;304,0,82,0
pekmez;Üzüm pekmezi;uzum pekmezi|pekmez;;T;;plant;292,1,72,0
tahin;Tahin;tahin;helva;T;susam;plant;595,17,21,54
susam;Susam;susam;yagi,tahin,simit,kraker,bar,helva;T,A;susam;plant;573,18,23,50
kakao;Kakao;kakao;kremasi,sutlu,icecek,gofret,findik;T;;plant;228,20,58,14
hindistancevizi;Hindistan cevizi;hindistan cevizi;sutu,yagi,sekerleme;T;;plant;354,3,15,33
hindistancevizisutu;Hindistan cevizi sütü;hindistan cevizi sutu;;T,M,I;;plant;197,2,3,21;ml
salca;Domates salçası;domates salcasi;;T;;plant;80,4,15,1
biberSalcasi;Biber salçası;biber salcasi;;T;;plant;80,4,15,1
sirke;Sirke;elma sirkesi|uzum sirkesi|sirke;;T;;plant;20,0,1,0;ml
nareksisi;Nar ekşisi;nar eksisi;;T;;plant;60,0,15,0;ml
soyasosu;Soya sosu;soya sosu;;T;soya;plant;60,8,6,0;ml
kori;Köri;kori|curry;sos;T;;plant;325,14,58,14;P
zeytinyagi;Zeytinyağı;zeytinyagi;;T;;plant;884,0,0,100;ml
aycicek;Ayçiçek yağı;aycicek yagi;;T;;plant;884,0,0,100;ml
tuz;Tuz;tuz;tuzsuz,tuzlu;T;;plant;0,0,0,0;P
karabiber;Karabiber;karabiber;;T;;plant;250,10,64,3;P
pulbiber;Pul biber;pul biber;;T;;plant;282,12,50,14;P
kimyon;Kimyon;kimyon;;T;;plant;375,18,44,22;P
kekik;Kekik;kekik;yagi,sabun,cay;T;;plant;276,9,64,7;P
tarcin;Tarçın;tarcin;sakiz,cay,kek;T;;plant;247,4,81,1;P
sumak;Sumak;sumak;;T;;plant;250,5,60,5;P
zerdecal;Zerdeçal;zerdecal;;T;;plant;312,10,67,3;P
kabartma;Kabartma tozu;kabartma tozu;;T;;plant;53,0,28,0;P
vanilya;Vanilya;vanilya|vanilin;;T;;plant;288,0,13,0;P
maya;Maya;instant maya|kuru maya|maya;kabartma;T;;plant;325,40,41,8;P
turkkahvesi;Türk kahvesi;turk kahvesi;sutlu,3u1,2si1,kapsul;I,T;;plant;2,0,0,0
cay;Çay;cay;bitki,yesil,ada,ihlamur,soguk,kupa,bardak,demlik,makinesi,kasigi;I,T;;plant;1,0,0,0
yesilcay;Yeşil çay;yesil cay;aromali,soguk,icecek;I,T;;plant;1,0,0,0
ihlamur;Ihlamur;ihlamur;aromali,soguk,seker;I,T;;plant;1,0,0,0
sodasu;Soda;maden suyu|soda;aromali,meyveli;I;;plant;0,0,0,0;ml
sut;Süt;sut;tozu,cikolatali,kakaolu,cilekli,muzlu,laktozsuz,keci,badem,soya,hindistan;M;sut;dairy;61,3,5,3;ml
yogurt;Yoğurt;yogurt;icecek,meyveli,suzme,cilekli,kakaolu;M;sut;dairy;61,3,5,3
ayran;Ayran;ayran;;I,M;sut;dairy;37,2,3,2;ml
beyazpeynir;Beyaz peynir;beyaz peynir;light,yarim;M;sut;dairy;264,14,1,22
kasar;Kaşar peyniri;kasar peyniri|kasar;tost,cubuk;M;sut;dairy;330,24,2,25
lor;Lor peyniri;lor peyniri|lor;;M;sut;dairy;98,11,3,4
krema;Süt kreması;sivi krema|krema;sanitize,sekerli,kakaolu,kremasi,cikolata,kahve,sac,yuz,el;M;sut;dairy;292,2,3,30;ml
kaymak;Kaymak;kaymak;;M;sut;dairy;350,2,3,38
tereyagi;Tereyağı;tereyagi;;M;sut;dairy;717,1,0,81
parmesan;Parmesan;parmesan|rende kasar;;M;sut;dairy;400,36,4,28
mozzarella;Mozzarella;mozzarella|mozarella;;M;sut;dairy;280,28,3,17
yumurta;Yumurta;yumurta;cikolata,makarna,eriste;M;yumurta;egg;143,13,1,10;adet:55
kiyma;Dana kıyma;dana kiyma|kiyma;tavuk,hindi,kuzu;E;;meat;250,17,0,20
kusbasi;Dana kuşbaşı;dana kusbasi|kusbasi;tavuk,hindi,kuzu;E;;meat;190,26,0,9
kuzukusbasi;Kuzu kuşbaşı;kuzu kusbasi;;E;;meat;240,25,0,16
kuzuincik;Kuzu incik;kuzu incik;;E;;meat;250,24,0,17
tavukgogus;Tavuk göğüs;tavuk gogus|pilic gogus|pilic bonfile|tavuk bonfile|pilic fileto;fume,jambon,salam,doner,pane,haslanmis;E;;meat;165,31,0,4
tavukbut;Tavuk but;tavuk but|pilic but;pane,haslanmis,fume;E;;meat;209,26,0,11
sucuk;Sucuk;sucuk;tost,pizza,cips;E,M;;meat;450,20,3,40
pastirma;Pastırma;pastirma;;E,M;;meat;240,30,1,13
somon;Somon;somon;fume,konserve;E,D;balik;fish;208,20,0,13
levrek;Levrek;levrek;;E,D;balik;fish;97,18,0,2
cipura;Çipura;cipura;;E,D;balik;fish;100,19,0,2
hamsi;Hamsi;hamsi;konserve;E,D;balik;fish;131,20,0,5
tonbaligi;Ton balığı;ton baligi;;T,E;balik;fish;116,26,0,1
yufka;Yufka;yufka;kadayif;F,T,M;gluten;plant;300,9,60,2
pide;Pide ekmeği;pide;kadayif;F;gluten;plant;270,9,53,2
ekmek;Ekmek;ekmek;galeta,kirintisi,kadayif;F;gluten;plant;265,9,49,3
galetaunu;Galeta unu;galeta unu;;T,F;gluten;plant;395,13,72,5
tortilla;Tortilla;tortilla|lavas;cips;F,T;gluten;plant;300,8,50,7
zeytin;Siyah zeytin;siyah zeytin|zeytin;ezmesi;M,T;;plant;115,1,6,11
""".strip()

VOCAB: dict[str, dict] = {}
for _line in _VOCAB.splitlines():
    _f = _line.split(";")
    _f += [""] * (10 - len(_f))
    _key, _name, _term, _excl, _cats, _allergen, _kind, _nut, _unit, _pantry = _f[:10]
    _k, _p, _c, _fat = (float(x) for x in _nut.split(","))
    if _unit == "P":
        _unit, _pantry = "", "P"
    _unit, _, _piece = (_unit or "g").partition(":")
    VOCAB[_key] = {
        "name": _name, "term": _term, "excl": _excl or None,
        "cats": ",".join(CATS[c] for c in _cats.split(",")), "allergens": [a for a in _allergen.split(",") if a],
        "kind": _kind, "nut": (_k, _p, _c, _fat), "unit": _unit, "piece": float(_piece) if _piece else None,
        "pantry": _pantry == "P",
    }

COURSES = {
    "a": ("Ana yemek", "ana", "🍲", "ogle,aksam"), "k": ("Kahvaltılık", "ana", "🍳", "kahvalti"),
    "c": ("Çorba", "corba", "🥣", "ogle,aksam"), "s": ("Salata", "salata", "🥗", "ogle,aksam"),
    "t": ("Tatlı", "tatli", "🍮", "ogle,aksam"), "y": ("Yanında", "yan", "🍚", "ogle,aksam"),
    "i": ("İçecek", "icecek", "🥤", "ogle,aksam"), "r": ("Ara öğün", "ara", "🥜", "ara"),
}


def recipe(slug, name, typ, servings, prep, cook, description, steps, ingredients, popularity=70, *,
           cuisine, tags="", groups="", pair="", icon=None, slots=None):
    """steps: ' | ' ile ayrılmış adımlar. ingredients: 'anahtar miktar[=ölçü metni], ...' (miktar sözlükteki birimde).
    groups: bu ana yemeğin yanına uyan yan yemek / içecek grupları (pilav, bulgur, ayran...).
    pair: bu yan yemeğin uyduğu grup (yan yemeklerde zorunlu)."""
    course, course_type, default_icon, default_slots = COURSES[typ]
    rows, allergens, kinds = [], set(), set()
    kcal = protein = carbs = fat = 0.0
    for token in (t.strip() for t in ingredients.split(",") if t.strip()):
        head, _, text = token.partition("=")
        key, qty = head.split()
        v = VOCAB[key]
        absorbed = 1.0
        if qty.endswith("~"):  # kızartma yağı: tamamı alınır ama yemeğe yalnız ~%15'i geçer
            qty, absorbed = qty[:-1], 0.15
        qty = float(qty)
        grams = (qty * v["piece"] if v["unit"] == "adet" else qty) * absorbed
        k, p, c, f = v["nut"]
        kcal += k * grams / 100; protein += p * grams / 100; carbs += c * grams / 100; fat += f * grams / 100
        allergens.update(v["allergens"]); kinds.add(v["kind"])
        number = int(qty) if qty == int(qty) else qty
        unit_text = {"g": "g", "ml": "ml", "adet": "adet"}[v["unit"]]
        rows.append((
            v["name"], text or f"{number} {unit_text}", qty, v["unit"], v["term"], v["excl"], v["cats"], v["pantry"],
        ))
    diets = []
    if not kinds & {"meat", "fish"}:
        diets.append("vejetaryen")
        if kinds <= {"plant"}:
            diets.append("vegan")
    return {
        "cuisine": cuisine, "slug": slug, "name": name, "course": course, "course_type": course_type,
        "icon": icon or default_icon, "servings": servings, "prep": prep, "cook": cook, "description": description,
        "allergens": ",".join(a for a in ALLERGEN_ORDER if a in allergens), "diets": ",".join(diets),
        "nutrition": tuple(round(x / servings) for x in (kcal, protein, carbs, fat)), "popularity": popularity,
        "steps": [s.strip() for s in steps.split("|")], "ingredients": rows, "meal_slots": slots or default_slots,
        "tags": tags, "groups": [g for g in groups.split(",") if g], "pair": pair,
    }
