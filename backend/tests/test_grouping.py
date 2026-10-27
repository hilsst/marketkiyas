from decimal import Decimal as D

from sqlalchemy import select

from app.models import GroupMember, Market, Product, ProductGroup, ShoppingList, ShoppingListItem, Unit, User
from app.services.grouping import regroup


async def _product(db, market_id, name, brand, group):
    p = Product(market_id=market_id, external_id=name, name=name, normalized_name=name.lower(), brand=brand,
                quantity=group.quantity, unit=group.unit, is_available=True)
    db.add(p)
    await db.flush()
    db.add(GroupMember(group_id=group.id, product_id=p.id, is_manual=False))
    return p


async def test_regroup_splits_wrong_members_and_merges_same_products(db):
    bim = await db.scalar(select(Market.id).where(Market.slug == "bim"))
    sok = await db.scalar(select(Market.id).where(Market.slug == "sok"))
    milk = ProductGroup(name="Tam Yağlı Süt 1 L", normalized_name="tam yagli sut 1000ml", quantity=D(1000), unit=Unit.ML)
    uht = ProductGroup(name="UHT Süt %3.1 Yağlı 1 L", normalized_name="uht sut 3.1 yagli 1000ml", quantity=D(1000), unit=Unit.ML)
    small_milk = ProductGroup(name="Süt 500 Ml", normalized_name="sut 500ml", quantity=D(500), unit=Unit.ML)
    db.add_all([milk, uht, small_milk])
    await db.flush()
    milk_id, uht_id = milk.id, uht.id
    await _product(db, bim, "Dost Tam Yağlı Süt 1 L", "Dost", milk)
    await _product(db, sok, "Mis UHT Süt %3.1 Yağlı 1 L", "Mis", uht)
    await _product(db, sok, "Torku Süt 500 Ml", "Torku", small_milk)
    water = await _product(db, sok, "Erikli Su 500 Ml", "Erikli", small_milk)  # yanlışlıkla sütle gruplanmış
    water_id = water.id

    # Listedeki kalem birleşen gruba bağlı: hayatta kalan gruba taşınmalı
    user = User(email="g@test.app", password_hash="x")
    db.add(user)
    await db.flush()
    shopping_list = ShoppingList(user_id=user.id, name="L")
    db.add(shopping_list)
    await db.flush()
    db.add(ShoppingListItem(list_id=shopping_list.id, group_id=uht.id, position=0))
    await db.commit()

    stats = await regroup(db)
    assert stats.detached == 1 and stats.groups_merged == 1

    members = dict((await db.execute(select(GroupMember.product_id, GroupMember.group_id))).all())
    water_key = await db.scalar(select(ProductGroup.normalized_name).where(ProductGroup.id == members[water_id]))
    assert water_key == "su 500ml"
    assert await db.scalar(select(ProductGroup.id).where(ProductGroup.id == uht_id)) is None
    assert await db.scalar(select(ShoppingListItem.group_id)) == milk_id
    assert sum(1 for g in members.values() if g == milk_id) == 2

    # Tekrar çalıştırınca değişiklik yok
    again = await regroup(db)
    assert (again.detached, again.groups_merged) == (0, 0)
