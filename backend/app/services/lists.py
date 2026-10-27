import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    GroupMember,
    ListMember,
    ListStatus,
    PlanType,
    Product,
    ProductGroup,
    SavingsRecord,
    ShoppingList,
    ShoppingListItem,
    User,
)
from app.schemas.lists import (
    AssignedProduct,
    ItemOut,
    ListDetail,
    ListMemberOut,
    ListSummary,
    MarketBreakdown,
    MarketTotalOut,
    OptimizeOut,
    PlanLineOut,
    PlanOut,
    SavingsProjection,
    ShoppingGroup,
    SingleMarketOut,
)
from app.schemas.savings import CompleteResponse
from app.services import optimizer
from app.services.optimizer import ItemInput, Offer, OptimizationResult, Plan
from app.services.pricing import PriceResolver, build_resolver, candidate_market_ids


def _list_options():
    return (
        selectinload(ShoppingList.items)
        .selectinload(ShoppingListItem.group)
        .selectinload(ProductGroup.members)
        .selectinload(GroupMember.product),
        selectinload(ShoppingList.items).selectinload(ShoppingListItem.assigned_product),
        selectinload(ShoppingList.items).selectinload(ShoppingListItem.assigned_store),
        selectinload(ShoppingList.items).selectinload(ShoppingListItem.added_by),
        selectinload(ShoppingList.user),
        selectinload(ShoppingList.members).selectinload(ListMember.user),
    )


def _visible_to(user: User):
    """Kullanıcının kendi listeleri ve üye olduğu ortak listeler."""
    return or_(
        ShoppingList.user_id == user.id,
        ShoppingList.id.in_(select(ListMember.list_id).where(ListMember.user_id == user.id)),
    )


async def get_owned_list(
    db: AsyncSession, user: User, list_id: int, *, owner_only: bool = False
) -> ShoppingList:
    """Liste sahibine ve ortak liste üyelerine açıktır; silmek gibi işlemler yalnızca sahibine."""
    shopping_list = await db.scalar(
        select(ShoppingList)
        .where(ShoppingList.id == list_id, _visible_to(user))
        .options(*_list_options())
        .execution_options(populate_existing=True)
    )
    if shopping_list is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liste bulunamadı")
    if owner_only and shopping_list.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu işlemi yalnızca listenin sahibi yapabilir")
    return shopping_list


# Karıştırılmayan harf ve rakamlar (0/O, 1/I yok)
SHARE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SHARE_CODE_LENGTH = 8


async def ensure_share_code(db: AsyncSession, shopping_list: ShoppingList) -> str:
    while shopping_list.share_code is None:
        code = "".join(secrets.choice(SHARE_CODE_ALPHABET) for _ in range(SHARE_CODE_LENGTH))
        if await db.scalar(select(ShoppingList.id).where(ShoppingList.share_code == code)) is None:
            shopping_list.share_code = code
    await db.commit()
    return shopping_list.share_code


async def join_list(db: AsyncSession, user: User, code: str) -> int:
    """Davet koduyla ortak listeye katılır; liste id'sini döner."""
    shopping_list = await db.scalar(
        select(ShoppingList)
        .where(ShoppingList.share_code == code.strip().upper())
        .options(selectinload(ShoppingList.members))
    )
    if shopping_list is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu kodla bir liste bulunamadı")
    if shopping_list.user_id != user.id and all(m.user_id != user.id for m in shopping_list.members):
        shopping_list.members.append(ListMember(user_id=user.id))
        await db.commit()
    return shopping_list.id


async def remove_member(db: AsyncSession, user: User, shopping_list: ShoppingList, member_id: int) -> None:
    """Sahip herhangi bir üyeyi çıkarabilir; üye yalnızca kendini ("Listeden Ayrıl")."""
    if user.id not in (shopping_list.user_id, member_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Başka bir üyeyi yalnızca listenin sahibi çıkarabilir")
    member = next((m for m in shopping_list.members if m.user_id == member_id), None)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu kullanıcı listenin üyesi değil")
    shopping_list.members.remove(member)
    await db.commit()


def get_item(shopping_list: ShoppingList, item_id: int) -> ShoppingListItem:
    for item in shopping_list.items:
        if item.id == item_id:
            return item
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün listede bulunamadı")


async def get_group(db: AsyncSession, group_id: int) -> ProductGroup:
    group = await db.scalar(
        select(ProductGroup)
        .where(ProductGroup.id == group_id)
        .options(selectinload(ProductGroup.members).selectinload(GroupMember.product))
    )
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün grubu bulunamadı")
    return group


def validate_brand(group: ProductGroup, brand: str | None) -> str | None:
    """Kilitlenen marka grupta gerçekten var mı? Grubun yazımıyla döner."""
    if brand is None:
        return None
    for member in group.members:
        if member.product.brand and member.product.brand.casefold() == brand.strip().casefold():
            return member.product.brand
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT, f"'{brand}' markası bu ürün grubunda bulunmuyor"
    )


