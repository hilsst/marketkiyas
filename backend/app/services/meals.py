"""Yemek planlayıcı: plan oluşturma, malzeme maliyeti ve alışveriş listesine aktarma.

Maliyet: plandaki her yemeğin malzemeleri kişi sayısına göre orantılanıp toplanır (aynı malzeme
farklı yemeklerde geçiyorsa birleşir). Her malzeme için katalogda arama yapılır ve kullanıcının
şubelerinde (seçmediyse zincir genelinde) gereken miktarı en ucuza karşılayan ürün grubu seçilir.

Mutfaklar: bir plan birden çok mutfaktan (Türk, İtalyan, Uzak Doğu...) oluşabilir. Her öğün tek bir
mutfaktan gelir (spagettinin yanına ayran gelmesin), mutfaklar öğünlere dengeli dağıtılır.

Bulunabilirlik: malzemelerinden biri uygulamadaki marketlerin hiçbirinde bulunamayan tarif (ör. nori
yosunu, mascarpone) planlarda ve tarif listesinde yer almaz; bkz. refresh_availability.
"""

import json
import logging

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Allergen,
    Category,
    CourseType,
    Cuisine,
    Diet,
    GroupMember,
    MealPlan,
    MealPlanEntry,
    MealSlot,
    PantryItem,
    PlanPeriod,
    Product,
    Recipe,
    RecipeIngredient,
    RecipeLike,
    ShoppingList,
    ShoppingListItem,
    Unit,
    User,
)
from app.schemas.meals import (
    BudgetOut,
    CostLine,
    CostOut,
    CuisineOut,
    IngredientChoice,
    IngredientOut,
    MatchedGroup,
    MealPlanDetail,
    MealPlanEntryOut,
    MealPlanSummary,
    Nutrition,
    PantryItemOut,
    RecipeDetail,
    RecipeSummary,
    StockUse,
)
from app.schemas.products import GroupSummary
from app.services import lists as list_svc
from app.services.catalog import search_groups
from app.services.ingredient_match import name_matches
from app.services.normalize import normalize_text

log = logging.getLogger("marketkiyas.meals")

SLOT_ORDER = {MealSlot.BREAKFAST: 0, MealSlot.LUNCH: 1, MealSlot.SNACK: 2, MealSlot.DINNER: 3}
COURSE_ORDER = {
    CourseType.SOUP: 0, CourseType.MAIN: 1, CourseType.SIDE: 2, CourseType.SALAD: 3, CourseType.DESSERT: 4,
    CourseType.DRINK: 5, CourseType.SNACK: 6,
}
MENU = [CourseType.SOUP, CourseType.MAIN, CourseType.SIDE, CourseType.SALAD, CourseType.DESSERT, CourseType.DRINK]
# Her öğünde önerilecek yemek türleri
SLOT_COURSES = {
    MealSlot.BREAKFAST: [CourseType.MAIN, CourseType.DRINK],
    MealSlot.LUNCH: MENU,
    MealSlot.SNACK: [CourseType.SNACK],
    MealSlot.DINNER: MENU,
}
PERIOD_DAYS = {PlanPeriod.DAILY: 1, PlanPeriod.WEEKLY: 7}  # days verilmezse
# Bir malzeme için değerlendirilecek arama sonucu sayısı
MATCH_CANDIDATES = 50
CENT = Decimal("0.01")
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _qty(value: Decimal) -> Decimal:
    """Miktar: en fazla 2 ondalık, gereksiz sıfırlar atılır; 200 -> 200 (2E+2 değil)."""
    value = value.quantize(CENT).normalize()
    return value.quantize(Decimal(1)) if value == value.to_integral() else value


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


# --- Mutfaklar ve tarifler -------------------------------------------------------------------


def _recipe_options():
    return selectinload(Recipe.cuisine), selectinload(Recipe.ingredients)


def _available():
    """Malzemeleri marketlerde bulunan (ya da henüz kontrol edilmemiş) tarifler."""
    return or_(Recipe.missing_ingredients.is_(None), Recipe.missing_ingredients == "")


async def cuisines(db: AsyncSession) -> list[CuisineOut]:
    """Mutfaklar; tarif sayısı ve örnekler yalnız malzemesi bulunan tariflerden."""
    recipes = (await db.scalars(select(Recipe).where(Recipe.is_active, _available()))).all()
    by_cuisine: dict[int, list[Recipe]] = defaultdict(list)
    for r in recipes:
        by_cuisine[r.cuisine_id].append(r)
    rows = await db.scalars(select(Cuisine).where(Cuisine.is_active).order_by(Cuisine.position, Cuisine.id))
    out = []
    for c in rows:
        mine = by_cuisine.get(c.id, [])
        # Örnek olarak öğle/akşam yemekleri (kahvaltılık değil), en sevilenler
        mains = sorted(
            (r for r in mine if r.course_type is CourseType.MAIN),
            key=lambda r: (MealSlot.DINNER not in r.slots, -r.score, r.id),
        )
        out.append(CuisineOut(
            slug=c.slug, name=c.name, icon=c.icon, is_default=c.is_default, recipe_count=len(mine),
            examples=[r.name for r in mains[:3]],
        ))
    return out


async def get_cuisine(db: AsyncSession, slug: str | None) -> Cuisine:
    """slug boşsa varsayılan mutfak (Türk)."""
    stmt = select(Cuisine).where(Cuisine.is_active)
    stmt = stmt.where(Cuisine.slug == slug) if slug else stmt.order_by(Cuisine.is_default.desc(), Cuisine.position)
    cuisine = await db.scalar(stmt.limit(1))
    if cuisine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mutfak bulunamadı")
    return cuisine


async def get_cuisines(db: AsyncSession, slugs: list[str]) -> list[Cuisine]:
    """Seçilen mutfaklar (seçim sırasıyla, tekrarsız); boşsa varsayılan mutfak."""
    slugs = list(dict.fromkeys(s for s in slugs if s))
    if not slugs:
        return [await get_cuisine(db, None)]
    found = {c.slug: c for c in (await db.scalars(
        select(Cuisine).where(Cuisine.is_active, Cuisine.slug.in_(slugs))
    )).all()}
    unknown = [s for s in slugs if s not in found]
    if unknown:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Mutfak bulunamadı: {', '.join(unknown)}")
    return [found[s] for s in slugs]


def nutrition_of(recipe: Recipe) -> Nutrition | None:
    if recipe.kcal is None:
        return None
    return Nutrition(kcal=recipe.kcal, protein_g=recipe.protein_g or 0, carbs_g=recipe.carbs_g or 0, fat_g=recipe.fat_g or 0)


def recipe_summary(recipe: Recipe, liked: set[int] | None = None) -> RecipeSummary:
    return RecipeSummary(
        id=recipe.id,
        slug=recipe.slug,
        name=recipe.name,
        cuisine=recipe.cuisine.slug,
        course=recipe.course,
        course_type=recipe.course_type,
        pairs_with=[p for p in (recipe.pairs_with or "").split(",") if p],
        meal_slots=recipe.slots,
        servings=recipe.servings,
        prep_minutes=recipe.prep_minutes,
        cook_minutes=recipe.cook_minutes,
        description=recipe.description,
        icon=recipe.icon,
        image_url=recipe.image_url,
        allergens=recipe.allergen_list,
        diets=recipe.diet_list,
        nutrition=nutrition_of(recipe),
        like_count=recipe.like_count,
        liked=bool(liked) and recipe.id in liked,
    )


async def liked_ids(db: AsyncSession, user_id: int | None) -> set[int]:
    if user_id is None:
        return set()
    return set((await db.scalars(select(RecipeLike.recipe_id).where(RecipeLike.user_id == user_id))).all())


