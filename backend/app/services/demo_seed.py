"""Next.js demosundaki örnek katalog ve listeleri veritabanına yükler (yerel geliştirme / deneme).

    python -m app.cli seed-demo

Gerçek fiyatlar değildir; scraper'ların yazdığı ürünlerle karışmasın diye external_id'ler "demo-"
ile başlar. Tekrar çalıştırmak bir şey değiştirmez.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import (
    Category,
    GroupMember,
    Market,
    PriceHistory,
    Product,
    ProductGroup,
    ShoppingList,
    ShoppingListItem,
    Unit,
    User,
)
from app.services.normalize import normalize_name

DEMO_EMAIL = "demo@marketkiyas.app"
DEMO_PASSWORD = "demo1234"

# demo kategorisi -> categories.slug
CATEGORY_SLUGS = {
    "Süt Ürünleri": "sut-kahvaltilik",
    "Ekmek & Fırın": "firin",
    "Temizlik": "temizlik",
    "Yağ & Bakliyat": "temel-gida",
}

# id, ad, kategori, birim, miktar
GROUPS = [
    (1, "Tam Yağlı Süt 1L", "Süt Ürünleri", Unit.ML, 1000),
    (2, "Yarım Yağlı Süt 1L", "Süt Ürünleri", Unit.ML, 1000),
    (3, "Yumurta 15'li", "Süt Ürünleri", Unit.PIECE, 15),
    (4, "Beyaz Ekmek 200g", "Ekmek & Fırın", Unit.G, 200),
    (5, "Tam Buğday Ekmek", "Ekmek & Fırın", Unit.G, 350),
    (6, "Sıvı Bulaşık Det. 750ml", "Temizlik", Unit.ML, 750),
    (7, "Çamaşır Det. 3L", "Temizlik", Unit.ML, 3000),
    (8, "Ayçiçek Yağı 1L", "Yağ & Bakliyat", Unit.ML, 1000),
    (9, "Pirinç 1kg", "Yağ & Bakliyat", Unit.G, 1000),
    (10, "Makarna 500g", "Yağ & Bakliyat", Unit.G, 500),
]

# id, grup, market, marka, fiyat, indirim öncesi fiyat
PRODUCTS = [
    (101, 1, "bim", "Dost", "31.90", None),
    (102, 1, "a101", "Sütaş", "32.50", None),
    (103, 1, "sok", "Pınar", "34.00", None),
    (104, 1, "file", "İçim", "36.75", None),
    (201, 2, "bim", "Dost", "30.50", None),
    (202, 2, "a101", "Sütaş", "31.00", None),
    (203, 2, "sok", "Pınar", "32.50", None),
    (301, 3, "bim", "Keskinoğlu", "42.50", None),
    (302, 3, "a101", "Yumurta", "43.90", None),
    (303, 3, "sok", "Ceyhan", "45.00", None),
    (304, 3, "file", "Güres", "48.00", None),
    (401, 4, "bim", "Uno", "12.50", None),
    (402, 4, "a101", "Uno", "12.00", None),
    (403, 4, "sok", "Halk", "12.50", None),
    (404, 4, "file", "Uno", "14.00", None),
    (501, 5, "bim", "Uno", "18.50", None),
    (502, 5, "a101", "Eti", "17.90", None),
    (503, 5, "file", "Uno", "21.00", None),
    (601, 6, "bim", "Fairy", "65.00", None),
    (602, 6, "a101", "Finish", "58.90", "72.00"),
    (603, 6, "sok", "Pril", "62.00", None),
    (604, 6, "file", "Fairy", "69.90", None),
    (701, 7, "bim", "Omo", "189.00", None),
    (702, 7, "a101", "Persil", "175.00", "210.00"),
    (703, 7, "sok", "Ariel", "199.90", None),
    (704, 7, "file", "Omo", "210.00", None),
    (801, 8, "bim", "Yudum", "89.50", None),
    (802, 8, "a101", "Kırlangıç", "85.00", None),
    (803, 8, "sok", "Bizim", "88.00", None),
    (804, 8, "file", "Torku", "92.00", None),
    (901, 9, "bim", "Duru", "42.00", None),
    (902, 9, "a101", "Torku", "40.50", None),
    (903, 9, "sok", "Reis", "43.00", None),
    (904, 9, "file", "Duru", "45.00", None),
    (1001, 10, "bim", "Filiz", "8.90", None),
    (1002, 10, "a101", "Filiz", "8.50", None),
    (1003, 10, "sok", "Barilla", "9.00", None),
    (1004, 10, "file", "Filiz", "10.50", None),
]

# liste adı, [(grup, miktar)]
LISTS = [
    ("Haftalık Alışveriş", [(1, 1), (3, 2), (4, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 2)]),
    ("Hafta Sonu", [(2, 1), (5, 1), (10, 1)]),
]

HISTORY_DAYS = 30


def price_history(product_id: int, base: Decimal) -> list[Decimal]:
    """Demodaki sparkline üreteciyle aynı eğri; son nokta bugünkü fiyat."""
    b = float(base)
    points = [
        max(b * 0.85, b - math.sin((product_id + i) * 0.7) * (b * 0.05) + (i / HISTORY_DAYS) * (b * 0.03))
        for i in range(HISTORY_DAYS)
    ]
    points[-1] = b
    return [Decimal(str(round(p, 2))) for p in points]


async def seed_demo(db: AsyncSession) -> dict[str, int]:
    if await db.scalar(select(Product.id).where(Product.external_id.like("demo-%")).limit(1)):
        return {"groups": 0, "products": 0, "lists": 0}

    markets = {m.slug: m.id for m in await db.scalars(select(Market))}
    categories = {c.slug: c.id for c in await db.scalars(select(Category))}
    now = datetime.now(timezone.utc)

    groups: dict[int, ProductGroup] = {}
    for demo_id, name, category, unit, qty in GROUPS:
        group = ProductGroup(
            name=name,
            normalized_name=normalize_name(name),
            category_id=categories.get(CATEGORY_SLUGS[category]),
            unit=unit,
            quantity=qty,
        )
        db.add(group)
        groups[demo_id] = group
    await db.flush()

    for demo_id, group_id, market, brand, price, old_price in PRODUCTS:
        group = groups[group_id]
        name = f"{brand} {group.name}"
        product = Product(
            market_id=markets[market],
            category_id=group.category_id,
            external_id=f"demo-{demo_id}",
            name=name,
            normalized_name=normalize_name(name),
            brand=brand,
            quantity=group.quantity,
            unit=group.unit,
            current_price=Decimal(price),
            last_seen_at=now,
        )
        db.add(product)
        await db.flush()
        db.add(GroupMember(group_id=group.id, product_id=product.id, is_manual=True))
        history = price_history(demo_id, Decimal(price))
        for i, point in enumerate(history):
            last = i == len(history) - 1
            db.add(
                PriceHistory(
                    product_id=product.id,
                    price=point,
                    regular_price=Decimal(old_price) if last and old_price else None,
                    is_campaign=bool(last and old_price),
                    recorded_at=now - timedelta(days=len(history) - 1 - i),
                )
            )

    user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), full_name="Demo Kullanıcı")
        db.add(user)
        await db.flush()
    for list_name, items in LISTS:
        db.add(
            ShoppingList(
                user_id=user.id,
                name=list_name,
                items=[
                    ShoppingListItem(group_id=groups[g].id, quantity=qty, position=i)
                    for i, (g, qty) in enumerate(items)
                ],
            )
        )
    await db.commit()
    return {"groups": len(GROUPS), "products": len(PRODUCTS), "lists": len(LISTS)}
