"""Yemek planlayıcı: plan oluşturma, malzeme maliyeti ve alışveriş listesine aktarma.

Maliyet: plandaki her yemeğin malzemeleri kişi sayısına göre orantılanıp toplanır (aynı malzeme
farklı yemeklerde geçiyorsa birleşir). Her malzeme için katalogda arama yapılır ve kullanıcının
şubelerinde (seçmediyse zincir genelinde) gereken miktarı en ucuza karşılayan ürün grubu seçilir.
"""

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CourseType,
    Cuisine,
    MealPlan,
    MealPlanEntry,
    MealSlot,
    PlanPeriod,
    Recipe,
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
    RecipeDetail,
    RecipeSummary,
)
from app.schemas.products import GroupSummary
from app.services import lists as list_svc
from app.services.catalog import search_groups
from app.services.normalize import normalize_text

SLOT_ORDER = {MealSlot.BREAKFAST: 0, MealSlot.LUNCH: 1, MealSlot.SNACK: 2, MealSlot.DINNER: 3}
COURSE_ORDER = {
    CourseType.SOUP: 0, CourseType.MAIN: 1, CourseType.SALAD: 2, CourseType.DESSERT: 3, CourseType.DRINK: 4,
    CourseType.SNACK: 5,
}
# Her öğünde önerilecek yemek türleri
SLOT_COURSES = {
    MealSlot.BREAKFAST: [CourseType.MAIN, CourseType.DRINK],
    MealSlot.LUNCH: [CourseType.SOUP, CourseType.MAIN, CourseType.SALAD, CourseType.DESSERT, CourseType.DRINK],
    MealSlot.SNACK: [CourseType.SNACK],
    MealSlot.DINNER: [CourseType.SOUP, CourseType.MAIN, CourseType.SALAD, CourseType.DESSERT, CourseType.DRINK],
}
PERIOD_DAYS = {PlanPeriod.DAILY: 1, PlanPeriod.WEEKLY: 7}
# Bir malzeme için değerlendirilecek arama sonucu sayısı
MATCH_CANDIDATES = 30
CENT = Decimal("0.01")
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


# --- Mutfaklar ve tarifler -------------------------------------------------------------------


def _recipe_options():
    return selectinload(Recipe.cuisine), selectinload(Recipe.ingredients)


async def cuisines(db: AsyncSession) -> list[CuisineOut]:
    counts = dict(
        (await db.execute(
            select(Recipe.cuisine_id, func.count()).where(Recipe.is_active).group_by(Recipe.cuisine_id)
        )).all()
    )
    rows = await db.scalars(select(Cuisine).where(Cuisine.is_active).order_by(Cuisine.position, Cuisine.id))
    return [
        CuisineOut(slug=c.slug, name=c.name, icon=c.icon, is_default=c.is_default, recipe_count=counts.get(c.id, 0))
        for c in rows
    ]


async def get_cuisine(db: AsyncSession, slug: str | None) -> Cuisine:
    """slug boşsa varsayılan mutfak (Anadolu)."""
    stmt = select(Cuisine).where(Cuisine.is_active)
    stmt = stmt.where(Cuisine.slug == slug) if slug else stmt.order_by(Cuisine.is_default.desc(), Cuisine.position)
    cuisine = await db.scalar(stmt.limit(1))
    if cuisine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mutfak bulunamadı")
    return cuisine


def recipe_summary(recipe: Recipe) -> RecipeSummary:
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
    )


async def list_recipes(
    db: AsyncSession, cuisine: str | None, slot: MealSlot | None, course: CourseType | None = None
) -> list[RecipeSummary]:
    stmt = select(Recipe).join(Cuisine).where(Recipe.is_active, Cuisine.is_active).options(*_recipe_options())
    if cuisine:
        stmt = stmt.where(Cuisine.slug == cuisine)
    recipes = [
        r for r in (await db.scalars(stmt.order_by(Recipe.id))).all()
        if (slot is None or slot in r.slots) and (course is None or r.course_type is course)
    ]
    return [recipe_summary(r) for r in recipes]


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
        **recipe_summary(recipe).model_dump(),
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