async def list_recipes(
    db: AsyncSession, cuisine: str | None, slot: MealSlot | None, course: CourseType | None = None,
    diets: list[Diet] | None = None, avoid: list[Allergen] | None = None, user_id: int | None = None,
    have: list[str] | None = None,
) -> list[RecipeSummary]:
    """En sevilenler önce (başlangıç puanı + kullanıcı beğenileri).

    have ("Dolabımda ne var"): yalnız bu malzemelerden en az birini kullanan tarifler; en az eksiği
    olan önce, her tarifte alınması gereken (evde var sayılmayan) eksik malzemeler `missing`'de."""
    stmt = (
        select(Recipe).join(Cuisine).where(Recipe.is_active, Cuisine.is_active, _available())
        .options(*_recipe_options())
    )
    if cuisine:
        stmt = stmt.where(Cuisine.slug == cuisine)
    recipes = [
        r for r in (await db.scalars(stmt.order_by(Recipe.id))).all()
        if (slot is None or slot in r.slots) and (course is None or r.course_type is course)
        and r.suits(diets or [], avoid or [])
    ]
    recipes.sort(key=lambda r: (-r.score, r.id))
    liked = await liked_ids(db, user_id)
    home = have_set(have or [])
    if not home:
        return [recipe_summary(r, liked) for r in recipes]
    out = []
    for r in recipes:
        needed = [i for i in r.ingredients if not i.is_pantry]
        used = [i for i in needed if normalize_text(i.name) in home]
        if not used:
            continue
        summary = recipe_summary(r, liked)
        summary.missing = list(dict.fromkeys(i.name for i in needed if normalize_text(i.name) not in home))
        out.append((len(summary.missing), -len(used), summary))
    out.sort(key=lambda x: (x[0], x[1]))  # sıralama kararlı: eşitlerde sevilen önce kalır
    return [x[2] for x in out]


async def ingredient_choices(db: AsyncSession) -> list[IngredientChoice]:
    """"Dolabımda ne var" seçicisi için tariflerde geçen malzemeler (tuz, baharat gibi evde var
    sayılanlar hariç); en çok tarifte geçen önce."""
    recipes = (await db.scalars(
        select(Recipe).join(Cuisine).where(Recipe.is_active, Cuisine.is_active, _available())
        .options(selectinload(Recipe.ingredients))
    )).all()
    names: dict[str, str] = {}
    counts: Counter = Counter()
    for r in recipes:
        for key in {normalize_text(i.name): i for i in r.ingredients if not i.is_pantry}:
            counts[key] += 1
        for i in r.ingredients:
            if not i.is_pantry:
                names.setdefault(normalize_text(i.name), i.name)
    return [
        IngredientChoice(name=names[k], recipe_count=n)
        for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], names[kv[0]]))
    ]


async def set_like(db: AsyncSession, user: User, recipe: Recipe, like: bool) -> None:
    """Beğeni (tekrar beğenmek / beğenmemiş tarifi bırakmak bir şey değiştirmez)."""
    existing = await db.get(RecipeLike, (user.id, recipe.id))
    if like and existing is None:
        db.add(RecipeLike(user_id=user.id, recipe_id=recipe.id))
        recipe.like_count += 1
    elif not like and existing is not None:
        await db.delete(existing)
        recipe.like_count = max(0, recipe.like_count - 1)
    await db.commit()


async def get_recipe(db: AsyncSession, recipe_id: int) -> Recipe:
    recipe = await db.scalar(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.is_active).options(*_recipe_options())
    )
    if recipe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarif bulunamadı")
    return recipe


async def recipe_detail(db: AsyncSession, recipe: Recipe, servings: int, user_id: int | None) -> RecipeDetail:
    cost = await compute_cost(db, [(recipe, Decimal(servings) / recipe.servings)], servings, user_id)
    return RecipeDetail(
        **recipe_summary(recipe, await liked_ids(db, user_id)).model_dump(),
        steps=[s for s in recipe.steps.split("\n") if s.strip()],
        ingredients=[
            IngredientOut(name=i.name, amount_text=i.amount_text, quantity=i.quantity, unit=i.unit, is_pantry=i.is_pantry)
            for i in recipe.ingredients
        ],
        cost=cost,
    )


# --- Maliyet --------------------------------------------------------------------------------


@dataclass
class _Need:
    name: str
    unit: Unit
    search_term: str
    excludes: tuple[str, ...]
    categories: tuple[str, ...]  # izin verilen kategori slug'ları; boş = sınır yok
    is_pantry: bool
    quantity: Decimal = Decimal(0)
    recipes: list[str] = field(default_factory=list)
    names: set[str] = field(default_factory=set)  # tariflerdeki adları (normalize), "dolabımda var" için
    key: str = ""  # normalize arama ifadesi; dolaptaki artanlar bu anahtar + birimle eşleşir


@dataclass(frozen=True)
class _Pick:
    group: GroupSummary
    price: Decimal
    market_id: int | None
    packages: int
    purchase_cost: Decimal
    used_cost: Decimal
    approximate: bool


def _cheapest_market(group: GroupSummary) -> tuple[Decimal, int | None] | None:
    if not group.market_prices:
        return (group.min_price, None) if group.min_price is not None else None
    best = min(group.market_prices, key=lambda m: (m.min_price, m.market_id))
    return best.min_price, best.market_id


def _price_for(group: GroupSummary, need: _Need) -> _Pick | None:
    cheapest = _cheapest_market(group)
    if cheapest is None:
        return None
    price, market_id = cheapest
    if group.unit == need.unit and group.quantity:
        size = Decimal(group.quantity)
        packages = max(1, math.ceil(need.quantity / size))
        used = price * need.quantity / size
        approximate = False
    else:
        # Paket birimi tarifle uyuşmuyor (ör. adetle satılan ürün, gramla tarif): 1 paket say
        packages, used, approximate = 1, price, True
    return _Pick(group, price, market_id, packages, _money(price * packages), _money(used), approximate)


# Bu kategorilerdeki ürünler hiçbir tarif malzemesi olamaz (ör. "Zeytinyağlı Sıvı Sabun")
NON_FOOD_CATEGORIES = ("temizlik", "kisisel-bakim", "bebek")


async def _category_ids(db: AsyncSession) -> dict[str, int]:
    """Ana kategoriler (alt kategoriler değil): slug -> id."""
    return dict((await db.execute(select(Category.slug, Category.id).where(Category.parent_id.is_(None)))).all())


def _category_ok(group: GroupSummary, need: _Need, categories: dict[str, int]) -> bool:
    """Temizlik/bakım/bebek ürünü hiçbir zaman; malzemenin kategori listesi varsa kategorisi bilinen ürün
    o listede olmalı ("Ice Tea Limon" İçecek'te, limon Meyve & Sebze'den gelir)."""
    non_food = {categories[s] for s in NON_FOOD_CATEGORIES if s in categories}
    if group.category_id in non_food or group.subcategory_id in non_food:
        return False
    if not need.categories or group.category_id is None:
        return True
    return group.category_id in {categories[s] for s in need.categories if s in categories}


async def _groups_for(
    db: AsyncSession, term: str, need: _Need, user_id: int | None, categories: dict[str, int], cache: dict | None
) -> list[GroupSummary]:
    """Arama ifadesine uyan, malzeme olabilecek ürün grupları. cache: aynı istekte (ör. bütçeye uydururken
    planın maliyeti defalarca hesaplanır) aynı arama tekrar yapılmasın."""
    key = (term, need.excludes, need.categories, user_id)
    if cache is not None and key in cache:
        return cache[key]
    groups = [
        g for g in await search_groups(db, term, None, MATCH_CANDIDATES, user_id=user_id)
        if _category_ok(g, need, categories) and name_matches(term, g.name, need.excludes)
    ]
    if cache is not None:
        cache[key] = groups
    return groups


