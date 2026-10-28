"""Ürün gruplarının bakımı: yanlış gruba girmiş ürünleri ayırır, aynı ürünü anlatan grupları birleştirir.

Gruplar ilk kez eklenirken eşleştirilir (marketfiyati/ingest.py). Eşleştirme kuralı değiştiğinde ya da
zincirler aynı ürünü farklı adlarla getirdiğinde ("UHT Süt %3.1 Yağlı" ile "Tam Yağlı Süt") eski gruplar
bu modülle düzeltilir. Elle eklenen üyeler (is_manual) ve listelerde/alarmlarda kullanılan gruplar korunur:
birleşmede listeler ve alarmlar hayatta kalan gruba taşınır.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GroupMember, PriceAlert, Product, ProductGroup, ShoppingListItem
from app.services.normalize import normalize_name, same_product, turkish_lower

log = logging.getLogger(__name__)


@dataclass
class RegroupStats:
    detached: int = 0
    groups_created: int = 0
    groups_merged: int = 0
    groups_deleted: int = 0


def _display_name(product: Product) -> str:
    """Markasız ürün adı: ('Pınar Süt 1 L', 'Pınar') -> 'Süt 1 L'."""
    if not product.brand:
        return product.name
    needle = turkish_lower(product.brand.strip())
    start = turkish_lower(product.name).find(needle)
    if start < 0:
        return product.name
    return re.sub(r"\s+", " ", f"{product.name[:start]} {product.name[start + len(needle):]}").strip() or product.name


def _compatible(a: ProductGroup, b: ProductGroup) -> bool:
    return (
        a.quantity == b.quantity
        and a.unit == b.unit
        and (a.category_id is None or b.category_id is None or a.category_id == b.category_id)
        and (a.normalized_name == b.normalized_name or same_product(a.normalized_name, b.normalized_name))
    )


async def regroup(db: AsyncSession) -> RegroupStats:
    stats = RegroupStats()
    groups = list(
        await db.scalars(
            select(ProductGroup)
            .options(selectinload(ProductGroup.members).selectinload(GroupMember.product))
            # Oturumda önceden yüklenmiş gruplar varsa üyeleri veritabanından tazelensin
            .execution_options(populate_existing=True)
        )
    )
    buckets: dict[tuple, list[ProductGroup]] = defaultdict(list)
    for g in groups:
        buckets[(g.quantity, g.unit)].append(g)

    # 1) Grubuyla aynı ürünü anlatmayan otomatik üyeleri ayır ve uygun gruba (yoksa yeni gruba) koy
    for group in list(groups):  # yeni oluşturulan gruplar bu turda gezilmez
        for member in list(group.members):
            product = member.product
            if member.is_manual or product.quantity != group.quantity or product.unit != group.unit:
                continue
            name = _display_name(product)
            key = normalize_name(name)
            if key == group.normalized_name or same_product(key, group.normalized_name):
                continue
            target = next(
                (
                    g
                    for g in buckets[(product.quantity, product.unit)]
                    if g is not group
                    and same_product(key, g.normalized_name)
                    and (g.category_id is None or product.category_id is None or g.category_id == product.category_id)
                ),
                None,
            )
            if target is None:
                target = ProductGroup(
                    name=name,
                    normalized_name=key,
                    quantity=product.quantity,
                    unit=product.unit,
                    image_url=product.image_url,
                    category_id=product.category_id,
                )
                db.add(target)
                await db.flush()
                buckets[(target.quantity, target.unit)].append(target)
                groups.append(target)
                stats.groups_created += 1
            await db.execute(update(GroupMember).where(GroupMember.id == member.id).values(group_id=target.id))
            stats.detached += 1
    await db.flush()

    # 2) Aynı ürünü anlatan grupları birleştir (her kümenin ilk grubu kalır)
    for bucket in buckets.values():
        survivors: list[ProductGroup] = []
        for group in sorted(bucket, key=lambda g: g.id):
            survivor = next((s for s in survivors if _compatible(s, group)), None)
            if survivor is None:
                survivors.append(group)
                continue
            await _merge(db, survivor, group)
            stats.groups_merged += 1

    # 3) Boş kalan ve hiçbir yerde kullanılmayan grupları sil
    used = select(ShoppingListItem.group_id).union(select(PriceAlert.group_id), select(GroupMember.group_id))
    result = await db.execute(delete(ProductGroup).where(ProductGroup.id.not_in(used)))
    stats.groups_deleted = result.rowcount or 0
    await db.commit()
    log.info("gruplar düzenlendi: %s", stats)
    return stats


async def _merge(db: AsyncSession, survivor: ProductGroup, loser: ProductGroup) -> None:
    await db.execute(update(GroupMember).where(GroupMember.group_id == loser.id).values(group_id=survivor.id))
    await db.execute(
        update(ShoppingListItem).where(ShoppingListItem.group_id == loser.id).values(group_id=survivor.id)
    )
    # Aynı kullanıcının iki grupta da alarmı varsa hayatta kalanınki yeterli
    survivor_users = select(PriceAlert.user_id).where(PriceAlert.group_id == survivor.id)
    await db.execute(
        delete(PriceAlert).where(PriceAlert.group_id == loser.id, PriceAlert.user_id.in_(survivor_users))
    )
    await db.execute(update(PriceAlert).where(PriceAlert.group_id == loser.id).values(group_id=survivor.id))
    if survivor.subcategory_id is None and loser.subcategory_id is not None:
        survivor.subcategory_id = loser.subcategory_id
    if survivor.category_id is None and loser.category_id is not None:
        survivor.category_id = loser.category_id
    if survivor.image_url is None:
        survivor.image_url = loser.image_url
