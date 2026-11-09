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