async def _match(
    db: AsyncSession, need: _Need, user_id: int | None, categories: dict[str, int], cache: dict | None = None
) -> _Pick | None:
    """Gereken miktarı en ucuza karşılayan grup. Ürün adı arama ifadesinin malzemesi olmalıdır
    (bkz. ingredient_match: "limon" için "Limonlu Popkek", "pul biber" için "Sivri Biber" sayılmaz);
    bulunamazsa malzeme eksik görünür. Arama ifadesi "|" ile alternatif içerebilir: "tavuk gogus|pilic gogus"."""
    picks: dict[int, _Pick] = {}
    for term in (t.strip() for t in need.search_term.split("|")):
        if not term:
            continue
        for group in await _groups_for(db, term, need, user_id, categories, cache):
            if group.id in picks:
                continue
            pick = _price_for(group, need)
            if pick is not None:
                picks[group.id] = pick
    return min(picks.values(), key=lambda p: (p.approximate, p.purchase_cost, p.used_cost), default=None)


def _need_of(ing: RecipeIngredient) -> _Need:
    excludes = tuple(normalize_text(e) for e in (ing.exclude_terms or "").split(",") if e.strip())
    categories = tuple(c.strip() for c in (ing.categories or "").split(",") if c.strip())
    return _Need(ing.name, ing.unit, ing.search_term, excludes, categories, ing.is_pantry, Decimal(ing.quantity))


def _collect_needs(uses: list[tuple[Recipe, Decimal]]) -> list[_Need]:
    needs: dict[tuple[str, Unit], _Need] = {}
    for recipe, factor in uses:
        for ing in recipe.ingredients:
            key = (normalize_text(ing.search_term), ing.unit)
            need = needs.get(key)
            if need is None:
                need = needs[key] = _need_of(ing)
                need.quantity = Decimal(0)
                need.key = key[0]
            need.quantity += Decimal(ing.quantity) * factor
            need.names.add(normalize_text(ing.name))
            if recipe.name not in need.recipes:
                need.recipes.append(recipe.name)
    return list(needs.values())


async def compute_cost(
    db: AsyncSession,
    uses: list[tuple[Recipe, Decimal]],
    portions: int,
    user_id: int | None,
    include_pantry: bool = False,
    have: set[str] | None = None,
    cache: dict | None = None,
    categories: dict[str, int] | None = None,
    stock: dict[tuple[str, Unit], Decimal] | None = None,
) -> CostOut:
    """uses: (tarif, çarpan) — çarpan = plan kişi sayısı / tarifin kişi sayısı, her öğün için ayrı.
    have: kullanıcının evde olduğunu söylediği malzemeler (normalize adlar); maliyete katılmaz.
    stock: dolaptaki artan miktarlar ((anahtar, birim) -> miktar); önce bunlar kullanılır, yalnız
    eksik kısım için paket alınır."""
    lines: list[CostLine] = []
    pantry: list[str] = []
    at_home: list[str] = []
    from_stock: list[StockUse] = []
    stock = dict(stock or {})
    if categories is None:
        categories = await _category_ids(db)
    for need in _collect_needs(uses):
        if need.is_pantry and not include_pantry:
            pantry.append(need.name)
            continue
        if have and need.names & have:
            at_home.append(need.name)
            continue
        take = min(stock.get((need.key, need.unit), Decimal(0)), need.quantity)
        if take > 0:
            stock[(need.key, need.unit)] -= take
            need.quantity -= take
            from_stock.append(StockUse(name=need.name, quantity=_qty(take), unit=need.unit))
            if need.quantity <= 0:
                continue
        pick = await _match(db, need, user_id, categories, cache)
        lines.append(
            CostLine(
                name=need.name,
                key=need.key,
                needed_quantity=_qty(need.quantity),
                unit=need.unit,
                is_pantry=need.is_pantry,
                recipes=need.recipes,
                match=None if pick is None else MatchedGroup(
                    group_id=pick.group.id,
                    name=pick.group.name,
                    quantity=pick.group.quantity,
                    unit=pick.group.unit,
                    image_url=pick.group.image_url,
                    price=pick.price,
                    market_id=pick.market_id,
                ),
                packages=pick.packages if pick else 0,
                purchase_cost=pick.purchase_cost if pick else None,
                used_cost=pick.used_cost if pick else None,
                approximate=pick.approximate if pick else False,
            )
        )
    purchase = sum((line.purchase_cost for line in lines if line.purchase_cost is not None), Decimal(0))
    used = sum((line.used_cost for line in lines if line.used_cost is not None), Decimal(0))
    return CostOut(
        purchase_total=_money(purchase),
        used_total=_money(used),
        per_serving=_money(used / portions) if portions and used else None,
        portions=portions,
        missing_count=sum(1 for line in lines if line.match is None),
        include_pantry=include_pantry,
        lines=lines,
        pantry=pantry,
        have=at_home,
        from_stock=from_stock,
        leftover_value=_money(max(purchase - used, Decimal(0))),
    )


# --- Bulunabilirlik -------------------------------------------------------------------------


async def _has_catalog(db: AsyncSession) -> bool:
    """Katalogda fiyatı olan ürün var mı? (İlk kurulumda, senkronizasyondan önce hiçbir tarif gizlenmesin.)"""
    return await db.scalar(
        select(func.count()).select_from(GroupMember).join(Product, Product.id == GroupMember.product_id)
        .where(Product.current_price.is_not(None)).limit(1)
    ) > 0


async def refresh_availability(db: AsyncSession) -> dict[str, int]:
    """Her tarifin malzemelerini uygulamadaki bütün marketlerin kataloğunda arar; bulunamayanları
    recipes.missing_ingredients'a yazar. Eksiği olan tarif planlarda ve listelerde görünmez.

    Evde var sayılan (tuz, karabiber gibi) malzemelere bakılmaz. Katalog boşsa (henüz senkronizasyon
    yapılmamış) hiçbir tarif gizlenmez. Fiyat senkronizasyonundan sonra ve API açılışında çalışır."""
    recipes = (await db.scalars(
        select(Recipe).where(Recipe.is_active).options(selectinload(Recipe.ingredients)).order_by(Recipe.id)
    )).all()
    if not await _has_catalog(db):
        for recipe in recipes:
            recipe.missing_ingredients = None
        await db.commit()
        return {"recipes": len(recipes), "hidden": 0}

    categories = await _category_ids(db)
    found: dict[tuple, bool] = {}
    hidden = 0
    for recipe in recipes:
        missing: list[str] = []
        for ing in recipe.ingredients:
            if ing.is_pantry:
                continue
            need = _need_of(ing)
            key = (normalize_text(need.search_term), need.excludes, need.categories)
            if key not in found:
                found[key] = await _match(db, need, None, categories) is not None
            if not found[key] and ing.name not in missing:
                missing.append(ing.name)
        recipe.missing_ingredients = ", ".join(missing)[:512]
        hidden += bool(missing)
    await db.commit()
    log.info("tarif bulunabilirliği: %d tariften %d tanesinin malzemesi eksik", len(recipes), hidden)
    return {"recipes": len(recipes), "hidden": hidden}


# --- Plan oluşturma -------------------------------------------------------------------------


def _plan_options():
    return (
        selectinload(MealPlan.cuisine),
        selectinload(MealPlan.entries).selectinload(MealPlanEntry.recipe).selectinload(Recipe.cuisine),
        selectinload(MealPlan.entries).selectinload(MealPlanEntry.recipe).selectinload(Recipe.ingredients),
    )


def slot_courses(slot: MealSlot, courses: list[CourseType]) -> list[CourseType]:
    """Öğünde olacak yemek türleri; plan oluştururken seçilen türlerle süzülür (ara öğün hariç)."""
    if slot is MealSlot.SNACK:
        return [CourseType.SNACK]
    return [c for c in SLOT_COURSES[slot] if c in courses]