def validate_product(group: ProductGroup, product_id: int) -> Product:
    """Kilitlenen ürün bu grubun üyesi mi?"""
    for member in group.members:
        if member.product_id == product_id:
            return member.product
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Seçilen ürün bu ürün grubunda bulunmuyor")


def set_preference(
    item: ShoppingListItem, group: ProductGroup, changes: dict
) -> bool:
    """Marka/ürün kilidini `changes`e göre ayarlar; tercih değiştiyse True döner.

    Ürün kilidi markayı da kilitler. Yalnızca marka gönderilirse ürün kilidi kalkar;
    preferred_product_id: null (marka gönderilmeden) "Farketmez"e döndürür."""
    before = (item.preferred_brand, item.preferred_product_id)
    if changes.get("preferred_product_id") is not None:
        product = validate_product(group, changes["preferred_product_id"])
        item.preferred_product_id = product.id
        item.preferred_brand = product.brand
    elif "preferred_brand" in changes:
        item.preferred_product_id = None
        item.preferred_brand = validate_brand(group, changes["preferred_brand"])
    elif "preferred_product_id" in changes:
        item.preferred_product_id = None
        item.preferred_brand = None
    return before != (item.preferred_brand, item.preferred_product_id)


def reset_plan(shopping_list: ShoppingList) -> None:
    """Kalem eklenir/silinir ya da miktar/marka değişirse uygulanan plan ve beklenen tasarruf
    geçersiz olur; liste yeniden optimize edilip uygulanmalıdır. İşaretler (alındı) korunur."""
    if shopping_list.applied_plan is None:
        return
    shopping_list.applied_plan = None
    shopping_list.applied_at = None
    shopping_list.planned_total = None
    shopping_list.preference_total = None
    shopping_list.expected_savings = None
    if shopping_list.status is ListStatus.SHOPPING:
        shopping_list.status = ListStatus.ACTIVE
    for item in shopping_list.items:
        item.assigned_market_id = None
        item.assigned_product_id = None
        item.assigned_unit_price = None
        item.assigned_store_id = None


# --- Serileştirme -------------------------------------------------------------------------


