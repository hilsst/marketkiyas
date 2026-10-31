from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models import Allergen, CourseType, Diet, MealSlot
from app.schemas.meals import (
    CuisineOut,
    EntryCreate,
    EntryUpdate,
    ExportOut,
    ExportRequest,
    MealPlanCreate,
    MealPlanDetail,
    MealPlanSummary,
    MealPlanUpdate,
    RecipeDetail,
    RecipeSummary,
)
from app.services import lists as list_svc
from app.services import meals as svc

router = APIRouter(tags=["meals"])


@router.get("/cuisines", response_model=list[CuisineOut])
async def list_cuisines(db: DbSession) -> list[CuisineOut]:
    """Plan için seçilebilecek mutfaklar (Türk, İtalyan, Uzak Doğu, Meksika); tarif sayısı ve örnekler
    yalnız malzemeleri marketlerde bulunan tariflerden."""
    return await svc.cuisines(db)


@router.get("/recipes", response_model=list[RecipeSummary])
async def list_recipes(
    db: DbSession, user: OptionalUser, cuisine: str | None = None, slot: MealSlot | None = None,
    course: CourseType | None = None, diet: Annotated[list[Diet] | None, Query()] = None,
    avoid: Annotated[list[Allergen] | None, Query()] = None,
) -> list[RecipeSummary]:
    """En sevilen tarifler önce. diet=vegan&avoid=gluten: yalnız uyanlar."""
    return await svc.list_recipes(db, cuisine, slot, course, diet, avoid, user.id if user else None)


@router.put("/recipes/{recipe_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def like_recipe(recipe_id: int, user: CurrentUser, db: DbSession) -> Response:
    await svc.set_like(db, user, await svc.get_recipe(db, recipe_id), True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/recipes/{recipe_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_recipe(recipe_id: int, user: CurrentUser, db: DbSession) -> Response:
    await svc.set_like(db, user, await svc.get_recipe(db, recipe_id), False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
async def get_recipe(
    recipe_id: int, db: DbSession, user: OptionalUser, servings: Annotated[int | None, Query(ge=1, le=12)] = None
) -> RecipeDetail:
    """Tarif, malzemeler ve istenen kişi sayısı için tahmini maliyet (kullanıcının şubelerine göre)."""
    recipe = await svc.get_recipe(db, recipe_id)
    return await svc.recipe_detail(db, recipe, servings or recipe.servings, user.id if user else None)


@router.get("/meal-plans", response_model=list[MealPlanSummary])
async def list_plans(user: CurrentUser, db: DbSession) -> list[MealPlanSummary]:
    return await svc.list_plans(db, user)


@router.post("/meal-plans", response_model=MealPlanDetail, status_code=status.HTTP_201_CREATED)
async def create_plan(body: MealPlanCreate, user: CurrentUser, db: DbSession) -> MealPlanDetail:
    """Günlük (1 gün) ya da haftalık (7 gün) plan: seçilen mutfaklardan çeşitli yemekler öğünlere dağıtılır;
    her öğün tek mutfaktan gelir."""
    plan = await svc.create_plan(
        db, user, period=body.period, cuisine_slugs=body.cuisines or ([body.cuisine] if body.cuisine else []),
        servings=body.servings,
        slots=body.meal_slots, courses=body.courses, start=body.start_date, name=body.name,
        diets=body.diets, avoid=body.avoid_allergens,
    )
    return await svc.to_detail(db, plan, user.id)


@router.get("/meal-plans/{plan_id}", response_model=MealPlanDetail)
async def get_plan(plan_id: int, user: CurrentUser, db: DbSession, include_pantry: bool = False) -> MealPlanDetail:
    """Plan ve güncel fiyatlarla malzeme maliyeti. include_pantry: tuz, baharat gibi evde
    var sayılanlar da hesaba katılsın."""
    return await svc.to_detail(db, await svc.get_plan(db, user, plan_id), user.id, include_pantry)


@router.patch("/meal-plans/{plan_id}", response_model=MealPlanDetail)
async def update_plan(plan_id: int, body: MealPlanUpdate, user: CurrentUser, db: DbSession) -> MealPlanDetail:
    plan = await svc.get_plan(db, user, plan_id)
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(plan, field, value)
    await db.commit()
    return await svc.to_detail(db, await svc.get_plan(db, user, plan_id), user.id)


@router.patch("/meal-plans/{plan_id}/entries/{entry_id}", response_model=MealPlanDetail)
async def change_entry(
    plan_id: int, entry_id: int, body: EntryUpdate, user: CurrentUser, db: DbSession
) -> MealPlanDetail:
    """Öğünün yemeğini değiştir; recipe_id boşsa "Başka öner"."""
    plan = await svc.get_plan(db, user, plan_id)
    await svc.change_entry(db, user, plan, entry_id, body.recipe_id)
    return await svc.to_detail(db, await svc.get_plan(db, user, plan_id), user.id)


@router.post("/meal-plans/{plan_id}/entries", response_model=MealPlanDetail, status_code=status.HTTP_201_CREATED)
async def add_entry(plan_id: int, body: EntryCreate, user: CurrentUser, db: DbSession) -> MealPlanDetail:
    """Öğüne yemek ekle (ör. kaldırılan çorbayı geri getir); tarif verilmezse uygun olan önerilir."""
    plan = await svc.get_plan(db, user, plan_id)
    await svc.add_entry(db, plan, body.day_index, body.slot, body.course, body.recipe_id)
    return await svc.to_detail(db, await svc.get_plan(db, user, plan_id), user.id)


@router.delete("/meal-plans/{plan_id}/entries/{entry_id}", response_model=MealPlanDetail)
async def remove_entry(plan_id: int, entry_id: int, user: CurrentUser, db: DbSession) -> MealPlanDetail:
    """O öğünde istenmeyen yemeği (ör. çorba) kaldır; maliyetten de çıkar."""
    plan = await svc.get_plan(db, user, plan_id)
    await svc.remove_entry(db, plan, entry_id)
    return await svc.to_detail(db, await svc.get_plan(db, user, plan_id), user.id)


@router.delete("/meal-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: int, user: CurrentUser, db: DbSession) -> Response:
    await db.delete(await svc.get_plan(db, user, plan_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/meal-plans/{plan_id}/to-list", response_model=ExportOut)
async def export_plan(plan_id: int, body: ExportRequest, user: CurrentUser, db: DbSession) -> ExportOut:
    """"Alışveriş listesine aktar": malzemeler mevcut bir listeye ya da yeni listeye eklenir."""
    plan = await svc.get_plan(db, user, plan_id)
    shopping_list, added, skipped = await svc.export_to_list(
        db, user, plan, list_id=body.list_id, list_name=body.list_name, include_pantry=body.include_pantry
    )
    detail = list_svc.to_detail(await list_svc.get_owned_list(db, user, shopping_list.id))
    return ExportOut(list=detail, added=added, skipped=skipped)