async def _cuisine_recipes(
    db: AsyncSession, cuisines: list[Cuisine], diets: list[Diet] | None = None, avoid: list[Allergen] | None = None
) -> list[Recipe]:
    """Mutfakların, malzemesi marketlerde bulunan, diyete uyan ve kaçınılan alerjenleri içermeyen tarifleri."""
    rows = (await db.scalars(
        select(Recipe)
        .where(Recipe.cuisine_id.in_([c.id for c in cuisines]), Recipe.is_active, _available())
        .options(*_recipe_options())
        .order_by(Recipe.id)
    )).all()
    return [r for r in rows if r.suits(diets or [], avoid or [])]


async def _plan_recipes(db: AsyncSession, plan: MealPlan) -> list[Recipe]:
    return await _cuisine_recipes(db, await get_cuisines(db, plan.cuisine_slugs), plan.diet_list, plan.avoid_list)


def _pool(recipes: list[Recipe], slot: MealSlot, course: CourseType) -> list[Recipe]:
    return [r for r in recipes if r.course_type is course and slot in r.slots]


def _candidates(
    recipes: list[Recipe], slot: MealSlot, course: CourseType, main: Recipe | None = None,
    cuisine_id: int | None = None,
) -> list[Recipe]:
    """Öğüne ve türe uygun tarifler. İçecekte ana yemekle uyumlu olanlar (uyumlu yoksa hepsi); yan
    yemekte (pilav, makarna, püre) yalnızca ana yemeğe uyanlar, uyan yoksa yan yemek önerilmez.

    cuisine_id: öğünün mutfağı. Önce o mutfaktan seçilir; o mutfakta bu türden yemek yoksa tatlı ve
    içecek planın öbür mutfaklarından gelebilir (içecekte yalnız her yemeğe uyanlar), çorba, ana
    yemek, yan yemek ve salata gelmez."""
    if cuisine_id is not None:
        own = _candidates([r for r in recipes if r.cuisine_id == cuisine_id], slot, course, main)
        if own or course not in (CourseType.DESSERT, CourseType.DRINK):
            return own
        pool = [r for r in _pool(recipes, slot, course) if r.cuisine_id != cuisine_id]
        return pool if course is CourseType.DESSERT else [r for r in pool if not r.pairs_with]
    pool = _pool(recipes, slot, course)
    if course is CourseType.DRINK:
        return [r for r in pool if r.pairs(main)] or pool
    if course is CourseType.SIDE:
        return [r for r in pool if r.pairs(main)]
    return pool


def _order(slot: MealSlot, course: CourseType) -> int:
    return SLOT_ORDER[slot] * 10 + COURSE_ORDER[course]


def default_name(days: int, start: date) -> str:
    label = {1: "Günlük", 7: "Haftalık"}.get(days, f"{days} günlük")
    return f"{label} yemek planı · {start.day} {MONTHS[start.month - 1]}"


def period_of(days: int) -> PlanPeriod:
    return {1: PlanPeriod.DAILY, 7: PlanPeriod.WEEKLY}.get(days, PlanPeriod.CUSTOM)


def _meal_cuisines(recipes: list[Recipe], cuisines: list[Cuisine], slot: MealSlot, courses: list[CourseType]) -> list[int]:
    """Bu öğünü kendi başına çıkarabilen mutfaklar: öğünün ana yemeği (ara öğünde atıştırmalığı) olanlar;
    hiçbirinde yoksa menüdeki herhangi bir türden yemeği olanlar."""
    wanted = slot_courses(slot, courses)
    first = CourseType.SNACK if slot is MealSlot.SNACK else CourseType.MAIN
    with_first = [c.id for c in cuisines if first in wanted and _candidates(recipes, slot, first, cuisine_id=c.id)]
    return with_first or [c.id for c in cuisines if any(_pool([r for r in recipes if r.cuisine_id == c.id], slot, k) for k in wanted)]


# --- Kalan yemek ("bir pişir iki ye") ---------------------------------------------------------

# Ertesi güne kalan yemek türleri; salata, tatlı ve içecek her öğünde taze
LEFTOVER_COURSES = (CourseType.SOUP, CourseType.MAIN, CourseType.SIDE)


def _source(entry: MealPlanEntry) -> MealPlanEntry | None:
    """Yeni (henüz kaydedilmemiş) kayıtlarda ilişki bellekte; yüklenmiş kayıtlarda yalnız id var."""
    return entry.__dict__.get("leftover_of")


def is_leftover(entry: MealPlanEntry) -> bool:
    return entry.leftover_of_id is not None or _source(entry) is not None


def _children(plan: MealPlan, entry: MealPlanEntry) -> list[MealPlanEntry]:
    """Bu yemekten kalan (ertesi güne aktarılan) kayıtlar."""
    return [
        e for e in plan.entries
        if e is not entry and (_source(e) is entry or (entry.id is not None and e.leftover_of_id == entry.id))
    ]


def _detach(entry: MealPlanEntry) -> None:
    """Kalan yemek artık ayrıca pişirilecek (kaynağı değişti, silindi ya da kullanıcı değiştirdi)."""
    entry.leftover_of_id = None
    if "leftover_of" in entry.__dict__:
        entry.leftover_of = None


# --- Tercihler: az israf, dolabımda olanlar, bütçe ------------------------------------------


def _terms(recipe: Recipe) -> set[str]:
    """Tarifin alınması gereken (evde var sayılmayan) malzemeleri, arama ifadesiyle."""
    return {normalize_text(i.search_term) for i in recipe.ingredients if not i.is_pantry}


def have_set(names: list[str]) -> set[str]:
    return {normalize_text(n) for n in names if n.strip()}


class _Prefs:
    """Aynı sayıda kullanılmış tarifler arasında seçimi yönlendirir (çeşitlilik her zaman önce gelir):

    - low_waste: plandaki yemeklerle ortak malzemesi olan tarif öne çıkar (yarım kalan maydanoz,
      yoğurt, peynir başka yemekte kullanılsın);
    - have: kullanıcının evde olduğunu söylediği malzemeleri kullanan tarif öne çıkar;
    - prices: bütçe varsa ucuz tarif öne çıkar."""

    def __init__(
        self, recipes: list[Recipe], low_waste: bool, have: set[str], prices: dict[int, Decimal] | None,
        stock_terms: set[str] | None = None,
    ):
        self.terms = {r.id: _terms(r) for r in recipes}
        # Dolapta olanlar: kullanıcının seçtikleri + önceki alışverişlerden artanlar
        self.have_terms = {
            normalize_text(i.search_term) for r in recipes for i in r.ingredients
            if not i.is_pantry and normalize_text(i.name) in have
        } | (stock_terms or set())
        self.low_waste = low_waste
        self.prices = prices
        self.bought: Counter = Counter()

    @property
    def active(self) -> bool:
        return self.low_waste or bool(self.have_terms) or self.prices is not None

    def add(self, recipe: Recipe) -> None:
        self.bought.update(self.terms.get(recipe.id, set()))

    def bonus(self, recipe: Recipe, pool: list[Recipe]) -> float:
        terms = self.terms.get(recipe.id, set())
        b = 0.0
        if self.low_waste:
            b += 0.3 * sum(1 for t in terms if self.bought[t])
        if self.have_terms:
            b += 0.45 * len(terms & self.have_terms)
        if self.prices:
            costs = [self.prices.get(r.id, Decimal(0)) for r in pool]
            low, high = min(costs), max(costs)
            if high > low:
                b -= 0.6 * float((self.prices.get(recipe.id, low) - low) / (high - low))
        # Bir yemek fazla kullanılmış olmayı hiçbir zaman telafi etmesin
        return max(min(b, 0.9), -0.9)