def _display_name(user: User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.email.split("@")[0]


def _summary_fields(shopping_list: ShoppingList) -> dict:
    return dict(
        id=shopping_list.id,
        owner_id=shopping_list.user_id,
        owner_name=_display_name(shopping_list.user),
        member_count=len(shopping_list.members),
        name=shopping_list.name,
        icon=shopping_list.icon,
        status=shopping_list.status,
        applied_plan=shopping_list.applied_plan,
        planned_total=shopping_list.planned_total,
        item_count=len(shopping_list.items),
        checked_count=sum(1 for i in shopping_list.items if i.is_checked),
        created_at=shopping_list.created_at,
        updated_at=shopping_list.updated_at,
    )


def to_summary(shopping_list: ShoppingList, resolver: PriceResolver | None = None) -> ListSummary:
    summary = ListSummary(**_summary_fields(shopping_list))
    if resolver is not None and shopping_list.items:
        plan = optimizer.opportunist_plan(_item_inputs(shopping_list, resolver))
        summary.estimated_total = plan.total
        by_market = plan.lines_by_market()
        if by_market:
            summary.top_market_id = min(by_market, key=lambda m: (-len(by_market[m]), m))
    return summary


async def list_summaries(db: AsyncSession, user: User) -> list[ListSummary]:
    rows = (
        await db.scalars(
            select(ShoppingList)
            .where(_visible_to(user))
            .options(*_list_options())
            .order_by(ShoppingList.updated_at.desc(), ShoppingList.id.desc())
        )
    ).all()
    product_ids = [m.product_id for sl in rows for item in sl.items for m in item.group.members]
    resolver = await build_resolver(db, user.id, product_ids)
    return [to_summary(sl, resolver) for sl in rows]


def _item_out(item: ShoppingListItem) -> ItemOut:
    assigned = None
    if item.assigned_market_id is not None:
        product = item.assigned_product
        assigned = AssignedProduct(
            market_id=item.assigned_market_id,
            product_id=item.assigned_product_id,
            product_name=product.name if product else None,
            brand=product.brand if product else None,
            unit_price=item.assigned_unit_price,
            store_id=item.assigned_store_id,
            store_name=item.assigned_store.name if item.assigned_store else None,
        )
    return ItemOut(
        id=item.id,
        group_id=item.group_id,
        group_name=item.group.name,
        category_id=item.group.category_id,
        image_url=item.group.image_url,
        quantity=item.quantity,
        preferred_brand=item.preferred_brand,
        preferred_product_id=item.preferred_product_id,
        is_checked=item.is_checked,
        position=item.position,
        note=item.note,
        added_by_id=item.added_by_user_id,
        added_by_name=_display_name(item.added_by),
        assigned=assigned,
    )


def _shopping_groups(shopping_list: ShoppingList) -> list[ShoppingGroup]:
    """Plan uygulandıysa kalemleri markete göre gruplar. Alınan ürünler yerinde kalır (sıra korunur)."""
    if shopping_list.applied_plan is None:
        return []
    groups: dict[int | None, list[ShoppingListItem]] = {}
    for item in shopping_list.items:  # position sırasına göre gelir
        groups.setdefault(item.assigned_market_id, []).append(item)
    ordered = sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))
    return [
        ShoppingGroup(
            market_id=market_id,
            item_ids=[i.id for i in items],
            checked_count=sum(1 for i in items if i.is_checked),
        )
        for market_id, items in ordered
    ]


def to_detail(shopping_list: ShoppingList) -> ListDetail:
    return ListDetail(
        **_summary_fields(shopping_list),
        preference_total=shopping_list.preference_total,
        expected_savings=shopping_list.expected_savings,
        applied_at=shopping_list.applied_at,
        completed_at=shopping_list.completed_at,
        items=[_item_out(i) for i in shopping_list.items],
        shopping_groups=_shopping_groups(shopping_list),
        share_code=shopping_list.share_code,
        members=[
            ListMemberOut(user_id=m.user_id, name=_display_name(m.user), joined_at=m.created_at)
            for m in shopping_list.members
        ],
    )


# --- Optimizasyon -------------------------------------------------------------------------


# "Pirinç 1 kg" ile "Baldo Pirinç 1 Kg" gibi aynı miktardaki benzer gruplar (pg_trgm word_similarity)
SIMILAR_GROUP_THRESHOLD = 0.8
SIMILAR_GROUP_LIMIT = 30


async def similar_groups(db: AsyncSession, groups: list[ProductGroup]) -> dict[int, list[ProductGroup]]:
    """Her grup için adı grubun adını kapsayan, miktarı ve birimi aynı diğer gruplar.

    Tek Market'te bir ürün o markette hiç yoksa benzeri buradan alınır. Miktarı bilinmeyen gruplar
    için aranmaz; yanlış eşleşme riski yüksek.
    """
    result: dict[int, list[ProductGroup]] = {}
    for group in {g.id: g for g in groups}.values():
        if group.quantity is None or group.unit is None:
            continue
        result[group.id] = list(
            await db.scalars(
                select(ProductGroup)
                .where(
                    ProductGroup.id != group.id,
                    ProductGroup.quantity == group.quantity,
                    ProductGroup.unit == group.unit,
                    func.word_similarity(group.normalized_name, ProductGroup.normalized_name)
                    >= SIMILAR_GROUP_THRESHOLD,
                )
                .options(selectinload(ProductGroup.members).selectinload(GroupMember.product))
                .limit(SIMILAR_GROUP_LIMIT)
            )
        )
    return result


def _offers(members: list[GroupMember], resolver: PriceResolver) -> list[Offer]:
    offers = []
    for member in members:
        resolved = resolver.price(member.product)
        if resolved is None:
            continue
        offers.append(
            Offer(
                product_id=member.product.id,
                product_name=member.product.name,
                brand=member.product.brand,
                market_id=member.product.market_id,
                unit_price=resolved.price,
                store_id=resolved.store_id,
            )
        )
    return offers


