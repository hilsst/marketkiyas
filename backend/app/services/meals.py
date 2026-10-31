"""Yemek planlayıcı: plan oluşturma, malzeme maliyeti ve alışveriş listesine aktarma.

Maliyet: plandaki her yemeğin malzemeleri kişi sayısına göre orantılanıp toplanır (aynı malzeme
farklı yemeklerde geçiyorsa birleşir). Her malzeme için katalogda arama yapılır ve kullanıcının
şubelerinde (seçmediyse zincir genelinde) gereken miktarı en ucuza karşılayan ürün grubu seçilir.

Mutfaklar: bir plan birden çok mutfaktan (Türk, İtalyan, Uzak Doğu...) oluşabilir. Her öğün tek bir
mutfaktan gelir (spagettinin yanına ayran gelmesin), mutfaklar öğünlere dengeli dağıtılır.

Bulunabilirlik: malzemelerinden biri uygulamadaki marketlerin hiçbirinde bulunamayan tarif (ör. nori
yosunu, mascarpone) planlarda ve tarif listesinde yer almaz; bkz. refresh_availability.
"""

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
    CostLine,
    CostOut,
    CuisineOut,
    IngredientOut,
    MatchedGroup,
    MealPlanDetail,
    MealPlanEntryOut,
    MealPlanSummary,
    Nutrition,
    RecipeDetail,
    RecipeSummary,
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
PERIOD_DAYS = {PlanPeriod.DAILY: 1, PlanPeriod.WEEKLY: 7}
# Bir malzeme için değerlendirilecek arama sonucu sayısı
MATCH_CANDIDATES = 50
CENT = Decimal("0.01")
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


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
) -> list[RecipeSummary]:
    """En sevilenler önce (başlangıç puanı + kullanıcı beğenileri)."""
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
    return [recipe_summary(r, liked) for r in recipes]


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


async def _match(db: AsyncSession, need: _Need, user_id: int | None, categories: dict[str, int]) -> _Pick | None:
    """Gereken miktarı en ucuza karşılayan grup. Ürün adı arama ifadesinin malzemesi olmalıdır
    (bkz. ingredient_match: "limon" için "Limonlu Popkek", "pul biber" için "Sivri Biber" sayılmaz);
    bulunamazsa malzeme eksik görünür. Arama ifadesi "|" ile alternatif içerebilir: "tavuk gogus|pilic gogus"."""
    picks: dict[int, _Pick] = {}
    for term in (t.strip() for t in need.search_term.split("|")):
        if not term:
            continue
        for group in await search_groups(db, term, None, MATCH_CANDIDATES, user_id=user_id):
            if group.id in picks or not _category_ok(group, need, categories):
                continue
            if not name_matches(term, group.name, need.excludes):
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
            need.quantity += Decimal(ing.quantity) * factor
            if recipe.name not in need.recipes:
                need.recipes.append(recipe.name)
    return list(needs.values())