def _choose(
    candidates: list[Recipe], usage: Counter, today: set[int], yesterday: set[int], rng: random.Random,
    exclude: int | None = None, prefs: _Prefs | None = None,
) -> Recipe:
    """Çeşitlilik: aynı gün tekrar etmesin, mümkünse dünkü yemekler gelmesin, en az kullanılan önce;
    eşitlerde tercihler (az israf, dolaptakiler, bütçe), sonra sevilen tarif (puanı yüksek) daha büyük
    olasılıkla seçilir."""
    pool = [r for r in candidates if r.id != exclude] or candidates

    def key(r: Recipe):
        bonus = prefs.bonus(r, pool) if prefs is not None and prefs.active else 0.0
        return (r.id in today, r.id in yesterday, usage[r.id] - bonus, -rng.random() * (r.score + 10))

    return min(pool, key=key)


# --- Plan oluşturma -------------------------------------------------------------------------


async def create_plan(
    db: AsyncSession, user: User, *, period: PlanPeriod, cuisine_slugs: list[str], servings: int,
    slots: list[MealSlot], courses: list[CourseType], start: date | None, name: str | None,
    diets: list[Diet] | None = None, avoid: list[Allergen] | None = None, rng: random.Random | None = None,
    days: int | None = None, weekdays: list[int] | None = None, budget: Decimal | None = None,
    leftovers: bool = False, low_waste: bool = False, have: list[str] | None = None,
) -> tuple[MealPlan, int]:
    """Planı oluşturur; (plan, bütçe için değiştirilen yemek sayısı) döner."""
    rng = rng or random.Random()
    days = days or PERIOD_DAYS.get(period, 7)
    cuisines = await get_cuisines(db, cuisine_slugs)
    slots = sorted(set(slots), key=SLOT_ORDER.__getitem__)
    courses = sorted(set(courses), key=COURSE_ORDER.__getitem__)
    diets = sorted(set(diets or []), key=list(Diet).index)
    avoid = sorted(set(avoid or []), key=list(Allergen).index)
    weekdays = sorted(set(weekdays or []))
    if len(weekdays) == 7:
        weekdays = []
    have = list(dict.fromkeys(h.strip() for h in (have or []) if h.strip()))
    recipes = await _cuisine_recipes(db, cuisines, diets, avoid)
    menu = {slot: [c for c in slot_courses(slot, courses) if _pool(recipes, slot, c)] for slot in slots}
    if not any(menu.values()):
        names = ", ".join(c.name for c in cuisines)
        detail = f"{names} için seçilen öğünlere uygun tarif yok"
        if diets or avoid:
            detail += " (diyet ve alerji seçimlerinize uyan)"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)
    start = start or date.today()
    active_days = [d for d in range(days) if not weekdays or (start + timedelta(days=d)).weekday() in weekdays]
    if not active_days:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Seçilen günler plan süresine denk gelmiyor")
    # Hangi öğünü hangi mutfaklar çıkarabilir (ör. kahvaltılığı olmayan mutfak kahvaltıya gelmez)
    able = {slot: _meal_cuisines(recipes, cuisines, slot, courses) for slot in slots}
    have_names = have_set(have)
    cache: dict = {}
    categories = await _category_ids(db)
    prices = None
    if budget is not None:
        prices = {r.id: await _estimate(db, r, servings, user.id, have_names, cache, categories) for r in recipes}
    await remember_have(db, user, have_names)
    stock = await load_stock(db, user.id)
    prefs = _Prefs(recipes, low_waste, have_names, prices, {key for key, _ in stock})
    by_id = {r.id: r for r in recipes}

    plan = MealPlan(
        user_id=user.id,
        name=name or default_name(days, start),
        period=period_of(days),
        days=days,
        weekdays=",".join(str(d) for d in weekdays),
        budget=budget,
        leftovers=leftovers,
        low_waste=low_waste,
        have_items="|".join(have),
        cuisine_id=cuisines[0].id,
        cuisines=",".join(c.slug for c in cuisines),
        start_date=start,
        servings=servings,
        meal_slots=",".join(s.value for s in slots),
        courses=",".join(c.value for c in courses),
        diets=",".join(d.value for d in diets),
        avoid_allergens=",".join(a.value for a in avoid),
    )
    usage: Counter = Counter()
    cuisine_usage: Counter = Counter()  # mutfaklar öğünlere dengeli dağılsın
    yesterday: set[int] = set()
    # (gün, öğün) -> o öğüne kalan yemekler (önceki akşamın çorba / ana / yan yemeği)
    carry: dict[tuple[int, MealSlot], list[MealPlanEntry]] = {}
    leftover_slot = MealSlot.LUNCH if MealSlot.LUNCH in slots else MealSlot.DINNER
    for day in active_days:
        today: set[int] = set()
        today_cuisines: set[int] = set()
        for slot in slots:
            main = None
            cuisine_id = None
            carried = carry.pop((day, slot), [])
            for src in carried:
                recipe = by_id[src.recipe_id]
                plan.entries.append(MealPlanEntry(
                    day_index=day, slot=slot, course=src.course, slot_order=_order(slot, src.course),
                    recipe_id=recipe.id, leftover_of=src,
                ))
                today.add(recipe.id)
                cuisine_id = recipe.cuisine_id
                if src.course is CourseType.MAIN:
                    main = recipe
            if not carried and able[slot]:
                # En az kullanılan mutfak; eşitse bugün henüz gelmemiş olan, sonra rastgele
                cuisine_id = min(able[slot], key=lambda c: (cuisine_usage[c], c in today_cuisines, rng.random()))
                cuisine_usage[cuisine_id] += 1
                today_cuisines.add(cuisine_id)
            made: list[MealPlanEntry] = []
            for course in menu[slot]:
                if any(e.course is course for e in carried):
                    continue
                candidates = _candidates(recipes, slot, course, main, cuisine_id)
                if not candidates:  # ör. mantının yanına pilav önerilmez
                    continue
                recipe = _choose(candidates, usage, today, yesterday, rng, prefs=prefs)
                if course is CourseType.MAIN:
                    main = recipe
                usage[recipe.id] += 1
                today.add(recipe.id)
                prefs.add(recipe)
                entry = MealPlanEntry(day_index=day, slot=slot, course=course, slot_order=_order(slot, course), recipe_id=recipe.id)
                plan.entries.append(entry)
                made.append(entry)
            # Bir pişir iki ye: akşam yemeği (kendisi kalan değilse) ertesi gün öğlene kalır; planda
            # öğle yoksa ertesi akşama (iki günde bir pişirilir). Ertesi gün planda değilse kalmaz.
            if leftovers and slot is MealSlot.DINNER and not carried and day + 1 in active_days:
                keep = [e for e in made if e.course in LEFTOVER_COURSES]
                if any(e.course is CourseType.MAIN for e in keep):
                    carry[(day + 1, leftover_slot)] = keep
        yesterday = today

    swaps = 0
    if budget is not None:
        swaps = await _fit_budget(db, plan, recipes, budget, prices, user.id, have_names, cache, categories, rng)
    db.add(plan)
    await db.commit()
    return await get_plan(db, user, plan.id), swaps


async def _estimate(
    db: AsyncSession, recipe: Recipe, servings: int, user_id: int, have: set[str], cache: dict,
    categories: dict[str, int],
) -> Decimal:
    """Tarifin plan kişi sayısı için kullanılan malzeme değeri (bütçe karşılaştırması için). Fiyatı
    bulunamayan malzeme bedava sayılmasın: bulunanların ortalaması kadar eklenir."""
    cost = await compute_cost(
        db, [(recipe, Decimal(servings) / recipe.servings)], 1, user_id, have=have, cache=cache, categories=categories
    )
    priced = [line.used_cost for line in cost.lines if line.used_cost is not None]
    average = sum(priced, Decimal(0)) / len(priced) if priced else MISSING_PRICE
    return cost.used_total + average * cost.missing_count


# Hiçbir malzemesinin fiyatı bulunamayan tarifte eksik malzeme başına varsayılan değer (TL)
MISSING_PRICE = Decimal(40)