def _item_inputs(
    shopping_list: ShoppingList, resolver: PriceResolver, similar: dict[int, list[ProductGroup]] | None = None
) -> list[ItemInput]:
    similar = similar or {}
    inputs = []
    for item in shopping_list.items:
        offers = _offers(item.group.members, resolver)
        similar_offers = [o for g in similar.get(item.group_id, []) for o in _offers(g.members, resolver)]
        inputs.append(
            ItemInput(
                item_id=item.id,
                group_id=item.group_id,
                group_name=item.group.name,
                quantity=item.quantity,
                preferred_brand=item.preferred_brand,
                offers=tuple(offers),
                preferred_product_id=item.preferred_product_id,
                similar_offers=tuple(similar_offers),
            )
        )
    return inputs


async def run_optimizer(
    db: AsyncSession, shopping_list: ShoppingList, user_id: int | None = None
) -> OptimizationResult:
    """user_id: fiyatları kimin şubelerinden alınacağı (ortak listede listeyi açan kişi)."""
    similar = await similar_groups(db, [item.group for item in shopping_list.items])
    product_ids = [m.product_id for item in shopping_list.items for m in item.group.members]
    product_ids += [m.product_id for groups in similar.values() for g in groups for m in g.members]
    resolver = await build_resolver(db, user_id or shopping_list.user_id, product_ids)
    market_ids = await candidate_market_ids(db, resolver)
    return optimizer.optimize(_item_inputs(shopping_list, resolver, similar), market_ids)


def _plan_out(plan: Plan) -> PlanOut:
    return PlanOut(
        plan_type=plan.plan_type,
        total=plan.total,
        missing_item_ids=plan.missing_item_ids,
        lines=[
            PlanLineOut(
                item_id=line.item_id,
                group_id=line.group_id,
                group_name=line.group_name,
                quantity=line.quantity,
                product_id=line.offer.product_id,
                product_name=line.offer.product_name,
                brand=line.offer.brand,
                market_id=line.offer.market_id,
                unit_price=line.offer.unit_price,
                store_id=line.offer.store_id,
                line_total=line.line_total,
                substituted=line.substituted,
            )
            for line in plan.lines
        ],
        by_market=[
            MarketBreakdown(
                market_id=market_id,
                total=sum((line.line_total for line in lines), Decimal("0.00")),
                item_ids=[line.item_id for line in lines],
            )
            for market_id, lines in sorted(plan.lines_by_market().items())
        ],
    )


def to_optimize_out(result: OptimizationResult) -> OptimizeOut:
    single = result.single_market
    savings = result.savings
    return OptimizeOut(
        single_market=SingleMarketOut(
            available=single.plan is not None,
            warning=single.warning,
            plan=_plan_out(single.plan) if single.plan else None,
            markets=[
                MarketTotalOut(
                    market_id=m.market_id, total=m.total, found=m.found, missing=m.missing, substituted=m.substituted
                )
                for m in single.markets
            ],
        ),
        combination=_plan_out(result.combination),
        opportunist=_plan_out(result.opportunist),
        savings=SavingsProjection(
            preference_total=savings.preference_total,
            opportunist_total=savings.optimized_total,
            weekly=savings.weekly,
            monthly=savings.monthly,
            yearly=savings.yearly,
        ),
    )


async def apply_plan(
    db: AsyncSession, shopping_list: ShoppingList, plan_type: PlanType, user_id: int | None = None
) -> None:
    """"Listeye Uygula": her kaleme marketini ve ürününü atar, listeyi Alışveriş Modu'na alır."""
    result = await run_optimizer(db, shopping_list, user_id)
    plan = result.plan(plan_type)
    if plan is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            result.single_market.warning or optimizer.NO_COMPLETE_MARKET_WARNING,
        )
    if not plan.lines:
        raise HTTPException(status.HTTP_409_CONFLICT, "Planda uygulanacak ürün yok")

    lines = {line.item_id: line for line in plan.lines}
    for item in shopping_list.items:
        line = lines.get(item.id)
        item.assigned_market_id = line.offer.market_id if line else None
        item.assigned_product_id = line.offer.product_id if line else None
        item.assigned_unit_price = line.offer.unit_price if line else None
        item.assigned_store_id = line.offer.store_id if line else None

    shopping_list.applied_plan = plan_type
    shopping_list.applied_at = datetime.now(timezone.utc)
    shopping_list.status = ListStatus.SHOPPING
    shopping_list.planned_total = plan.total
    shopping_list.preference_total = result.savings.preference_total
    # Tasarruf yalnızca Fırsatçı planında doğar
    shopping_list.expected_savings = (
        result.savings.weekly if plan_type is PlanType.OPPORTUNIST else Decimal("0.00")
    )
    await db.commit()