def _roots(term: str) -> list[str]:
    """Kaba kök: 'domates salcasi' -> ['domates', 'salca'] ('Domates Salça 830 g' de eşleşsin)."""
    roots = []
    for word in normalize_text(term).split():
        root = word
        if word.endswith("si") and len(word) > 4:
            root = word[:-2]
        elif word[-1] in "iu" and len(word) > 3:
            root = word[:-1]
        roots.append(root)
    return roots


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


async def _match(db: AsyncSession, need: _Need, user_id: int | None) -> _Pick | None:
    """Gereken miktarı en ucuza karşılayan grup. Grubun adı arama ifadesinin bütün kelimelerini
    içermelidir (ör. "pul biber" için "Sivri Biber" sayılmaz); bulunamazsa malzeme eksik görünür.
    Arama ifadesi "|" ile alternatif içerebilir: "tavuk gogus|pilic gogus"."""
    picks: dict[int, _Pick] = {}
    for term in (t.strip() for t in need.search_term.split("|")):
        if not term:
            continue
        roots = _roots(term)
        for group in await search_groups(db, term, None, MATCH_CANDIDATES, user_id=user_id):
            name = normalize_text(group.name)
            if group.id in picks or any(ex in name for ex in need.excludes) or not all(r in name for r in roots):
                continue
            pick = _price_for(group, need)
            if pick is not None:
                picks[group.id] = pick
    return min(picks.values(), key=lambda p: (p.approximate, p.purchase_cost, p.used_cost), default=None)


def _collect_needs(uses: list[tuple[Recipe, Decimal]]) -> list[_Need]:
    needs: dict[tuple[str, Unit], _Need] = {}
    for recipe, factor in uses:
        for ing in recipe.ingredients:
            key = (normalize_text(ing.search_term), ing.unit)
            need = needs.get(key)
            if need is None:
                excludes = tuple(normalize_text(e) for e in (ing.exclude_terms or "").split(",") if e.strip())
                need = needs[key] = _Need(ing.name, ing.unit, ing.search_term, excludes, ing.is_pantry)
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
    for need in _collect_needs(uses):
        if need.is_pantry and not include_pantry:
            pantry.append(need.name)
            continue
        pick = await _match(db, need, user_id)
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
    """Çeşitlilik: aynı gün tekrar etmesin, mümkünse dünkü yemekler gelmesin, en az kullanılan önce."""
    pool = [r for r in candidates if r.id != exclude] or candidates
    return min(pool, key=lambda r: (r.id in today, r.id in yesterday, usage[r.id], rng.random()))


def slot_courses(slot: MealSlot, courses: list[CourseType]) -> list[CourseType]:
    """Öğünde olacak yemek türleri; plan oluştururken seçilen türlerle süzülür (ara öğün hariç)."""
    if slot is MealSlot.SNACK:
        return [CourseType.SNACK]
    return [c for c in SLOT_COURSES[slot] if c in courses]


async def _cuisine_recipes(db: AsyncSession, cuisine: Cuisine) -> list[Recipe]:
    return list((await db.scalars(
        select(Recipe).where(Recipe.cuisine_id == cuisine.id, Recipe.is_active).order_by(Recipe.id)
    )).all())


def _candidates(recipes: list[Recipe], slot: MealSlot, course: CourseType, main: Recipe | None = None) -> list[Recipe]:
    """Öğüne ve türe uygun tarifler. İçecekte ana yemekle uyumlu olanlar; uyumlu yoksa hepsi."""
    pool = [r for r in recipes if r.course_type is course and slot in r.slots]
    if course is CourseType.DRINK:
        return [r for r in pool if r.pairs(main)] or pool
    return pool


def _order(slot: MealSlot, course: CourseType) -> int:
    return SLOT_ORDER[slot] * 10 + COURSE_ORDER[course]


def default_name(period: PlanPeriod, start: date) -> str:
    label = "Günlük" if period is PlanPeriod.DAILY else "Haftalık"
    return f"{label} yemek planı · {start.day} {MONTHS[start.month - 1]}"


