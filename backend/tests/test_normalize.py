from decimal import Decimal

import pytest

from app.models.enums import Unit
from app.services.normalize import normalize_name, normalize_text, parse_quantity


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Pınar Süt 1 L", "pinar sut 1000ml"),
        ("PINAR SÜT 1L", "pinar sut 1000ml"),
        ("Sütaş Yoğurt 2x500 g", "sutas yogurt 1000g"),
        ("30'lu Yumurta", "yumurta 30adet"),
        ("Ülker Çikolata 1,5 kg", "ulker cikolata 1500g"),
        ("Erikli Su 0,5 lt", "erikli su 500ml"),
        ("Domates", "domates"),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_turkish_dotted_i():
    assert normalize_text("İÇİM AYRAN") == "icim ayran"


def test_parse_quantity():
    assert parse_quantity("Ayçiçek Yağı 5 L") == (Decimal(5000), Unit.ML)
    assert parse_quantity("Ekmek") is None
