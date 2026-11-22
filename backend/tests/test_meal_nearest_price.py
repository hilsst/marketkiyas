"""Yemek planı malzeme fiyatı: konum varsa en yakın şubenin fiyatı, yoksa en ucuz market."""
from decimal import Decimal
from types import SimpleNamespace

from app.services.meals import _cheapest_market


def _group(**extra) -> SimpleNamespace:
    base = {
        "min_price": Decimal(30),
        "market_prices": [
            SimpleNamespace(market_id=1, min_price=Decimal(40)),
            SimpleNamespace(market_id=2, min_price=Decimal(30)),
        ],
        "nearest_price": None,
        "nearest_market_id": None,
    }
    return SimpleNamespace(**{**base, **extra})


def test_cheapest_market_without_location():
    assert _cheapest_market(_group()) == (Decimal(30), 2)


def test_nearest_store_price_wins_over_cheaper_far_one():
    group = _group(nearest_price=Decimal(40), nearest_market_id=1)
    assert _cheapest_market(group) == (Decimal(40), 1)


def test_meal_savings_vs_average_and_cheapest():
    from app.services.meals import _meal_savings, _price_for

    group = _group(
        id=1, unit="g", quantity=None, nearest_price=Decimal(40), nearest_market_id=1,
        nearest_store_name="Migros Yakın", market_prices=[
            SimpleNamespace(market_id=1, min_price=Decimal(40)),
            SimpleNamespace(market_id=2, min_price=Decimal(20)),
            SimpleNamespace(market_id=3, min_price=Decimal(60)),
        ],
    )
    need = SimpleNamespace(unit="adet", quantity=Decimal(1))
    pick = _price_for(group, need)
    out = _meal_savings([pick], True)
    assert out["nearest_store"] == "Migros Yakın"
    assert out["savings"] == Decimal("0.00")  # yakın şube ortalama (40) ile aynı
    assert out["nearby_extra"] == Decimal("20.00")  # en ucuz şubeye (20) göre fazlası


def test_meal_savings_without_location_has_no_nearby_extra():
    from app.services.meals import _meal_savings, _price_for

    pick = _price_for(_group(id=1, unit="g", quantity=None), SimpleNamespace(unit="adet", quantity=Decimal(1)))
    out = _meal_savings([pick], False)
    assert out["nearby_extra"] is None and out["savings"] == Decimal("5.00")
