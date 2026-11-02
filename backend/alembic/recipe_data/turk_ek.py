"""Türk Mutfağı: eklenen son tarifler (göç 0020 verisi)."""

from .vocab import recipe as _r


def r(*a, **kw):
    return _r(*a, cuisine="anadolu", **kw)


EK = [
    r("tavuklu-pilav", "Tavuklu Pilav", "a", 4, 10, 35,
      "Didiklenmiş tavuklu tereyağlı pilav.",
      "Tavuğu haşlayıp didin, suyunu ayırın. | Pirinci tereyağında kavurun. | Tavuk suyu ve tavukla pişirip demleyin.",
      "tavukgogus 400, pirinc 300, tereyagi 30, tuz 5, karabiber 2", 82, groups="ayran,cacik,salgam"),
    r("kasarli-tost", "Kaşarlı Tost", "k", 2, 3, 6,
      "Klasik kaşarlı ve domatesli tost.",
      "Ekmeğin arasına kaşar ve domates koyun. | Tost makinesinde ya da tavada pişirin.",
      "ekmek 160, kasar 100, domates 100, tereyagi 10", 85),
    r("mantar-sote", "Mantar Sote", "a", 4, 10, 15,
      "Sarımsaklı, biberli mantar sote.",
      "Mantarı yüksek ateşte soteleyin. | Biber, soğan ve sarımsağı ekleyin. | Domates ve baharatla tamamlayın.",
      "mantar 500, sivribiber 100, sogan 80, sarimsak 6, domates 150, aycicek 30, tuz 5, karabiber 2", 74, groups="pilav,bulgur"),
    r("bulgur-salatasi", "Bulgur Salatası", "s", 4, 20, 0,
      "Domates, maydanoz ve nar ekşili bulgur salatası.",
      "Bulguru sıcak suyla ıslatın. | Domates, soğan, biber ve maydanozu ekleyin. | Nar ekşisi, pul biber ve zeytinyağıyla karıştırın.",
      "koftelikbulgur 150, domates 250, sogan 60, sivribiber 80, maydanoz 30, nareksisi 20, zeytinyagi 40, pulbiber 2, tuz 3", 72, tags="ramazan"),
    r("kabak-mucveri", "Kabak Mücveri", "a", 4, 20, 20,
      "Peynirli, dereotlu kızarmış kabak köftesi.",
      "Kabağı rendeleyip suyunu sıkın. | Yumurta, un, peynir ve dereotuyla karıştırın. | Kaşıkla yağa bırakıp kızartın.",
      "kabak 600, yumurta 3, un 80, beyazpeynir 100, dereotu 15, aycicek 150~, tuz 3", 84, slots="kahvalti,ogle,aksam", groups="ayran,cacik", tags="ramazan"),
    r("sebzeli-tavuk-sote", "Sebzeli Tavuk Wrap", "a", 4, 15, 15,
      "Lavaşa sarılmış sebzeli tavuk.",
      "Tavuğu baharatla pişirin. | Lavaşa tavuk, marul, domates ve yoğurt sosu koyun. | Sarıp tavada ısıtın.",
      "tortilla 250, tavukgogus 400, marul 100, domates 150, yogurt 80, sarimsak 3, aycicek 20, tuz 3", 80, slots="ogle,aksam"),
]