async def compute_cost(
    db: AsyncSession,
    uses: list[tuple[Recipe, Decimal]],
    portions: int,
    user_id: int | None,
    include_pantry: bool = False,
) -> CostOut:
    """uses: (tarif, çarpan) — çarpan = plan kişi sayısı / tarifin kişi sayısı, her öğün için ayrı."""
    lines: list[CostLine] = []
    pantry: list[str] = []
    categories = await _category_ids(db)
    for need in _collect_needs(uses):
        if need.is_pantry and not include_pantry:
            pantry.append(need.name)
            continue
        pick = await _match(db, need, user_id, categories)
        lines.append(
            CostLine(
                name=need.name,
                needed_quantity=need.quantity.quantize(CENT).normalize(),
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


def _choose(
    candidates: list[Recipe], usage: Counter, today: set[int], yesterday: set[int], rng: random.Random,
    exclude: int | None = None,
) -> Recipe:
    """Çeşitlilik: aynı gün tekrar etmesin, mümkünse dünkü yemekler gelmesin, en az kullanılan önce;
    eşitlerde sevilen tarif (puanı yüksek) daha büyük olasılıkla seçilir."""
    pool = [r for r in candidates if r.id != exclude] or candidates
    return min(pool, key=lambda r: (r.id in today, r.id in yesterday, usage[r.id], -rng.random() * (r.score + 10)))


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


def default_name(period: PlanPeriod, start: date) -> str:
    label = "Günlük" if period is PlanPeriod.DAILY else "Haftalık"
    return f"{label} yemek planı · {start.day} {MONTHS[start.month - 1]}"


def _meal_cuisines(recipes: list[Recipe], cuisines: list[Cuisine], slot: MealSlot, courses: list[CourseType]) -> list[int]:
    """Bu öğünü kendi başına çıkarabilen mutfaklar: öğünün ana yemeği (ara öğünde atıştırmalığı) olanlar;
    hiçbirinde yoksa menüdeki herhangi bir türden yemeği olanlar."""
    wanted = slot_courses(slot, courses)
    first = CourseType.SNACK if slot is MealSlot.SNACK else CourseType.MAIN
    with_first = [c.id for c in cuisines if first in wanted and _candidates(recipes, slot, first, cuisine_id=c.id)]
    return with_first or [c.id for c in cuisines if any(_pool([r for r in recipes if r.cuisine_id == c.id], slot, k) for k in wanted)]


async def create_plan(
    db: AsyncSession, user: User, *, period: PlanPeriod, cuisine_slugs: list[str], servings: int,
    slots: list[MealSlot], courses: list[CourseType], start: date | None, name: str | None,
    diets: list[Diet] | None = None, avoid: list[Allergen] | None = None, rng: random.Random | None = None,
) -> MealPlan:
    rng = rng or random.Random()
    cuisines = await get_cuisines(db, cuisine_slugs)
    slots = sorted(set(slots), key=SLOT_ORDER.__getitem__)
    courses = sorted(set(courses), key=COURSE_ORDER.__getitem__)
    diets = sorted(set(diets or []), key=list(Diet).index)
    avoid = sorted(set(avoid or []), key=list(Allergen).index)
    recipes = await _cuisine_recipes(db, cuisines, diets, avoid)
    menu = {slot: [c for c in slot_courses(slot, courses) if _pool(recipes, slot, c)] for slot in slots}
    if not any(menu.values()):
        names = ", ".join(c.name for c in cuisines)
        detail = f"{names} için seçilen öğünlere uygun tarif yok"
        if diets or avoid:
            detail += " (diyet ve alerji seçimlerinize uyan)"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)
    start = start or date.today()
    # Hangi öğünü hangi mutfaklar çıkarabilir (ör. kahvaltılığı olmayan mutfak kahvaltıya gelmez)
    able = {slot: _meal_cuisines(recipes, cuisines, slot, courses) for slot in slots}

    plan = MealPlan(
        user_id=user.id,
        name=name or default_name(period, start),
        period=period,
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
    for day in range(PERIOD_DAYS[period]):
        today: set[int] = set()
        today_cuisines: set[int] = set()
        for slot in slots:
            main = None
            cuisine_id = None
            if able[slot]:
                # En az kullanılan mutfak; eşitse bugün henüz gelmemiş olan, sonra rastgele
                cuisine_id = min(able[slot], key=lambda c: (cuisine_usage[c], c in today_cuisines, rng.random()))
                cuisine_usage[cuisine_id] += 1
                today_cuisines.add(cuisine_id)
            for course in menu[slot]:
                candidates = _candidates(recipes, slot, course, main, cuisine_id)
                if not candidates:  # ör. mantının yanına pilav önerilmez
                    continue
                recipe = _choose(candidates, usage, today, yesterday, rng)
                if course is CourseType.MAIN:
                    main = recipe
                usage[recipe.id] += 1
                today.add(recipe.id)
                plan.entries.append(
                    MealPlanEntry(day_index=day, slot=slot, course=course, slot_order=_order(slot, course), recipe_id=recipe.id)
                )
        yesterday = today
    db.add(plan)
    await db.commit()
    return await get_plan(db, user, plan.id)


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
    return _choose(pool, usage, today, around, rng, exclude=skip_entry.recipe_id if skip_entry else None)


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
    entry.recipe_id = recipe.id
    if entry.course is CourseType.MAIN:
        _repair_companions(plan, recipes, entry, recipe, rng)
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
    """Kullanıcı o öğünde bu yemeği istemiyor (ör. çorba): plandan ve maliyetten çıkar."""
    plan.entries.remove(_get_entry(plan, entry_id))
    await db.commit()


async def add_entry(
    db: AsyncSession, plan: MealPlan, day: int, slot: MealSlot, course: CourseType, recipe_id: int | None,
    rng: random.Random | None = None,
) -> None:
    """Kaldırılan bir yemek türünü (ya da yeni bir öğünü) geri ekle; tarif verilmezse önerilir."""
    if day >= PERIOD_DAYS[plan.period]:
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
    return [(e.recipe, Decimal(plan.servings) / e.recipe.servings) for e in plan.entries]


def meal_count(plan: MealPlan) -> int:
    """Öğün sayısı (gün x öğün); bir öğündeki çorba, ana yemek, tatlı... tek öğün sayılır."""
    return len({(e.day_index, e.slot) for e in plan.entries})


async def plan_cost(db: AsyncSession, plan: MealPlan, user_id: int, include_pantry: bool = False) -> CostOut:
    return await compute_cost(db, _uses(plan), meal_count(plan) * plan.servings, user_id, include_pantry)


def to_summary(plan: MealPlan) -> MealPlanSummary:
    return MealPlanSummary(
        id=plan.id,
        name=plan.name,
        period=plan.period,
        cuisine=plan.cuisine.slug,
        cuisines=plan.cuisine_slugs,
        start_date=plan.start_date,
        days=PERIOD_DAYS[plan.period],
        servings=plan.servings,
        meal_slots=plan.slots,
        courses=plan.course_list,
        diets=plan.diet_list,
        avoid_allergens=plan.avoid_list,
        entry_count=meal_count(plan),
        exported_list_id=plan.exported_list_id,
        created_at=plan.created_at,
    )


def daily_nutrition(plan: MealPlan) -> Nutrition | None:
    """Kişi başı günlük ortalama (plandaki bütün yemekler; besin değeri olmayanlar hariç)."""
    known = [e.recipe for e in plan.entries if e.recipe.kcal is not None]
    if not known:
        return None
    days = PERIOD_DAYS[plan.period]
    return Nutrition(
        kcal=round(sum(r.kcal for r in known) / days),
        protein_g=round(sum(r.protein_g or 0 for r in known) / days),
        carbs_g=round(sum(r.carbs_g or 0 for r in known) / days),
        fat_g=round(sum(r.fat_g or 0 for r in known) / days),
    )


async def to_detail(db: AsyncSession, plan: MealPlan, user_id: int, include_pantry: bool = False) -> MealPlanDetail:
    liked = await liked_ids(db, user_id)
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
            )
            for e in sorted(plan.entries, key=lambda e: (e.day_index, e.slot_order))
        ],
        daily_nutrition=daily_nutrition(plan),
        cost=await plan_cost(db, plan, user_id, include_pantry),
    )


# --- Alışveriş listesine aktarma ------------------------------------------------------------


async def export_to_list(
    db: AsyncSession, user: User, plan: MealPlan, *, list_id: int | None, list_name: str | None, include_pantry: bool
) -> tuple[ShoppingList, int, list[str]]:
    """Malzemeler (bulunan ürün grupları, paket adediyle) listeye eklenir. Grup listede zaten
    varsa yeni kalem açılmaz, miktarı artar (elle ürün eklemekle aynı kural)."""
    cost = await plan_cost(db, plan, user.id, include_pantry)
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
    return shopping_list, len(packages), skipped
