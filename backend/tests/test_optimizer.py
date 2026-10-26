from decimal import Decimal as D

from app.models.enums import PlanType
from app.services.optimizer import NO_COMPLETE_MARKET_WARNING, ItemInput, Offer, optimize

BIM, A101, SOK, FILE = 1, 2, 3, 4
MARKETS = [BIM, A101, SOK, FILE]


def offer(pid, market, price, brand=None):
    return Offer(pid, f"p{pid}", brand, market, D(price))


def item(item_id, offers, brand=None, qty="1"):
    return ItemInput(item_id, item_id * 10, f"g{item_id}", D(qty), brand, tuple(offers))


MILK = [
    offer(1, BIM, "32.50", "Sütaş"),
    offer(2, A101, "34.90", "Pınar"),
    offer(3, SOK, "33.00", "Pınar"),
    offer(4, FILE, "36.00", "Sütaş"),
]
BREAD = [offer(5, BIM, "10.00"), offer(6, A101, "9.50"), offer(7, SOK, "10.50")]
EGGS = [offer(8, BIM, "80.00"), offer(9, A101, "85.00")]


def test_single_market_picks_cheapest_complete_market():
    result = optimize([item(1, MILK), item(2, BREAD), item(3, EGGS)], MARKETS)
    single = result.single_market
    assert single.warning is None
    # BİM: 32.50+10+80=122.50, A101: 34.90+9.50+85=129.40, Şok/File eksik
    assert {line.offer.market_id for line in single.plan.lines} == {BIM}
    assert single.plan.total == D("122.50")
    missing = {m.market_id: m.missing for m in single.markets}
    assert missing == {BIM: 0, A101: 0, SOK: 1, FILE: 2}


def test_single_market_warns_when_no_market_has_everything():
    tea = [offer(10, SOK, "50.00")]
    result = optimize([item(1, EGGS), item(2, tea)], MARKETS)
    assert result.single_market.plan is None
    assert result.single_market.warning == NO_COMPLETE_MARKET_WARNING
    assert result.plan(PlanType.SINGLE_MARKET) is None


def test_single_market_respects_locked_brand():
    # Pınar sadece A101 ve Şok'ta; yumurta Şok'ta yok -> BİM de eksiksiz ama Sütaş'la, A101 tercihe uyuyor
    result = optimize([item(1, MILK, brand="pınar"), item(2, EGGS)], MARKETS)
    assert result.single_market.plan.lines[0].offer.market_id == A101
    assert not any(line.substituted for line in result.single_market.plan.lines)


def test_single_market_uses_similar_product_when_group_missing():
    # "Pirinç 1 kg" grubu BİM'de yok ama "Baldo Pirinç 1 Kg" var
    rice = ItemInput(1, 10, "Pirinç 1 kg", D("1"), "Anadolu Mutfağı", (offer(20, SOK, "32.50", "Anadolu Mutfağı"),),
                     similar_offers=(offer(21, BIM, "45.00", "Baldo"), offer(22, BIM, "39.00", "Ekonomik")))
    result = optimize([rice, item(2, EGGS)], [BIM, SOK])
    single = result.single_market
    assert {(m.market_id, m.missing, m.substituted) for m in single.markets} == {(BIM, 0, 1), (SOK, 1, 0)}
    line = next(line for line in single.plan.lines if line.item_id == 1)
    assert line.substituted and line.offer.product_id == 22
    # Fırsatçı ve Kombinasyon benzer ürünleri kullanmaz
    assert [line.offer.product_id for line in result.opportunist.lines if line.item_id == 1] == [20]


def test_single_market_substitutes_brand_instead_of_missing():
    # Torku hiçbir markette yok: süt her markette başka markayla bulunur, eksik sayılmaz
    result = optimize([item(1, MILK, brand="Torku"), item(2, BREAD)], MARKETS)
    single = result.single_market
    assert single.warning is None
    by_market = {m.market_id: (m.missing, m.substituted) for m in single.markets}
    assert by_market == {BIM: (0, 1), A101: (0, 1), SOK: (0, 1), FILE: (1, 1)}
    # BİM 32.50+10 = 42.50, A101 34.90+9.50 = 44.40, Şok 33+10.50 = 43.50
    assert {line.offer.market_id for line in single.plan.lines} == {BIM}
    milk = next(line for line in single.plan.lines if line.item_id == 1)
    assert milk.substituted and milk.offer.brand == "Sütaş"


def test_combination_respects_brand_and_opportunist_ignores_it():
    result = optimize([item(1, MILK, brand="Pınar", qty="2"), item(2, BREAD)], MARKETS)
    combo = {line.item_id: line.offer for line in result.combination.lines}
    opp = {line.item_id: line.offer for line in result.opportunist.lines}
    assert combo[1].market_id == SOK and combo[1].brand == "Pınar"
    assert opp[1].market_id == BIM and opp[1].brand == "Sütaş"
    assert combo[2].market_id == opp[2].market_id == A101

    assert result.combination.total == D("75.50")  # 2*33 + 9.50
    assert result.opportunist.total == D("74.50")  # 2*32.50 + 9.50
    assert result.savings.weekly == D("1.00")
    assert result.savings.monthly == D("4.00")
    assert result.savings.yearly == D("52.00")


def test_unavailable_brand_is_missing_and_not_counted_as_savings():
    result = optimize([item(1, MILK, brand="Torku"), item(2, BREAD)], MARKETS)
    assert result.combination.missing_item_ids == [1]
    assert result.opportunist.missing_item_ids == []
    assert result.savings.weekly == D("0.00")


def test_farketmez_items_produce_no_savings():
    result = optimize([item(1, MILK), item(2, BREAD)], MARKETS)
    assert result.combination.total == result.opportunist.total
    assert result.savings.weekly == D("0.00")


def test_plan_groups_lines_by_market():
    result = optimize([item(1, MILK), item(2, BREAD), item(3, EGGS)], MARKETS)
    by_market = result.opportunist.lines_by_market()
    assert {m: [line.item_id for line in lines] for m, lines in by_market.items()} == {
        BIM: [1, 3],
        A101: [2],
    }