# Bütçeye uydurmak için en fazla bu kadar adım (her adımda bir yemek değişir ya da çıkar)
MAX_BUDGET_STEPS = 40
# Bütçe yetmiyorsa çıkarılabilecek "olmasa da olur" yemekler, önce bunlar
OPTIONAL_COURSES = (CourseType.DRINK, CourseType.DESSERT, CourseType.SALAD, CourseType.SOUP)


async def _fit_budget(
    db: AsyncSession, plan: MealPlan, recipes: list[Recipe], budget: Decimal, prices: dict[int, Decimal],
    user_id: int, have: set[str], cache: dict, categories: dict[str, int], rng: random.Random,
) -> int:
    """Alışveriş tutarı bütçeyi aşıyorsa en pahalı yemekler aynı öğüne uygun daha ucuz bir tarifle
    değiştirilir (kalanları da onu izler). Ucuzu kalmadıysa içecek, tatlı, salata, çorba çıkarılır.
    Ana yemek hiç çıkarılmaz; bütçe yine de yetmezse plan olduğu gibi kalır (ekranda aşım görünür)."""
    by_id = {r.id: r for r in recipes}

    async def total() -> Decimal:
        uses = [(by_id[e.recipe_id], Decimal(plan.servings) / by_id[e.recipe_id].servings) for e in plan.entries]
        cost = await compute_cost(db, uses, 1, user_id, have=have, cache=cache, categories=categories)
        return cost.purchase_total

    steps = 0
    tried: set[int] = set()
    current = await total()
    while current > budget and steps < MAX_BUDGET_STEPS:
        open_entries = [e for e in plan.entries if not is_leftover(e) and id(e) not in tried]
        if not open_entries:
            break
        entry = max(open_entries, key=lambda e: prices.get(e.recipe_id, Decimal(0)) * (1 + len(_children(plan, e))))
        price = prices.get(entry.recipe_id, Decimal(0))
        main = None if entry.course is CourseType.MAIN else _main_of(plan, entry.day_index, entry.slot, by_id)
        pool = _candidates(recipes, entry.slot, entry.course, main, by_id[entry.recipe_id].cuisine_id)
        cheaper = [r for r in pool if r.id != entry.recipe_id and prices.get(r.id, Decimal(0)) < price]
        if cheaper:
            today = {e.recipe_id for e in plan.entries if e.day_index == entry.day_index}
            usage = Counter(e.recipe_id for e in plan.entries)
            new = min(cheaper, key=lambda r: (r.id in today, usage[r.id], prices.get(r.id, Decimal(0)), rng.random()))
            for e in [entry, *_children(plan, entry)]:
                e.recipe_id = new.id
                if e.course is CourseType.MAIN:
                    _repair_companions(plan, recipes, e, new, rng)
        elif entry.course in OPTIONAL_COURSES:
            for e in _children(plan, entry):
                plan.entries.remove(e)
            plan.entries.remove(entry)
        else:
            tried.add(id(entry))  # bundan ucuzu yok ve çıkarılamaz (ana / yan yemek)
            continue
        steps += 1
        current = await total()
    return steps


async def get_plan(db: AsyncSession, user: User, plan_id: int) -> MealPlan:
    plan = await db.scalar(
        select(MealPlan)
        .where(MealPlan.id == plan_id, MealPlan.user_id == user.id)
        .options(*_plan_options())
        .execution_options(populate_existing=True)
    )
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yemek planı bulunamadı")
    return plan


async def list_plans(db: AsyncSession, user: User) -> list[MealPlanSummary]:
    plans = (await db.scalars(
        select(MealPlan)
        .where(MealPlan.user_id == user.id)
        .options(selectinload(MealPlan.cuisine), selectinload(MealPlan.entries))
        .order_by(MealPlan.created_at.desc(), MealPlan.id.desc())
    )).all()
    return [to_summary(p) for p in plans]


def _meal_entries(plan: MealPlan, day: int, slot: MealSlot) -> list[MealPlanEntry]:
    return [e for e in plan.entries if e.day_index == day and e.slot is slot]


def _main_of(plan: MealPlan, day: int, slot: MealSlot, recipes: dict[int, Recipe]) -> Recipe | None:
    main = next((e for e in _meal_entries(plan, day, slot) if e.course is CourseType.MAIN), None)
    return recipes.get(main.recipe_id) if main else None


def _meal_cuisine(plan: MealPlan, day: int, slot: MealSlot, skip_entry: MealPlanEntry | None) -> int | None:
    """Öğünün mutfağı: ana yemeğinin (yoksa öğündeki başka bir yemeğin) mutfağı."""
    meal = sorted(_meal_entries(plan, day, slot), key=lambda e: (e.course is not CourseType.MAIN, e is skip_entry))
    for e in meal:
        recipe = e.__dict__.get("recipe")  # yeni eklenen kayıtta ilişki yüklü değil
        if recipe is not None:
            return recipe.cuisine_id
    return None


def _suggest(
    plan: MealPlan, recipes: list[Recipe], day: int, slot: MealSlot, course: CourseType,
    rng: random.Random, skip_entry: MealPlanEntry | None = None,
) -> Recipe | None:
    """Öğünün mutfağından öneri (İtalyan öğüne İtalyan tatlı); o mutfakta yoksa planın öbür mutfaklarından."""
    by_id = {r.id: r for r in recipes}
    others = [e for e in plan.entries if e is not skip_entry]
    main = _main_of(plan, day, slot, by_id)
    cuisine_id = main.cuisine_id if main is not None else _meal_cuisine(plan, day, slot, skip_entry)
    pool = _candidates(recipes, slot, course, main, cuisine_id)
    if not pool and cuisine_id is not None and course is not CourseType.SIDE:
        pool = _candidates(recipes, slot, course, main)
    if not pool:
        return None
    usage = Counter(e.recipe_id for e in others)
    today = {e.recipe_id for e in others if e.day_index == day}
    around = {e.recipe_id for e in others if abs(e.day_index - day) == 1}
    prefs = None
    if plan.low_waste or plan.have_list:
        prefs = _Prefs(recipes, plan.low_waste, have_set(plan.have_list), None)
        for e in others:
            if e.recipe_id in by_id:
                prefs.add(by_id[e.recipe_id])
    return _choose(pool, usage, today, around, rng, exclude=skip_entry.recipe_id if skip_entry else None, prefs=prefs)


async def change_entry(
    db: AsyncSession, user: User, plan: MealPlan, entry_id: int, recipe_id: int | None,
    rng: random.Random | None = None,
) -> None:
    rng = rng or random.Random()
    entry = _get_entry(plan, entry_id)
    recipes = await _plan_recipes(db, plan)
    if recipe_id is not None:
        recipe = await get_recipe(db, recipe_id)
    else:
        # "Başka öner": aynı mutfaktan bu öğüne ve türe uygun, şu ankinden farklı bir yemek
        recipe = _suggest(plan, recipes, entry.day_index, entry.slot, entry.course, rng, skip_entry=entry)
        if recipe is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bu öğün için başka tarif yok")
    # Kalan yemeği değiştiren kullanıcı o öğünde ayrıca pişirecek; pişen yemek değişince kalanı da değişir
    targets = [entry] if is_leftover(entry) else [entry, *_children(plan, entry)]
    if is_leftover(entry):
        _detach(entry)
    for e in targets:
        e.recipe_id = recipe.id
        if e.course is CourseType.MAIN:
            _repair_companions(plan, recipes, e, recipe, rng)
    await db.commit()


