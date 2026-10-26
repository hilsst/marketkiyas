from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    GroupMember,
    Market,
    PlanType,
    Product,
    ProductGroup,
    SavingsRecord,
    ShoppingList,
    ShoppingListItem,
    Unit,
    User,
)


async def test_seeded_markets(client):
    r = await client.get("/api/markets")
    assert [m["slug"] for m in r.json()] == ["bim", "a101", "sok", "file"]
    assert len((await client.get("/api/categories")).json()) > 0
    assert (await client.get("/api/health")).json()["database"] == "ok"


async def _user(db) -> User:
    user = User(email="u@example.com", password_hash="x")
    db.add(user)
    await db.flush()
    return user


async def test_savings_survive_list_deletion(db):
    user = await _user(db)
    lst = ShoppingList(user_id=user.id, name="Haftalık")
    db.add(lst)
    await db.flush()
    db.add(
        SavingsRecord(
            user_id=user.id,
            list_id=lst.id,
            list_name=lst.name,
            plan_type=PlanType.OPPORTUNIST,
            preference_total=Decimal("412.50"),
            optimized_total=Decimal("356.75"),
            saved_amount=Decimal("55.75"),
        )
    )
    await db.commit()

    await db.delete(lst)
    await db.commit()

    record = await db.scalar(select(SavingsRecord))
    assert record.list_id is None
    assert record.list_name == "Haftalık"
    assert record.saved_amount == Decimal("55.75")


async def test_list_can_be_saved_to_vault_only_once(db):
    user = await _user(db)
    lst = ShoppingList(user_id=user.id, name="L")
    db.add(lst)
    await db.flush()
    kwargs = dict(
        user_id=user.id,
        list_id=lst.id,
        list_name="L",
        plan_type=PlanType.OPPORTUNIST,
        preference_total=10,
        optimized_total=8,
        saved_amount=2,
    )
    db.add(SavingsRecord(**kwargs))
    await db.flush()
    db.add(SavingsRecord(**kwargs))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_grouping_and_trgm_similarity(db):
    bim, a101 = (await db.scalars(select(Market).where(Market.slug.in_(["bim", "a101"])).order_by(Market.id))).all()
    group = ProductGroup(name="Süt 1 L", normalized_name="sut 1000ml", quantity=1000, unit=Unit.ML)
    p1 = Product(market_id=bim.id, external_id="1", name="Sütaş Süt 1 L", normalized_name="sutas sut 1000ml", brand="Sütaş", quantity=1000, unit=Unit.ML, current_price=Decimal("32.50"))
    p2 = Product(market_id=a101.id, external_id="9", name="Pınar Süt 1L", normalized_name="pinar sut 1000ml", brand="Pınar", quantity=1000, unit=Unit.ML, current_price=Decimal("34.90"))
    db.add_all([group, p1, p2])
    await db.flush()
    db.add_all([GroupMember(group_id=group.id, product_id=p1.id), GroupMember(group_id=group.id, product_id=p2.id)])
    await db.flush()

    # Liste kalemi gruba bağlanır; marka kilidi opsiyonel
    lst = ShoppingList(user_id=(await _user(db)).id, name="L")
    db.add(lst)
    await db.flush()
    db.add_all([
        ShoppingListItem(list_id=lst.id, group_id=group.id),  # Farketmez
        ShoppingListItem(list_id=lst.id, group_id=group.id, preferred_brand="Pınar", position=1),
    ])
    await db.flush()

    cheapest = await db.scalar(
        select(func.min(Product.current_price)).join(GroupMember).where(GroupMember.group_id == group.id)
    )
    assert cheapest == Decimal("32.50")

    sim = await db.scalar(
        select(func.similarity(Product.normalized_name, "pınar süt 1000ml".replace("ı", "i").replace("ü", "u"))).where(Product.id == p2.id)
    )
    assert sim > 0.9
    # Aynı ürün iki gruba giremez
    db.add(GroupMember(group_id=group.id, product_id=p1.id))
    with pytest.raises(IntegrityError):
        await db.flush()
