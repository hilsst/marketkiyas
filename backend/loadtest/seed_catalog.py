"""Yük testi için katalog: her tarifin her malzemesine (arama ifadesiyle) iki markette birer ürün açar,
böylece 84 tarifin hepsi planlarda görünür. Gerçek fiyat değildir; yalnız yük testi/e2e içindir.

    python -m loadtest.seed_catalog      # backend/ klasöründen
"""
import asyncio
import random
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models import GroupMember, Market, Product, ProductGroup, Recipe
from app.services.meals import refresh_availability
from app.services.normalize import normalize_name


async def main() -> None:
    rnd = random.Random(7)
    async with SessionLocal() as db:
        markets = (await db.scalars(select(Market).where(Market.slug.in_(["bim", "a101", "sok"])))).all()
        recipes = (await db.scalars(select(Recipe).options(selectinload(Recipe.ingredients)))).all()
        seen: set[str] = {n for (n,) in (await db.execute(select(ProductGroup.normalized_name))).all()}
        added = 0
        for ing in (i for r in recipes for i in r.ingredients if not i.is_pantry):
            name = f"{ing.search_term.title()} 1 kg" if ing.unit.value == "g" else f"{ing.search_term.title()} 1 L" \
                if ing.unit.value == "ml" else f"{ing.search_term.title()} 10'lu"
            key = normalize_name(name)
            if key in seen:
                continue
            seen.add(key)
            qty = {"g": 1000, "ml": 1000}.get(ing.unit.value, 10)
            group = ProductGroup(name=name, normalized_name=key, unit=ing.unit, quantity=qty)
            db.add(group)
            await db.flush()
            for m in markets:
                product = Product(
                    market_id=m.id, external_id=f"yuk-{group.id}-{m.slug}", name=name, normalized_name=key,
                    current_price=Decimal(rnd.randint(1500, 20000)) / 100,
                )
                db.add(product)
                await db.flush()
                db.add(GroupMember(group_id=group.id, product_id=product.id))
            added += 1
        await db.commit()
        print("grup:", added, await refresh_availability(db))


if __name__ == "__main__":
    asyncio.run(main())
