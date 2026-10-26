"""Liste optimizasyonu: Tek Market, Kombinasyon ve Fırsatçı planları.

Saf Python; veritabanına dokunmaz. `load_list_offers` (services/lists.py) girdiyi hazırlar.

- Kombinasyon: kullanıcının marka tercihlerine uyarak her kalemi en ucuz olduğu marketten alır.
  Bu aynı zamanda "kullanıcının kendi tercihleriyle ödeyeceği tutar"dır (Tasarruf'un referansı).
- Fırsatçı: marka tercihlerini yok sayar, her kalemin piyasadaki en ucuzunu alır.
- Tek Market: her marketin toplamını tercihlere uyarak hesaplar; tercih edilen marka o markette yoksa
  aynı ürünün o marketteki en ucuz başka markası alınır (substituted). Kalem yalnızca market o ürünü
  hiç satmıyorsa eksiktir. Eksiksiz marketlerden önce en az marka değişikliği olanı, sonra en ucuzu
  seçilir. Hiçbiri eksiksiz değilse plan yoktur ve uyarı döner.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from app.models.enums import PlanType

NO_COMPLETE_MARKET_WARNING = "Hiçbir market listedeki tüm ürünleri satmıyor"

WEEKS_PER_MONTH = 4
WEEKS_PER_YEAR = 52


@dataclass(frozen=True)
class Offer:
    """Bir grubun bir marketteki somut ürünü ve fiyatı."""

    product_id: int
    product_name: str
    brand: str | None
    market_id: int
    unit_price: Decimal
    store_id: int | None = None  # fiyatın geldiği şube (kullanıcı şube seçtiyse)


@dataclass(frozen=True)
class ItemInput:
    item_id: int
    group_id: int
    group_name: str
    quantity: Decimal
    preferred_brand: str | None  # None = Farketmez
    offers: tuple[Offer, ...]
    preferred_product_id: int | None = None  # ürün kilidi: yalnızca bu ürün (ve marketi)
    # Benzer gruplardaki ürünler ("Pirinç 1 kg" için "Baldo Pirinç 1 Kg"); yalnızca Tek Market'te,
    # grubun kendisi o markette hiç yoksa kullanılır
    similar_offers: tuple[Offer, ...] = ()

    def allowed_offers(self, respect_brand: bool) -> list[Offer]:
        if not respect_brand:
            return list(self.offers)
        if self.preferred_product_id is not None:
            return [o for o in self.offers if o.product_id == self.preferred_product_id]
        if not self.preferred_brand:
            return list(self.offers)
        brand = self.preferred_brand.casefold()
        return [o for o in self.offers if o.brand and o.brand.casefold() == brand]


@dataclass
class PlanLine:
    item_id: int
    group_id: int
    group_name: str
    quantity: Decimal
    offer: Offer
    substituted: bool = False  # tercih edilen marka bu markette yok, başka marka alındı

    @property
    def line_total(self) -> Decimal:
        return (self.offer.unit_price * self.quantity).quantize(Decimal("0.01"))


@dataclass
class Plan:
    plan_type: PlanType
    lines: list[PlanLine] = field(default_factory=list)
    missing_item_ids: list[int] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((line.line_total for line in self.lines), Decimal("0.00"))

    def lines_by_market(self) -> dict[int, list[PlanLine]]:
        grouped: dict[int, list[PlanLine]] = defaultdict(list)
        for line in self.lines:
            grouped[line.offer.market_id].append(line)
        return dict(grouped)


@dataclass
class MarketTotal:
    market_id: int
    total: Decimal
    found: int
    missing: int
    substituted: int = 0  # farklı markayla bulunan kalem sayısı


@dataclass
class SingleMarketResult:
    plan: Plan | None  # None -> eksiksiz market yok
    markets: list[MarketTotal]
    warning: str | None


@dataclass
class Savings:
    preference_total: Decimal
    optimized_total: Decimal
    weekly: Decimal

    @property
    def monthly(self) -> Decimal:
        return self.weekly * WEEKS_PER_MONTH

    @property
    def yearly(self) -> Decimal:
        return self.weekly * WEEKS_PER_YEAR


@dataclass
class OptimizationResult:
    single_market: SingleMarketResult
    combination: Plan
    opportunist: Plan
    savings: Savings

    def plan(self, plan_type: PlanType) -> Plan | None:
        if plan_type is PlanType.SINGLE_MARKET:
            return self.single_market.plan
        if plan_type is PlanType.COMBINATION:
            return self.combination
        return self.opportunist


def _cheapest(offers: list[Offer]) -> Offer | None:
    # Eşit fiyatta deterministik sonuç için market_id, product_id ile kır
    return min(offers, key=lambda o: (o.unit_price, o.market_id, o.product_id), default=None)


def _cheapest_plan(plan_type: PlanType, items: list[ItemInput], respect_brand: bool) -> Plan:
    plan = Plan(plan_type)
    for item in items:
        offer = _cheapest(item.allowed_offers(respect_brand))
        if offer is None:
            plan.missing_item_ids.append(item.item_id)
        else:
            plan.lines.append(PlanLine(item.item_id, item.group_id, item.group_name, item.quantity, offer))
    return plan


def opportunist_plan(items: list[ItemInput]) -> Plan:
    """Tercihler yok sayılarak her kalemin en ucuzu (liste kartındaki "Tahmini" tutar)."""
    return _cheapest_plan(PlanType.OPPORTUNIST, items, respect_brand=False)


def single_market(items: list[ItemInput], market_ids: list[int]) -> SingleMarketResult:
    totals: list[MarketTotal] = []
    plans: dict[int, Plan] = {}
    for market_id in market_ids:
        plan = Plan(PlanType.SINGLE_MARKET)
        for item in items:
            offer = _cheapest([o for o in item.allowed_offers(respect_brand=True) if o.market_id == market_id])
            substituted = False
            if offer is None:
                # Tercih edilen marka yok: aynı ürünün bu marketteki başka bir markası, o da yoksa benzeri
                offer = _cheapest([o for o in item.offers if o.market_id == market_id]) or _cheapest(
                    [o for o in item.similar_offers if o.market_id == market_id]
                )
                substituted = offer is not None
            if offer is None:
                plan.missing_item_ids.append(item.item_id)
            else:
                plan.lines.append(
                    PlanLine(item.item_id, item.group_id, item.group_name, item.quantity, offer, substituted)
                )
        plans[market_id] = plan
        totals.append(
            MarketTotal(
                market_id,
                plan.total,
                len(plan.lines),
                len(plan.missing_item_ids),
                sum(line.substituted for line in plan.lines),
            )
        )

    complete = [t for t in totals if t.missing == 0]
    if not items or not complete:
        return SingleMarketResult(None, totals, NO_COMPLETE_MARKET_WARNING if items else None)
    best = min(complete, key=lambda t: (t.substituted, t.total, t.market_id))
    return SingleMarketResult(plans[best.market_id], totals, None)


def calculate_savings(combination: Plan, opportunist: Plan) -> Savings:
    """Tasarruf = kullanıcının tercihleriyle ödeyeceği tutar - Fırsatçı toplamı.

    Kullanıcının tercih ettiği markanın hiç bulunmadığı kalemler iki tarafta da hesaba katılmaz,
    aksi halde eksik ürün "tasarruf" gibi görünürdü.
    """
    comparable = {line.item_id for line in combination.lines}
    preference = combination.total
    optimized = sum(
        (line.line_total for line in opportunist.lines if line.item_id in comparable), Decimal("0.00")
    )
    return Savings(preference, optimized, max(preference - optimized, Decimal("0.00")))


def optimize(items: list[ItemInput], market_ids: list[int]) -> OptimizationResult:
    combination = _cheapest_plan(PlanType.COMBINATION, items, respect_brand=True)
    opportunist = opportunist_plan(items)
    return OptimizationResult(
        single_market=single_market(items, market_ids),
        combination=combination,
        opportunist=opportunist,
        savings=calculate_savings(combination, opportunist),
    )
