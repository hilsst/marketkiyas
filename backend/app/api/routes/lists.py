from datetime import datetime, timezone

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import ShoppingList, ShoppingListItem
from app.schemas.lists import (
    ApplyPlanRequest,
    ItemCreate,
    ItemUpdate,
    ListCreate,
    ListDetail,
    ListSummary,
    ListUpdate,
    OptimizeOut,
)
from app.schemas.savings import CompleteResponse
from app.services import lists as svc

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[ListSummary])
async def list_lists(user: CurrentUser, db: DbSession) -> list[ListSummary]:
    rows = await db.scalars(
        select(ShoppingList)
        .where(ShoppingList.user_id == user.id)
        .options(selectinload(ShoppingList.items))
        .order_by(ShoppingList.updated_at.desc())
    )
    return [svc.to_summary(sl) for sl in rows]


@router.post("", response_model=ListDetail, status_code=status.HTTP_201_CREATED)
async def create_list(body: ListCreate, user: CurrentUser, db: DbSession) -> ListDetail:
    shopping_list = ShoppingList(user_id=user.id, name=body.name, icon=body.icon)
    db.add(shopping_list)
    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, shopping_list.id))


@router.get("/{list_id}", response_model=ListDetail)
async def get_list(list_id: int, user: CurrentUser, db: DbSession) -> ListDetail:
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.patch("/{list_id}", response_model=ListDetail)
async def update_list(list_id: int, body: ListUpdate, user: CurrentUser, db: DbSession) -> ListDetail:
    shopping_list = await svc.get_owned_list(db, user, list_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(shopping_list, field, value)
    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(list_id: int, user: CurrentUser, db: DbSession) -> Response:
    """Liste silinir; Tasarruf Kasası kayıtları korunur."""
    await db.delete(await svc.get_owned_list(db, user, list_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Kalemler -----------------------------------------------------------------------------


@router.post("/{list_id}/items", response_model=ListDetail, status_code=status.HTTP_201_CREATED)
async def add_item(list_id: int, body: ItemCreate, user: CurrentUser, db: DbSession) -> ListDetail:
    shopping_list = await svc.get_owned_list(db, user, list_id)
    group = await svc.get_group(db, body.group_id)
    next_position = await db.scalar(
        select(func.coalesce(func.max(ShoppingListItem.position) + 1, 0)).where(
            ShoppingListItem.list_id == list_id
        )
    )
    svc.reset_plan(shopping_list)
    shopping_list.items.append(
        ShoppingListItem(
            group_id=group.id,
            quantity=body.quantity,
            preferred_brand=svc.validate_brand(group, body.preferred_brand),
            note=body.note,
            position=next_position,
        )
    )
    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.patch("/{list_id}/items/{item_id}", response_model=ListDetail)
async def update_item(
    list_id: int, item_id: int, body: ItemUpdate, user: CurrentUser, db: DbSession
) -> ListDetail:
    """Marka kilitleme (sağa kaydır), miktar, "alındı" işareti ve sıralama."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    item = svc.get_item(shopping_list, item_id)
    changes = body.model_dump(exclude_unset=True)

    if "preferred_brand" in changes:
        brand = svc.validate_brand(item.group, changes["preferred_brand"])
        if brand != item.preferred_brand:
            svc.reset_plan(shopping_list)
        item.preferred_brand = brand
    if "quantity" in changes and changes["quantity"] is not None and changes["quantity"] != item.quantity:
        svc.reset_plan(shopping_list)
        item.quantity = changes["quantity"]
    if "is_checked" in changes and changes["is_checked"] is not None:
        item.is_checked = changes["is_checked"]
        item.checked_at = datetime.now(timezone.utc) if item.is_checked else None
    if "position" in changes and changes["position"] is not None:
        item.position = changes["position"]
    if "note" in changes:
        item.note = changes["note"]

    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.delete("/{list_id}/items/{item_id}", response_model=ListDetail)
async def delete_item(list_id: int, item_id: int, user: CurrentUser, db: DbSession) -> ListDetail:
    shopping_list = await svc.get_owned_list(db, user, list_id)
    item = svc.get_item(shopping_list, item_id)
    svc.reset_plan(shopping_list)
    shopping_list.items.remove(item)
    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


# --- Optimizasyon ve alışveriş akışı ------------------------------------------------------


@router.get("/{list_id}/optimize", response_model=OptimizeOut)
async def optimize_list(list_id: int, user: CurrentUser, db: DbSession) -> OptimizeOut:
    """Üç sekmenin (Tek Market, Kombinasyon, Fırsatçı) hesaplaması ve tasarruf projeksiyonu."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    return svc.to_optimize_out(await svc.run_optimizer(db, shopping_list))


@router.post("/{list_id}/apply", response_model=ListDetail)
async def apply_plan(
    list_id: int, body: ApplyPlanRequest, user: CurrentUser, db: DbSession
) -> ListDetail:
    """"Listeye Uygula": kalemler markete göre gruplanır, liste Alışveriş Modu'na geçer."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    await svc.apply_plan(db, shopping_list, body.plan_type)
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.post("/{list_id}/complete", response_model=CompleteResponse)
async def complete_list(list_id: int, user: CurrentUser, db: DbSession) -> CompleteResponse:
    """"Alışverişi Bitir": Fırsatçı planı uygulandıysa tasarruf kalıcı kasaya eklenir."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    return await svc.complete_list(db, user, shopping_list)
