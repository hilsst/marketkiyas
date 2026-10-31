import pytest

from app.services.ingredient_match import name_matches


@pytest.mark.parametrize(
    ("term", "product", "expected"),
    [
        # Kemal'in bulduğu hatalar
        ("zeytinyagi", "Zeytinyağlı Sıvı Sabun 1,5 L", False),
        ("limon", "Limonlu Popkek 45 g", False),
        ("zeytinyagi", "Komili Riviera Zeytinyağı 1 L", True),
        ("zeytinyagi", "Sızma Zeytin Yağı 2 L", True),
        ("limon", "Limon Kg", True),
        ("limon", "Limon Kolonyası 400 ml", False),
        ("limon", "Limon Aromalı Gazoz 1 L", False),
        ("limon", "Limon Suyu 500 ml", False),
        ("domates salcasi", "Tat Domates Salçası 830 g", True),
        ("domates", "Domates Salçası 830 g", False),
        ("domates", "Domates Kg", True),
        ("tuz", "Sofra Tuzu 750 g", True),
        ("tuz", "Tuzsuz Tereyağı 250 g", False),
        ("pul biber", "Sivri Biber 500 g", False),
        ("pilic gogus", "Piliç Göğüs Fileto 1 kg", True),
        ("sut", "Sütlü Çikolata 80 g", False),
        ("sut", "Pınar Tam Yağlı Süt 1 L", True),
        ("bal", "Çiçek Balı 450 g", True),
        ("bal", "Balık Yağı Kapsül", False),
        ("pirinc", "Pirinç Unu 500 g", False),
        ("pirinc unu", "Pirinç Unu 500 g", True),
        ("bugday unu", "Buğday Unu 1 kg", True),
        ("kuru sogan", "Kuru Soğan 1 kg", True),
        ("nar eksisi", "Nar Ekşisi 330 ml", True),
        ("nar eksisi", "Nar Ekşisi Sosu 330 ml", False),
        ("portakal suyu", "Portakal Suyu 1 L", True),
        ("yumurta", "Yumurta 15'li", True),
        ("tereyagi", "Tereyağı 250 g", True),
        ("tereyagi", "Tereyağlı Kruvasan", False),
        ("mercimek", "Mercimek Çorbası 70 g", False),
        ("elma", "Elmalı Turta", False),
        ("salgam suyu", "Şalgam Suyu Acılı 1 L", True),
        ("ekmek", "Ekmek Kadayıfı 200 g", False),
        ("kekik", "Kekik 40 g", True),
        ("aycicek yagi", "Ayçiçek Yağı 5 L", True),
        ("bal kabagi", "Bal Kabağı Kg", True),
        ("manti", "Kayseri Mantısı 500 g", True),
    ],
)
def test_name_matches(term, product, expected):
    assert name_matches(term, product) is expected


def test_excludes():
    assert not name_matches("bal", "Bal Kabağı Kg", ("kabag",))
