"""İndirimden menü: şu an indirimde olan malzemelerle ("tavuk indirimde, tavuklu hafta") menü kurma.

İki kaynak:
- Katalog fırsatları (catalog.deals): ürün grubu fiyatı son 30 günün zirvesinden ya da kampanya öncesi
  fiyattan düşük olanlar. Bunlar maliyet motorundaki ürün gruplarıdır; plan maliyeti indirimli fiyatı zaten
  yansıtır (en ucuz uygun ürün seçilir).
- Market aktüel/broşür ürünleri (AktuelItem): ürün grubuyla ilişkisi, kategorisi ve fiyat geçmişi yoktur. Bu
  yüzden yalnızca ad eşleşmesiyle (daha sıkı) "bu hafta indirimde" ipucu olarak sayılır: menüde öne çıkarmak ve
  etiketlemek için kullanılır, planın maliyetine girmez.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AktuelItem, Cuisine, Recipe
from app.schemas.meals import DealIngredient, DealMenuOut, DealRecipe, DealUse
from app.schemas.products import DealOut
from app.services import meals
from app.services.catalog import deals as catalog_deals
from app.services.ingredient_match import grocery_like, name_matches, unit_compatible
from app.services.normalize import normalize_text, parse_quantity

TZ = ZoneInfo("Europe/Istanbul")
DEAL_LIMIT = 500
AKTUEL_FRESH_DAYS = 14
TOP_INGREDIENTS = 30
TOP_RECIPES = 12


@dataclass
class _Hit:
    """Bir tarif malzemesiyle eşleşen indirim."""

    product_name: str
    price: Decimal
    previous_price: Decimal | None
    discount_percent: int | None
    source: str  # katalog / aktuel
    group_id: int | None = None
    market_slug: str | None = None

    def sort_key(self) -> tuple:
        return (self.source == "katalog", self.discount_percent or 0)


def _percent(price: Decimal, previous: Decimal | None) -> int | None:
    if previous is None or previous <= 0 or price >= previous:
        return None
    return int((1 - price / previous) * 100)


async def _aktuel_items(db: AsyncSession, today: date) -> list[AktuelItem]:
    fresh = datetime.now(timezone.utc) - timedelta(days=AKTUEL_FRESH_DAYS)
    return list((await db.scalars(
        select(AktuelItem).where(
            AktuelItem.seen_at >= fresh,
            or_(AktuelItem.starts_on.is_(None), AktuelItem.starts_on <= today),
            or_(AktuelItem.ends_on.is_(None), AktuelItem.ends_on >= today),
        )
    )).all())


def _catalog_ok(need: meals._Need, deal: DealOut, categories: dict[str, int]) -> bool:
    non_food = {categories[s] for s in meals.NON_FOOD_CATEGORIES if s in categories}
    if deal.category_id in non_food:
        return False
    if need.categories and deal.category_id is not None and deal.category_id not in {
        categories[s] for s in need.categories if s in categories
    }:
        return False
    return grocery_like(deal.group_name, deal.quantity, deal.category_id is not None) and unit_compatible(need.unit, deal.unit)


def _aktuel_ok(need: meals._Need, item: AktuelItem) -> bool:
    """Broşür ürününün kategorisi yok: ad + miktar metni gıda gibi görünmeli, birim uyuşmalı."""
    text = f"{item.title} {item.quantity_text or ''}".strip()
    if not grocery_like(text):
        return False
    parsed = parse_quantity(text)
    return parsed is None or unit_compatible(need.unit, parsed[1])


def _alternatives(need: meals._Need) -> list[str]:
    return [t.strip() for t in need.search_term.split("|") if t.strip()]


async def find_hits(db: AsyncSession, user_id: int | None, recipes: list[Recipe]) -> dict[str, _Hit]:
    """Tariflerdeki (evde var sayılmayan) malzemelerin her biri için en iyi indirim: arama ifadesi -> indirim."""
    today = datetime.now(TZ).date()  # sunucu UTC olsa da İstanbul günü
    categories = await meals._category_ids(db)
    deals = await catalog_deals(db, user_id, DEAL_LIMIT)
    aktuel = await _aktuel_items(db, today)
    needs: dict[str, meals._Need] = {}
    for recipe in recipes:
        for ing in recipe.ingredients:
            if not ing.is_pantry:
                needs.setdefault(normalize_text(ing.search_term), meals._need_of(ing))
    hits: dict[str, _Hit] = {}
    for key, need in needs.items():
        found: list[_Hit] = []
        for alt in _alternatives(need):
            for deal in deals:
                if _catalog_ok(need, deal, categories) and name_matches(alt, deal.group_name, need.excludes):
                    found.append(_Hit(
                        deal.product_name, deal.price, deal.previous_price, deal.discount_percent, "katalog",
                        group_id=deal.group_id,
                    ))
            for item in aktuel:
                if _aktuel_ok(need, item) and name_matches(alt, item.title, need.excludes):
                    found.append(_Hit(
                        item.title, item.price, item.old_price, _percent(item.price, item.old_price), "aktuel",
                        market_slug=item.market_slug,
                    ))
        if found:
            hits[key] = max(found, key=_Hit.sort_key)
    return hits


async def deal_terms(db: AsyncSession, user_id: int | None, recipes: list[Recipe]) -> set[str]:
    """Menüde öne çıkarılacak malzemeler: yalnız katalog indirimleri (sepet fiyatına yansıyanlar). Broşür
    ipuçları kullanıcının marketine bağlı olmadığı için planı yönlendirmez, yalnız etiket olarak gösterilir."""
    return {k for k, hit in (await find_hits(db, user_id, recipes)).items() if hit.source == "katalog"}


def _use(name: str, hit: _Hit) -> DealUse:
    return DealUse(
        name=name, product_name=hit.product_name, price=hit.price, previous_price=hit.previous_price,
        discount_percent=hit.discount_percent, source=hit.source, market_slug=hit.market_slug,
    )


async def _recipes(db: AsyncSession) -> list[Recipe]:
    return list((await db.scalars(
        select(Recipe).join(Cuisine).where(Recipe.is_active, Cuisine.is_active, meals._available())
        .options(*meals._recipe_options()).order_by(Recipe.id)
    )).all())


async def menu(db: AsyncSession, user_id: int | None) -> DealMenuOut:
    """İndirimdeki malzemeler (kaç tarifte geçtiğiyle) ve bunları en çok kullanan tarifler."""
    recipes = await _recipes(db)
    hits = await find_hits(db, user_id, recipes)
    liked = await meals.liked_ids(db, user_id)
    names: dict[str, str] = {}
    counts: dict[str, int] = {}
    scored: list[tuple[int, int, Recipe, list[str]]] = []
    for recipe in recipes:
        used = []
        for ing in recipe.ingredients:
            key = normalize_text(ing.search_term)
            if ing.is_pantry or key not in hits or ing.name in used:
                continue
            used.append(ing.name)
            names.setdefault(key, ing.name)
            counts[key] = counts.get(key, 0) + 1
        if used:
            scored.append((len(used), recipe.score, recipe, used))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2].id))
    ingredients = sorted(
        (
            DealIngredient(**_use(names[key], hit).model_dump(), recipe_count=counts[key])
            for key, hit in hits.items() if key in counts
        ),
        key=lambda d: (-d.recipe_count, -(d.discount_percent or 0), d.name),
    )[:TOP_INGREDIENTS]
    note = None
    if not hits:
        note = "Şu an indirimde olan bir malzeme bulunamadı; menü normal fiyatlarla kurulur."
    return DealMenuOut(
        ingredients=ingredients,
        recipes=[
            DealRecipe(recipe=meals.recipe_summary(r, liked), deal_ingredients=used)
            for _, _, r, used in scored[:TOP_RECIPES]
        ],
        note=note,
    )


async def uses_in_plan(
    db: AsyncSession, plan, user_id: int | None, cost
) -> list[DealUse]:
    """Planın malzemelerinden şu an indirimde olanlar. Katalog indirimi yalnız maliyet motorunun seçtiği ürün
    grubu o indirimli grupsa gösterilir ("tavuk indirimde" derken seçilen ürün indirimli olmayabilir);
    broşür indirimi ipucu olarak (fiyata girmeden) gösterilir."""
    recipes = [e.recipe for e in plan.entries]
    hits = await find_hits(db, user_id, recipes)
    picked = {line.key: line.match.group_id for line in cost.lines if line.match}
    out: dict[str, DealUse] = {}
    for recipe in recipes:
        for ing in recipe.ingredients:
            key = normalize_text(ing.search_term)
            hit = hits.get(key)
            if ing.is_pantry or hit is None or key in out:
                continue
            if hit.source == "katalog" and picked.get(key) != hit.group_id:
                continue
            out[key] = _use(ing.name, hit)
    return list(out.values())