def _repair_companions(
    plan: MealPlan, recipes: list[Recipe], main_entry: MealPlanEntry, main: Recipe, rng: random.Random
) -> None:
    """Ana yemek değişti: içecek uyumlu değilse uyumlu biri seçilir; yan yemek (pilav, püre) yeni ana
    yemeğe uymuyorsa uyan biriyle değişir, hiçbiri uymuyorsa kaldırılır (mantının yanına pilav olmaz).
    Plan menüsünde yan yemek varsa ve öğünde yoksa uyan biri eklenir."""
    by_id = {r.id: r for r in recipes}
    day, slot = main_entry.day_index, main_entry.slot
    meal = _meal_entries(plan, day, slot)
    drink = next((e for e in meal if e.course is CourseType.DRINK), None)
    if drink is not None and drink.recipe_id in by_id and not by_id[drink.recipe_id].pairs(main):
        new_drink = _suggest(plan, recipes, day, slot, CourseType.DRINK, rng, skip_entry=drink)
        if new_drink is not None:
            drink.recipe_id = new_drink.id
    side = next((e for e in meal if e.course is CourseType.SIDE), None)
    current = by_id.get(side.recipe_id) if side is not None else None
    if side is not None and (current is None or not current.pairs(main)):
        new_side = _suggest(plan, recipes, day, slot, CourseType.SIDE, rng, skip_entry=side)
        if new_side is None:
            plan.entries.remove(side)
        else:
            side.recipe_id = new_side.id
    elif side is None and CourseType.SIDE in plan.course_list and slot is not MealSlot.SNACK:
        new_side = _suggest(plan, recipes, day, slot, CourseType.SIDE, rng)
        if new_side is not None:
            plan.entries.append(MealPlanEntry(
                day_index=day, slot=slot, course=CourseType.SIDE, slot_order=_order(slot, CourseType.SIDE),
                recipe_id=new_side.id,
            ))


def _get_entry(plan: MealPlan, entry_id: int) -> MealPlanEntry:
    entry = next((e for e in plan.entries if e.id == entry_id), None)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Öğün bulunamadı")
    return entry


async def remove_entry(db: AsyncSession, plan: MealPlan, entry_id: int) -> None:
    """Kullanıcı o öğünde bu yemeği istemiyor (ör. çorba): plandan ve maliyetten çıkar. Kalanı
    planlanmış bir yemek kaldırılırsa kalanlar o gün ayrıca pişirilir."""
    entry = _get_entry(plan, entry_id)
    for child in _children(plan, entry):
        _detach(child)
    plan.entries.remove(entry)
    await db.commit()


