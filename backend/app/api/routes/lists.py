from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import ShoppingList, ShoppingListItem
from app.schemas.lists import (
    ApplyPlanRequest,
    ItemCreate,
    ItemUpdate,
    JoinListRequest,
    ListCreate,
    ListDetail,
    ListSummary,
    ListUpdate,
    OptimizeOut,
    ShareCodeOut,
)
from app.schemas.savings import CompleteResponse
from app.services import lists as svc

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[ListSummary])
async def list_lists(user: CurrentUser, db: DbSession) -> list[ListSummary]:
    """Listeler sayfası: her liste için "Tahmini" tutar ve "En çok" alınacak market."""
    return await svc.list_summaries(db, user)


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
    """Liste silinir; Tasarruf Kasası kayıtları korunur. Ortak listeyi yalnızca sahibi silebilir."""
    await db.delete(await svc.get_owned_list(db, user, list_id, owner_only=True))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Ortak liste ----------------------------------------------------------------------------


@router.post("/join", response_model=ListDetail)
async def join_list(body: JoinListRequest, user: CurrentUser, db: DbSession) -> ListDetail:
    """Davet koduyla ortak listeye katıl: liste iki tarafta da görünür, ikisi de düzenleyebilir."""
    list_id = await svc.join_list(db, user, body.code)
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.post("/{list_id}/share", response_model=ShareCodeOut)
async def share_list(list_id: int, user: CurrentUser, db: DbSession) -> ShareCodeOut:
    """"Listeyi Paylaş": davet kodu (yoksa oluşturulur)."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    return ShareCodeOut(share_code=await svc.ensure_share_code(db, shopping_list))


@router.delete("/{list_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(list_id: int, member_id: int, user: CurrentUser, db: DbSession) -> Response:
    """Sahip bir üyeyi çıkarır ya da üye listeden ayrılır."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    await svc.remove_member(db, user, shopping_list, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Kalemler -----------------------------------------------------------------------------


@router.post("/{list_id}/items", response_model=ListDetail, status_code=status.HTTP_201_CREATED)
async def add_item(list_id: int, body: ItemCreate, user: CurrentUser, db: DbSession) -> ListDetail:
    """Grup listede zaten varsa yeni kalem açılmaz: miktarı artar, gönderilen tercih uygulanır."""
    shopping_list = await svc.get_owned_list(db, user, list_id, editable=True)
    group = await svc.get_group(db, body.group_id)
    preference = body.model_dump(include={"preferred_brand", "preferred_product_id"}, exclude_none=True)
    existing = next((i for i in shopping_list.items if i.group_id == group.id), None)
    if existing is not None:
        svc.reset_plan(shopping_list)
        existing.quantity = min(existing.quantity + body.quantity, Decimal(999))
        svc.set_preference(existing, group, preference)
        await db.commit()
        return svc.to_detail(await svc.get_owned_list(db, user, list_id))

    next_position = await db.scalar(
        select(func.coalesce(func.max(ShoppingListItem.position) + 1, 0)).where(
            ShoppingListItem.list_id == list_id
        )
    )
    svc.reset_plan(shopping_list)
    item = ShoppingListItem(
        group_id=group.id, quantity=body.quantity, note=body.note, position=next_position, added_by_user_id=user.id
    )
    svc.set_preference(item, group, preference)
    shopping_list.items.append(item)
    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.patch("/{list_id}/items/{item_id}", response_model=ListDetail)
async def update_item(
    list_id: int, item_id: int, body: ItemUpdate, user: CurrentUser, db: DbSession
) -> ListDetail:
    """Marka kilitleme (sağa kaydır), miktar, "alındı" işareti ve sıralama."""
    shopping_list = await svc.get_owned_list(db, user, list_id, editable=True)
    item = svc.get_item(shopping_list, item_id)
    changes = body.model_dump(exclude_unset=True)

    if svc.set_preference(item, item.group, changes):
        svc.reset_plan(shopping_list)
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
    shopping_list = await svc.get_owned_list(db, user, list_id, editable=True)
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
    return svc.to_optimize_out(await svc.run_optimizer(db, shopping_list, user.id))


@router.post("/{list_id}/apply", response_model=ListDetail)
async def apply_plan(
    list_id: int, body: ApplyPlanRequest, user: CurrentUser, db: DbSession
) -> ListDetail:
    """"Listeye Uygula": kalemler markete göre gruplanır, liste Alışveriş Modu'na geçer."""
    shopping_list = await svc.get_owned_list(db, user, list_id, editable=True)
    await svc.apply_plan(db, shopping_list, body.plan_type, user.id)
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.post("/{list_id}/clear-preferences", response_model=ListDetail)
async def clear_preferences(list_id: int, user: CurrentUser, db: DbSession) -> ListDetail:
    """Kombinasyon ipucu: tüm marka/ürün kilitlerini kaldırır ("MARKA FARKETMEZ")."""
    shopping_list = await svc.get_owned_list(db, user, list_id, editable=True)
    changed = False
    for item in shopping_list.items:
        changed |= svc.set_preference(item, item.group, {"preferred_product_id": None})
    if changed:
        svc.reset_plan(shopping_list)
    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.delete("/{list_id}/plan", response_model=ListDetail)
async def cancel_plan(list_id: int, user: CurrentUser, db: DbSession) -> ListDetail:
    """Alışveriş Modu'nda "İptal Et": plan kaldırılır, alındı işaretleri korunur."""
    shopping_list = await svc.get_owned_list(db, user, list_id, editable=True)
    svc.reset_plan(shopping_list)
    await db.commit()
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))


@router.post("/{list_id}/complete", response_model=CompleteResponse)
async def complete_list(list_id: int, user: CurrentUser, db: DbSession) -> CompleteResponse:
    """"Alışverişi Bitir": Fırsatçı planı uygulandıysa tasarruf kalıcı kasaya eklenir; liste
    tamamlandı olarak kilitlenir; "Tekrar kullan" ile yeniden açılır."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    return await svc.complete_list(db, user, shopping_list)


@router.post("/{list_id}/reopen", response_model=ListDetail)
async def reopen_list(list_id: int, user: CurrentUser, db: DbSession) -> ListDetail:
    """"Listeyi tekrar kullan": tamamlanmış liste aynı ürünlerle yeniden açılır, işaretler sıfırlanır."""
    shopping_list = await svc.get_owned_list(db, user, list_id)
    await svc.reopen_list(db, shopping_list)
    return svc.to_detail(await svc.get_owned_list(db, user, list_id))