async def vault_total(db: AsyncSession, user: User) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(SavingsRecord.saved_amount), 0)).where(
            SavingsRecord.user_id == user.id
        )
    )
    return Decimal(total).quantize(Decimal("0.01"))


# Haftalık alışveriş listesi: bir liste bu süre içinde kasaya yalnızca bir kez tasarruf yazar
SAVINGS_COOLDOWN = timedelta(days=6)


async def complete_list(db: AsyncSession, user: User, shopping_list: ShoppingList) -> CompleteResponse:
    """"Alışverişi Bitir": Fırsatçı tasarrufunu kalıcı kasaya ekler ve Alışveriş Modu'ndan çıkar.

    Liste silinmez; gelecek hafta yeniden optimize edilip kullanılabilir. Plan sıfırlandığı için
    aynı alışveriş ikinci kez kasaya yazılamaz (çift tıklama 409 döner). Planı yeniden uygulayıp
    bitirerek kasayı şişirmemek için bir liste SAVINGS_COOLDOWN içinde yalnızca bir kez kasaya yazılır;
    o sürede bitirilen alışveriş tamamlanır ama tasarruf eklenmez."""
    if shopping_list.applied_plan is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu listede uygulanmış bir alışveriş planı yok")

    saved = shopping_list.expected_savings or Decimal("0.00")
    note = None
    last_saved_at = await db.scalar(
        select(func.max(SavingsRecord.created_at)).where(
            SavingsRecord.user_id == user.id, SavingsRecord.list_id == shopping_list.id
        )
    )
    if last_saved_at and last_saved_at > datetime.now(timezone.utc) - SAVINGS_COOLDOWN and saved > 0:
        saved = Decimal("0.00")
        note = "Bu listenin bu haftaki tasarrufu zaten kasada; aynı hafta tekrar eklenmez."
    if shopping_list.applied_plan is PlanType.OPPORTUNIST and saved > 0:
        db.add(
            SavingsRecord(
                user_id=user.id,
                list_id=shopping_list.id,
                list_name=shopping_list.name,
                plan_type=PlanType.OPPORTUNIST,
                preference_total=shopping_list.preference_total,
                optimized_total=shopping_list.preference_total - saved,
                saved_amount=saved,
                item_count=len(shopping_list.items),
            )
        )
    else:
        saved = Decimal("0.00")

    shopping = await shopping_savings(db, shopping_list)
    shopping_list.completed_at = datetime.now(timezone.utc)
    reset_plan(shopping_list)
    # Alışveriş bitti: liste gelecek hafta için "alınacaklar" hâline döner (İptal Et'ten farklı olarak)
    for item in shopping_list.items:
        item.is_checked = False
    await db.commit()
    return CompleteResponse(
        list_id=shopping_list.id,
        saved_amount=saved,
        shopping_savings=shopping,
        vault_total=await vault_total(db, user),
        note=note,
    )


async def shopping_savings(db: AsyncSession, shopping_list: ShoppingList) -> Decimal:
    """Uygulanan planla bu alışverişte kazanılan: her kalem için seçilebilecek ürünlerin (kullanıcının
    şubelerindeki) ortalama fiyatı ile plandaki fiyat farkı. Kasadaki "tercihlere göre" tasarruftan
    bağımsızdır; Farketmez kalemlerde ve kasa haftalık sınırdayken de kutlamada gösterilir."""
    product_ids = [m.product_id for item in shopping_list.items for m in item.group.members]
    resolver = await build_resolver(db, shopping_list.user_id, product_ids)
    inputs = {i.item_id: i for i in _item_inputs(shopping_list, resolver)}
    total = Decimal("0.00")
    for item in shopping_list.items:
        offers = inputs[item.id].offers
        if item.assigned_unit_price is None or not offers:
            continue
        average = sum((o.unit_price for o in offers), Decimal(0)) / len(offers)
        total += max(average - item.assigned_unit_price, Decimal(0)) * item.quantity
    return total.quantize(Decimal("0.01"))