async def add_entry(
    db: AsyncSession, plan: MealPlan, day: int, slot: MealSlot, course: CourseType, recipe_id: int | None,
    rng: random.Random | None = None,
) -> None:
    """Kaldırılan bir yemek türünü (ya da yeni bir öğünü) geri ekle; tarif verilmezse önerilir."""
    if day >= plan.days:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Plan bu günü kapsamıyor")
    if course not in slot_courses(slot, list(CourseType)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bu öğüne bu yemek türü eklenemez")
    if any(e.course is course for e in _meal_entries(plan, day, slot)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu öğünde bu türden bir yemek zaten var")
    if recipe_id is not None:
        recipe = await get_recipe(db, recipe_id)
    else:
        recipe = _suggest(plan, await _plan_recipes(db, plan), day, slot, course, rng or random.Random())
        if recipe is None:
            detail = "Bu öğün için uygun tarif yok"
            if course is CourseType.SIDE:
                detail = "Bu ana yemeğin yanına uygun bir pilav, makarna ya da püre yok"
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)
    plan.entries.append(
        MealPlanEntry(day_index=day, slot=slot, course=course, slot_order=_order(slot, course), recipe_id=recipe.id)
    )
    await db.commit()


def _uses(plan: MealPlan) -> list[tuple[Recipe, Decimal]]:
    """Kalan yemekler de sayılır: kaynağı iki kat pişirildiği için malzeme miktarı aynıdır."""
    return [(e.recipe, Decimal(plan.servings) / e.recipe.servings) for e in plan.entries]


def meal_count(plan: MealPlan) -> int:
    """Öğün sayısı (gün x öğün); bir öğündeki çorba, ana yemek, tatlı... tek öğün sayılır."""
    return len({(e.day_index, e.slot) for e in plan.entries})


async def plan_cost(db: AsyncSession, plan: MealPlan, user_id: int, include_pantry: bool = False) -> CostOut:
    """Listeye aktarılmamış plan dolabın güncel hâlini kullanır; aktarılmış plan, aktarıldığı anda
    dolaptan ne kullandıysa onu (yoksa kendi artanlarını kendi maliyetinden düşerdi)."""
    if plan.stock_used is not None:
        stock = {(u["key"], Unit(u["unit"])): Decimal(u["quantity"]) for u in json.loads(plan.stock_used)}
    else:
        stock = await load_stock(db, user_id)
    return await compute_cost(
        db, _uses(plan), meal_count(plan) * plan.servings, user_id, include_pantry, have=have_set(plan.have_list),
        stock=stock,
    )


# --- Dolap: alınan paketlerden artanlar -----------------------------------------------------

# Ana kategoriye göre açılmış paketin buzdolabında dayanacağı gün; listede olmayanlar (bakliyat, un,
# yağ, baharat, konserve) bozulmaz sayılır
SHELF_DAYS = {"et-tavuk-balik": 2, "firin": 3, "meyve-sebze": 7, "sut-kahvaltilik": 7}


def shelf_life(categories: tuple[str, ...]) -> int | None:
    days = [SHELF_DAYS[c] for c in categories if c in SHELF_DAYS]
    return min(days) if days else None


async def _pantry_rows(db: AsyncSession, user_id: int) -> list[PantryItem]:
    """Kullanıcının dolabı; son kullanma günü geçenler silinir."""
    rows = (await db.scalars(
        select(PantryItem).where(PantryItem.user_id == user_id).order_by(PantryItem.name)
    )).all()
    today = date.today()
    fresh = []
    for row in rows:
        if row.expires_on is not None and row.expires_on < today or (row.quantity is not None and row.quantity <= 0):
            await db.delete(row)
        else:
            fresh.append(row)
    if len(fresh) != len(rows):
        await db.commit()
    return fresh


async def load_stock(db: AsyncSession, user_id: int | None) -> dict[tuple[str, Unit], Decimal]:
    if user_id is None:
        return {}
    # Miktarı belirsiz olan ("dolabımda var" diye seçilen) gereken her miktarı karşılar
    return {
        (r.key, r.unit): Decimal(r.quantity) if r.quantity is not None else UNLIMITED
        for r in await _pantry_rows(db, user_id)
    }


UNLIMITED = Decimal("Infinity")


async def remember_have(db: AsyncSession, user: User, have: set[str]) -> None:
    """"Dolabımda ne var"da seçilen malzemeler Dolabım'a miktarsız ("var") yazılır; dolapta miktarıyla
    zaten varsa dokunulmaz. Bozulabilenlere bugünden itibaren dayanma süresi verilir."""
    if not have:
        return
    rows = {(r.key, r.unit): r for r in await _pantry_rows(db, user.id)}
    today = date.today()
    ingredients = (await db.scalars(select(RecipeIngredient).where(RecipeIngredient.is_pantry.is_(False)))).all()
    for ing in ingredients:
        if normalize_text(ing.name) not in have:
            continue
        need = _need_of(ing)
        key = (normalize_text(ing.search_term), ing.unit)
        if key in rows:
            continue
        days = shelf_life(need.categories)
        rows[key] = PantryItem(
            user_id=user.id, key=key[0], name=ing.name, quantity=None, unit=ing.unit,
            expires_on=today + timedelta(days=days) if days is not None else None,
        )
        db.add(rows[key])


async def pantry(db: AsyncSession, user: User) -> list[PantryItemOut]:
    return [
        PantryItemOut(id=r.id, name=r.name, quantity=r.quantity, unit=r.unit, expires_on=r.expires_on)
        for r in await _pantry_rows(db, user.id)
    ]


async def update_pantry_item(db: AsyncSession, user: User, item_id: int, quantity: Decimal | None) -> None:
    """Miktarı düzelt; 0 ya da None = dolaptan çıkar."""
    row = await db.scalar(select(PantryItem).where(PantryItem.id == item_id, PantryItem.user_id == user.id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dolapta böyle bir malzeme yok")
    if not quantity:
        await db.delete(row)
    else:
        row.quantity = quantity
    await db.commit()


async def _record_stock(db: AsyncSession, user: User, plan: MealPlan, cost: CostOut) -> list[StockUse]:
    """Plan ilk kez listeye aktarılırken: dolaptan kullanılanlar düşülür, alınacak paketlerden artanlar
    (ör. 500 g'lık paketten 200 g kullanılırsa 300 g) son kullanma günüyle dolaba eklenir. Planın dolaptan
    kullandıkları planda saklanır ki maliyeti sonra değişmesin. Tekrar aktarmada dolap değişmez."""
    needs = {(n.key, n.unit): n for n in _collect_needs(_uses(plan))}
    rows = {(r.key, r.unit): r for r in await _pantry_rows(db, user.id)}
    used = []
    for use in cost.from_stock:
        need = next((n for n in needs.values() if n.name == use.name and n.unit is use.unit), None)
        if need is None:
            continue
        used.append({"key": need.key, "unit": need.unit.value, "quantity": str(use.quantity), "name": use.name})
        row = rows.get((need.key, need.unit))
        if row is not None and row.quantity is not None:  # miktarı belirsiz ("var") olan düşülmez
            row.quantity = max(Decimal(0), Decimal(row.quantity) - use.quantity)
    plan.stock_used = json.dumps(used, ensure_ascii=False)

    stored: list[StockUse] = []
    today = date.today()
    for line in cost.lines:
        m = line.match
        if m is None or line.approximate or m.unit != line.unit or not m.quantity:
            continue
        extra = Decimal(m.quantity) * line.packages - Decimal(line.needed_quantity)
        if extra <= 0:
            continue
        need = needs.get((line.key, line.unit))
        days = shelf_life(need.categories) if need else None
        expires = today + timedelta(days=days + plan_span(plan)) if days is not None else None
        row = rows.get((line.key, line.unit))
        if row is None:
            row = rows[(line.key, line.unit)] = PantryItem(
                user_id=user.id, key=line.key, name=line.name, quantity=Decimal(0), unit=line.unit, expires_on=expires,
            )
            db.add(row)
        elif expires is not None and (row.expires_on is None or expires < row.expires_on):
            row.expires_on = expires
        if row.quantity is not None:
            row.quantity = Decimal(row.quantity) + extra
            stored.append(StockUse(name=line.name, quantity=_qty(extra), unit=line.unit))
    # Biten malzemeler en sonda silinir: aynı malzeme hem bitip hem yeni paketten artabilir; silip
    # yeniden eklemek aynı (kullanıcı, malzeme, birim) satırını iki kez yazmaya çalışırdı
    for row in rows.values():
        if row.quantity is not None and row.quantity <= 0 and row.id is not None:
            await db.delete(row)
    return stored


def plan_span(plan: MealPlan) -> int:
    """Planın bugünden sonra kaç gün süreceği (artan malzeme plan bitene kadar da kullanılabilir)."""
    end = plan.start_date + timedelta(days=plan.days - 1)
    return max(0, (end - date.today()).days)


def to_summary(plan: MealPlan) -> MealPlanSummary:
    return MealPlanSummary(
        id=plan.id,
        name=plan.name,
        period=plan.period,
        cuisine=plan.cuisine.slug,
        cuisines=plan.cuisine_slugs,
        start_date=plan.start_date,
        days=plan.days,
        servings=plan.servings,
        meal_slots=plan.slots,
        courses=plan.course_list,
        diets=plan.diet_list,
        avoid_allergens=plan.avoid_list,
        entry_count=meal_count(plan),
        weekdays=plan.weekday_list,
        budget=plan.budget,
        leftovers=plan.leftovers,
        low_waste=plan.low_waste,
        have=plan.have_list,
        exported_list_id=plan.exported_list_id,
        created_at=plan.created_at,
    )


def daily_nutrition(plan: MealPlan) -> Nutrition | None:
    """Kişi başı günlük ortalama (plandaki bütün yemekler; besin değeri olmayanlar hariç). Yemek
    yapılmayan günler (ör. hafta sonu seçilmediyse) ortalamaya girmez."""
    known = [e.recipe for e in plan.entries if e.recipe.kcal is not None]
    if not known:
        return None
    days = len({e.day_index for e in plan.entries}) or 1
    return Nutrition(
        kcal=round(sum(r.kcal for r in known) / days),
        protein_g=round(sum(r.protein_g or 0 for r in known) / days),
        carbs_g=round(sum(r.carbs_g or 0 for r in known) / days),
        fat_g=round(sum(r.fat_g or 0 for r in known) / days),
    )


async def to_detail(
    db: AsyncSession, plan: MealPlan, user_id: int, include_pantry: bool = False, swaps: int = 0
) -> MealPlanDetail:
    liked = await liked_ids(db, user_id)
    cost = await plan_cost(db, plan, user_id, include_pantry)
    budget = None
    if plan.budget is not None:
        budget = BudgetOut(
            budget=plan.budget, total=cost.purchase_total, within=cost.purchase_total <= plan.budget, swaps=swaps
        )
    return MealPlanDetail(
        **to_summary(plan).model_dump(),
        entries=[
            MealPlanEntryOut(
                id=e.id,
                day_index=e.day_index,
                date=plan.start_date + timedelta(days=e.day_index),
                slot=e.slot,
                course=e.course,
                recipe=recipe_summary(e.recipe, liked),
                leftover_of=e.leftover_of_id,
                leftover_for=[c.id for c in plan.entries if c.leftover_of_id == e.id],
            )
            for e in sorted(plan.entries, key=lambda e: (e.day_index, e.slot_order))
        ],
        daily_nutrition=daily_nutrition(plan),
        cost=cost,
        budget_status=budget,
    )


# --- Alışveriş listesine aktarma ------------------------------------------------------------


async def export_to_list(
    db: AsyncSession, user: User, plan: MealPlan, *, list_id: int | None, list_name: str | None, include_pantry: bool
) -> tuple[ShoppingList, int, list[str], list[StockUse]]:
    """Malzemeler (bulunan ürün grupları, paket adediyle) listeye eklenir. Grup listede zaten
    varsa yeni kalem açılmaz, miktarı artar (elle ürün eklemekle aynı kural)."""
    cost = await plan_cost(db, plan, user.id, include_pantry)
    stored: list[StockUse] = []
    if plan.stock_used is None:
        stored = await _record_stock(db, user, plan, cost)
    if list_id is not None:
        shopping_list = await list_svc.get_owned_list(db, user, list_id, editable=True)
    else:
        new_list = ShoppingList(user_id=user.id, name=list_name or plan.name, icon="🍲")
        db.add(new_list)
        await db.flush()
        shopping_list = await list_svc.get_owned_list(db, user, new_list.id)

    packages: dict[int, int] = defaultdict(int)
    for line in cost.lines:
        if line.match is not None:
            packages[line.match.group_id] += line.packages
    next_position = max((i.position for i in shopping_list.items), default=-1) + 1
    for group_id, count in packages.items():
        existing = next((i for i in shopping_list.items if i.group_id == group_id), None)
        if existing is not None:
            existing.quantity = min(existing.quantity + count, Decimal(999))
            continue
        shopping_list.items.append(
            ShoppingListItem(
                group_id=group_id,
                quantity=Decimal(min(count, 999)),
                position=next_position,
                note="Yemek planı",
                added_by_user_id=user.id,
            )
        )
        next_position += 1
    if packages:
        list_svc.reset_plan(shopping_list)
    plan.exported_list_id = shopping_list.id
    await db.commit()
    skipped = [line.name for line in cost.lines if line.match is None]
    return shopping_list, len(packages), skipped, stored
