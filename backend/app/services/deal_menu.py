"""İndirimden menü: şu an indirimde olan ürünleri tarif malzemelerine bağlar.

"Tavuk indirimde, tavuklu hafta": fırsatlar (son 30 günde ucuzlayan ya da kampanyadaki ürünler) ve
satıştaki aktüel (broşür) ürünleri, tariflerin malzeme arama ifadeleriyle eşleştirilir. Kullanıcı bu
malzemelerden seçer; plan oluşturulurken (MealPlanCreate.prefer) bu malzemeleri kullanan tarifler öne çıkar.

Eşleştirme kuralı tarif maliyetindekiyle aynıdır (ingredient_match.name_matches), böylece
"zeytinyağı" fırsatı "Zeytinyağlı Sabun" olmaz."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AktuelItem, Recipe, RecipeIngredient
from app.schemas.meals import DealIngredientOut
from app.services import catalog, meals
from app.services.ingredient_match import name_matches
from app.services.normalize import normalize_text

MAX_DEALS = 100


@dataclass
class _Ingredient:
    name: str
    term: str
    excludes: tuple[str, ...]
    recipes: set[int] = field(default_factory=set)
    recipe_names: list[str] = field(default_factory=list)


async def _ingredients(db: AsyncSession) -> list[_Ingredient]:
    rows = await db.execute(
        select(RecipeIngredient.name, RecipeIngredient.search_term, RecipeIngredient.exclude_terms, Recipe.id, Recipe.name)
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .where(Recipe.is_active.is_(True), meals._available(), RecipeIngredient.is_pantry.is_(False))
    )
    by_key: dict[str, _Ingredient] = {}
    for name, term, excludes, recipe_id, recipe_name in rows:
        key = normalize_text(name)
        ing = by_key.get(key)
        if ing is None:
            ex = tuple(normalize_text(e) for e in (excludes or "").split(",") if e.strip())
            ing = by_key[key] = _Ingredient(name=name, term=term, excludes=ex)
        if recipe_id not in ing.recipes and len(ing.recipe_names) < 2:
            ing.recipe_names.append(recipe_name)
        ing.recipes.add(recipe_id)
    return list(by_key.values())


def _percent(price: Decimal, before: Decimal | None) -> int:
    if not before or before <= price:
        return 0
    return int((1 - price / before) * 100)


async def deal_ingredients(db: AsyncSession, user_id: int | None) -> list[DealIngredientOut]:
    """İndirimdeki malzemeler, en çok indirimliden; her malzeme için en iyi fırsat."""
    deals = await catalog.deals(db, user_id, MAX_DEALS)
    today = date.today()
    aktuel = (await db.scalars(
        select(AktuelItem).where(
            or_(AktuelItem.starts_on.is_(None), AktuelItem.starts_on <= today),
            or_(AktuelItem.ends_on.is_(None), AktuelItem.ends_on >= today),
        )
    )).all()

    out: list[DealIngredientOut] = []
    for ing in await _ingredients(db):
        best: DealIngredientOut | None = None
        for d in deals:
            if name_matches(ing.term, d.group_name, ing.excludes):
                cand = DealIngredientOut(
                    name=ing.name, recipe_count=len(ing.recipes), recipe_names=ing.recipe_names, source="deal", product_name=d.group_name,
                    group_id=d.group_id, market_id=d.market_id, market_slug=None, image_url=d.image_url,
                    price=d.price, previous_price=d.previous_price, discount_percent=d.discount_percent,
                )
                if best is None or cand.discount_percent > best.discount_percent:
                    best = cand
        for a in aktuel:
            if name_matches(ing.term, a.title, ing.excludes):
                cand = DealIngredientOut(
                    name=ing.name, recipe_count=len(ing.recipes), recipe_names=ing.recipe_names, source="aktuel", product_name=a.title,
                    group_id=None, market_id=None, market_slug=a.market_slug, image_url=a.image_url,
                    price=a.price, previous_price=a.old_price, discount_percent=_percent(a.price, a.old_price),
                )
                if best is None or cand.discount_percent > best.discount_percent:
                    best = cand
        # İndirimi bilinmeyen ve tek tarifte geçen malzeme listeyi kalabalıklaştırır
        if best is not None and (best.discount_percent > 0 or best.recipe_count >= 2):
            out.append(best)
    # Önce gerçek indirimler (tasarruf TL'si, sonra oran), sonra indirim oranı bilinmeyenler
    out.sort(key=lambda d: (
        d.discount_percent == 0,
        -(float(d.previous_price - d.price) if d.previous_price and d.previous_price > d.price else 0.0),
        -d.discount_percent, -d.recipe_count, d.name,
    ))
    return out