async def create_plan(
    db: AsyncSession, user: User, *, period: PlanPeriod, cuisine_slug: str | None, servings: int,
    slots: list[MealSlot], courses: list[CourseType], start: date | None, name: str | None,
    rng: random.Random | None = None,
) -> MealPlan:
    rng = rng or random.Random()
    cuisine = await get_cuisine(db, cuisine_slug)
    slots = sorted(set(slots), key=SLOT_ORDER.__getitem__)
    courses = sorted(set(courses), key=COURSE_ORDER.__getitem__)
    recipes = await _cuisine_recipes(db, cuisine)
    menu = {slot: [c for c in slot_courses(slot, courses) if _candidates(recipes, slot, c)] for slot in slots}
    if not any(menu.values()):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"{cuisine.name} için seçilen öğünlere uygun tarif yok"
        )
    start = start or date.today()

    plan = MealPlan(
        user_id=user.id,
        name=name or default_name(period, start),
        period=period,
        cuisine_id=cuisine.id,
        start_date=start,
        servings=servings,
        meal_slots=",".join(s.value for s in slots),
        courses=",".join(c.value for c in courses),
    )
    usage: Counter = Counter()
    yesterday: set[int] = set()
    for day in range(PERIOD_DAYS[period]):
        today: set[int] = set()
        for slot in slots:
            main = None
            for course in menu[slot]:
                recipe = _choose(_candidates(recipes, slot, course, main), usage, today, yesterday, rng)
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


def _suggest(
    plan: MealPlan, recipes: list[Recipe], day: int, slot: MealSlot, course: CourseType,
    rng: random.Random, skip_entry: MealPlanEntry | None = None,
) -> Recipe | None:
    by_id = {r.id: r for r in recipes}
    others = [e for e in plan.entries if e is not skip_entry]
    pool = _candidates(recipes, slot, course, _main_of(plan, day, slot, by_id))
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
    recipes = await _cuisine_recipes(db, plan.cuisine)
    if recipe_id is not None:
        recipe = await get_recipe(db, recipe_id)
    else:
        # "Başka öner": aynı mutfaktan bu öğüne ve türe uygun, şu ankinden farklı bir yemek
        recipe = _suggest(plan, recipes, entry.day_index, entry.slot, entry.course, rng, skip_entry=entry)
        if recipe is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bu öğün için başka tarif yok")
    entry.recipe_id = recipe.id
    if entry.course is CourseType.MAIN:
        # Ana yemek değişti: içecek artık uyumlu değilse uyumlu bir içecek seçilir
        drink = next((e for e in _meal_entries(plan, entry.day_index, entry.slot) if e.course is CourseType.DRINK), None)
        by_id = {r.id: r for r in recipes}
        if drink is not None and drink.recipe_id in by_id and not by_id[drink.recipe_id].pairs(recipe):
            new_drink = _suggest(plan, recipes, drink.day_index, drink.slot, CourseType.DRINK, rng, skip_entry=drink)
            if new_drink is not None:
                drink.recipe_id = new_drink.id
    await db.commit()


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
        recipe = _suggest(plan, await _cuisine_recipes(db, plan.cuisine), day, slot, course, rng or random.Random())
        if recipe is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bu öğün için uygun tarif yok")
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
        start_date=plan.start_date,
        days=PERIOD_DAYS[plan.period],
        servings=plan.servings,
        meal_slots=plan.slots,
        courses=plan.course_list,
        entry_count=meal_count(plan),
        exported_list_id=plan.exported_list_id,
        created_at=plan.created_at,
    )


async def to_detail(db: AsyncSession, plan: MealPlan, user_id: int, include_pantry: bool = False) -> MealPlanDetail:
    return MealPlanDetail(
        **to_summary(plan).model_dump(),
        entries=[
            MealPlanEntryOut(
                id=e.id,
                day_index=e.day_index,
                date=plan.start_date + timedelta(days=e.day_index),
                slot=e.slot,
                course=e.course,
                recipe=recipe_summary(e.recipe),
            )
            for e in sorted(plan.entries, key=lambda e: (e.day_index, e.slot_order))
        ],
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
