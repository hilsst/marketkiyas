"""marketfiyati.org.tr verisini veritabanına aktarır.

Akış: arama sonucu (ürün + şube fiyatları) -> market (zincir) ve şube upsert -> ürün upsert
(zincir başına bir satır) -> şube fiyatı upsert -> ürünün güncel fiyatı ve fiyat geçmişi ->
ürün grubu eşleştirme (pg_trgm).
"""

import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Category,
    GroupMember,
    Market,
    PriceHistory,
    Product,
    ProductGroup,
    Store,
    StorePrice,
    Unit,
    UserStore,
)
from app.services.marketfiyati.client import MarketFiyatiClient
from app.services.marketfiyati.schemas import Depot, DepotPrice, SearchProduct
from app.services.normalize import (
    normalize_name,
    normalize_text,
    parse_quantity,
    same_product,
    turkish_lower,
)

log = logging.getLogger(__name__)

# Aday gruplar için en düşük trigram benzerliği; asıl karar same_product (kelime eşleşmesi).
# Miktar ve birim ayrıca birebir eşleşmeli.
GROUP_CANDIDATE_SIMILARITY = 0.3

# Kullanıcı şube seçince ve periyodik senkronizasyonda aranan temel ürünler
DEFAULT_KEYWORDS = (
    "süt", "yoğurt", "ayran", "peynir", "tereyağı", "yumurta", "zeytin", "bal", "reçel",
    "ekmek", "un", "makarna", "pirinç", "bulgur", "mercimek", "nohut", "fasulye", "şeker",
    "tuz", "ayçiçek yağı", "zeytinyağı", "salça", "çay", "kahve", "su", "maden suyu",
    "meyve suyu", "kola", "tavuk", "kıyma", "sucuk", "domates", "patates", "soğan", "muz",
    "elma", "bisküvi", "çikolata", "cips", "deterjan", "bulaşık deterjanı", "yumuşatıcı",
    "tuvalet kağıdı", "kağıt havlu", "şampuan", "diş macunu", "sabun", "bebek bezi",
)

# Sitenin kategori menüsü: bir şubenin tüm ürünleri bu kategoriler taranarak çekilir
MENU_CATEGORIES = (
    "Meyve ve Sebze", "Et, Tavuk ve Balık", "Süt Ürünleri ve Kahvaltılık", "Temel Gıda", "İçecek",
    "Atıştırmalık ve Tatlı", "Temizlik Ürünleri", "Kişisel Bakım", "Diğer Ürünler",
)
# Menü kategorisi -> uygulamanın kategori slug'ı (anahtarlar normalize_text ile, boşluksuz)
MENU_CATEGORY_SLUGS = {
    "meyvevesebze": "meyve-sebze",
    "ettavukvebalik": "et-tavuk-balik",
    "suturunlerivekahvaltilik": "sut-kahvaltilik",
    "temelgida": "temel-gida",
    "icecek": "icecek",
    "atistirmalikvetatli": "atistirmalik",
    "temizlikurunleri": "temizlik",
    "kisiselbakim": "kisisel-bakim",
}
# Alt kategori adında geçerse menü kategorisinden önce gelir ("Bebek Mamaları" Temel Gıda'da olsa da Bebek)
MAIN_CATEGORY_SLUGS = (
    ("bebek", "bebek"),
    ("dondurulmus", "dondurulmus"),
    ("ekmek", "firin"),
    ("unlu mamul", "firin"),
)

MARKET_ALIASES = {
    "sok": "sok",
    "sokmarket": "sok",
    "a101": "a101",
    "bim": "bim",
    "file": "file",
    "migros": "migros",
    "carrefour": "carrefour",
    "carrefoursa": "carrefour",
    "tarimkredi": "tarim_kredi",
    "tarimkredikooperatif": "tarim_kredi",
    "hakmar": "hakmar",
    "hakmarexpress": "hakmar",
}
MARKET_DISPLAY_NAMES = {
    "sok": "Şok",
    "a101": "A101",
    "bim": "BİM",
    "file": "File",
    "migros": "Migros",
    "carrefour": "CarrefourSA",
    "tarim_kredi": "Tarım Kredi",
    "hakmar": "Hakmar",
}


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(text))


def category_slug(product: SearchProduct) -> str | None:
    """marketfiyati kategorisini uygulamanın kategorisine çevirir; eşleşmezse None ("Pet Shop" gibi)."""
    main = normalize_text(product.main_category or "")
    for needle, slug in MAIN_CATEGORY_SLUGS:
        if needle in main:
            return slug
    return MENU_CATEGORY_SLUGS.get(_compact(product.menu_category or ""))


def market_slug(market_name: str) -> str:
    compact = _compact(market_name)
    return MARKET_ALIASES.get(compact) or re.sub(r"[^a-z0-9]+", "_", normalize_text(market_name)).strip("_")


def _strip_brand(title: str, brand: str | None) -> str:
    """Başlıktan markayı çıkarır, orijinal yazımı korur. ('Pınar Süt 1 L', 'Pınar') -> 'Süt 1 L'"""
    if not brand:
        return title
    needle = turkish_lower(brand.strip())
    start = turkish_lower(title).find(needle)
    if start < 0:
        return title
    return re.sub(r"\s+", " ", f"{title[:start]} {title[start + len(needle):]}").strip()


def group_key(product: SearchProduct) -> tuple[str, str, tuple[Decimal, Unit] | None]:
    """(görünen ad, normalize anahtar, miktar). Marka atılır: 'Pınar Süt 1 L' -> 'Süt 1 L', 'sut 1000ml'."""
    display = _strip_brand(product.title, product.brand) or product.title
    qty = parse_quantity(product.volume_or_weight or "") or parse_quantity(product.title)
    key = normalize_name(display)
    if qty and parse_quantity(display) is None:
        key = f"{key} {qty[0]}{qty[1].value}"
        if product.volume_or_weight:
            display = f"{display} {product.volume_or_weight}"
    return display, key, qty


@dataclass
class SyncStats:
    products_seen: int = 0
    products_upserted: int = 0
    store_prices: int = 0
    stores: int = 0
    groups_created: int = 0
    price_changes: int = 0
    markets_created: list[str] = field(default_factory=list)


class Ingestor:
    """Tek senkronizasyon boyunca market/şube/grup id'lerini önbellekte tutar."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.stats = SyncStats()
        self._markets: dict[str, int] = {}
        self._stores: dict[str, int] = {}
        self._groups: dict[tuple, int] = {}
        self._categories: dict[str, int] | None = None
        self._now = datetime.now(timezone.utc)

    async def market_id(self, market_name: str) -> int:
        slug = market_slug(market_name)
        if slug in self._markets:
            return self._markets[slug]
        market_id = await self.db.scalar(select(Market.id).where(Market.slug == slug))
        if market_id is None:
            market_id = await self.db.scalar(
                insert(Market)
                .values(slug=slug, name=MARKET_DISPLAY_NAMES.get(slug, market_name.strip()))
                .on_conflict_do_update(index_elements=[Market.slug], set_={"slug": slug})
                .returning(Market.id)
            )
            self.stats.markets_created.append(slug)
        self._markets[slug] = market_id
        return market_id

    async def store_id(self, depot: Depot) -> int:
        if depot.id in self._stores:
            return self._stores[depot.id]
        values = dict(
            market_id=await self.market_id(depot.market_name),
            external_id=depot.id,
            name=depot.name,
            latitude=depot.latitude,
            longitude=depot.longitude,
            last_seen_at=self._now,
        )
        stmt = insert(Store).values(**values)
        update = {k: stmt.excluded[k] for k in ("name", "last_seen_at", "market_id")}
        # Koordinat gelmediyse eskisini silme
        update["latitude"] = func.coalesce(stmt.excluded.latitude, Store.latitude)
        update["longitude"] = func.coalesce(stmt.excluded.longitude, Store.longitude)
        store_id = await self.db.scalar(
            stmt.on_conflict_do_update(index_elements=[Store.external_id], set_=update).returning(Store.id)
        )
        self._stores[depot.id] = store_id
        self.stats.stores = len(self._stores)
        return store_id

    async def upsert_depots(self, depots: Iterable[Depot]) -> list[int]:
        return [await self.store_id(d) for d in depots]

    async def category_id(self, product: SearchProduct) -> int | None:
        if self._categories is None:
            self._categories = dict((await self.db.execute(select(Category.slug, Category.id))).all())
        slug = category_slug(product)
        return self._categories.get(slug) if slug else None

    async def subcategory_id(self, product: SearchProduct, category_id: int | None) -> int | None:
        """Sitenin alt kategorisi ("Peynir", "Zeytin") uygulama kategorisinin altında bir kategori olur;
        ilk görüldüğünde oluşturulur. Slug: "<üst-slug>--<alt-ad>"."""
        if category_id is None or not product.main_category or self._categories is None:
            return None
        parent_slug = next((s for s, i in self._categories.items() if i == category_id), None)
        if parent_slug is None:
            return None
        slug = f"{parent_slug}--{re.sub(r'[^a-z0-9]+', '-', normalize_text(product.main_category)).strip('-')}"[:64]
        if slug not in self._categories:
            stmt = insert(Category).values(
                slug=slug, name=product.main_category.strip()[:120], parent_id=category_id, sort_order=0
            )
            self._categories[slug] = await self.db.scalar(
                stmt.on_conflict_do_update(index_elements=[Category.slug], set_={"slug": slug}).returning(Category.id)
            )
        return self._categories[slug]

    async def group_id(self, product: SearchProduct, category_id: int | None = None) -> int:
        display, key, qty = group_key(product)
        quantity, unit = qty if qty else (None, None)
        cache_key = (key, quantity, unit)
        if cache_key in self._groups:
            return self._groups[cache_key]

        # Aday: aynı miktar/birimde harfçe benzer gruplar; karar kelime eşleşmesiyle ("su" ≠ "süt")
        similarity = func.similarity(ProductGroup.normalized_name, key)
        stmt = select(ProductGroup.id, ProductGroup.normalized_name, ProductGroup.category_id).where(
            similarity >= GROUP_CANDIDATE_SIMILARITY
        )
        stmt = stmt.where(ProductGroup.unit.is_(None) if unit is None else ProductGroup.unit == unit)
        stmt = stmt.where(
            ProductGroup.quantity.is_(None) if quantity is None else ProductGroup.quantity == quantity
        )
        group_id = next(
            (
                gid
                for gid, name, gcat in await self.db.execute(stmt.order_by(similarity.desc()).limit(20))
                if same_product(name, key) and (gcat is None or category_id is None or gcat == category_id)
            ),
            None,
        )
        if group_id is None:
            group = ProductGroup(
                name=display,
                normalized_name=key,
                quantity=quantity,
                unit=unit,
                image_url=product.image_url,
                category_id=category_id,
            )
            self.db.add(group)
            await self.db.flush()
            group_id = group.id
            self.stats.groups_created += 1
        elif category_id is not None:
            # Anahtar kelimeyle eklenmiş, kategorisi olmayan gruplar kategori taramasında yerine oturur
            await self.db.execute(
                ProductGroup.__table__.update()
                .where(ProductGroup.id == group_id, ProductGroup.category_id.is_(None))
                .values(category_id=category_id)
            )
        self._groups[cache_key] = group_id
        return group_id

    async def ingest_product(self, product: SearchProduct) -> None:
        self.stats.products_seen += 1
        if not product.prices:
            return
        _, _, qty = group_key(product)
        category_id = await self.category_id(product)
        group_id = await self.group_id(product, category_id)
        subcategory_id = await self.subcategory_id(product, category_id)
        if subcategory_id is not None:
            # Grubun ilk tanınan alt kategorisi kalır; aynı kategorideki gruplara yazılır
            await self.db.execute(
                ProductGroup.__table__.update()
                .where(
                    ProductGroup.id == group_id,
                    ProductGroup.subcategory_id.is_(None),
                    ProductGroup.category_id == category_id,
                )
                .values(subcategory_id=subcategory_id)
            )

        by_market: dict[int, list] = defaultdict(list)
        for depot_price in product.prices:
            by_market[await self.market_id(depot_price.depot.market_name)].append(depot_price)

        for market_id, depot_prices in by_market.items():
            stmt = insert(Product).values(
                market_id=market_id,
                external_id=product.id,
                name=product.title,
                normalized_name=normalize_name(product.title),
                brand=product.brand,
                quantity=qty[0] if qty else None,
                unit=qty[1] if qty else None,
                image_url=product.image_url,
                category_id=category_id,
                is_available=True,
                last_seen_at=self._now,
            )
            product_id = await self.db.scalar(
                stmt.on_conflict_do_update(
                    constraint="uq_products_market_external",
                    set_={
                        **{
                            k: stmt.excluded[k]
                            for k in ("name", "normalized_name", "brand", "quantity", "unit", "image_url", "is_available", "last_seen_at")
                        },
                        "category_id": func.coalesce(stmt.excluded.category_id, Product.category_id),
                    },
                ).returning(Product.id)
            )
            self.stats.products_upserted += 1

            for dp in depot_prices:
                store_id = await self.store_id(dp.depot)
                sp = insert(StorePrice).values(
                    product_id=product_id, store_id=store_id, price=dp.price, unit_price=dp.unit_price, updated_at=self._now
                )
                await self.db.execute(
                    sp.on_conflict_do_update(
                        index_elements=[StorePrice.product_id, StorePrice.store_id],
                        set_={"price": sp.excluded.price, "unit_price": sp.excluded.unit_price, "updated_at": self._now},
                    )
                )
                self.stats.store_prices += 1

            await self._refresh_current_price(product_id, depot_prices)
            await self.db.execute(
                insert(GroupMember)
                .values(group_id=group_id, product_id=product_id, is_manual=False)
                .on_conflict_do_nothing(index_elements=[GroupMember.product_id])
            )

    async def _refresh_current_price(self, product_id: int, depot_prices: Sequence[DepotPrice] = ()) -> None:
        """Ürünün zincir genelindeki en düşük güncel fiyatı; fiyat ya da kampanya durumu değiştiyse
        fiyat geçmişine yazılır. Kampanya bilgisi (indirim öncesi fiyat) en düşük fiyatlı şubeden gelir;
        Fırsatlar bunu kullanır.
        """
        old, new = (
            await self.db.execute(
                select(
                    Product.current_price,
                    select(func.min(StorePrice.price))
                    .where(StorePrice.product_id == product_id)
                    .scalar_subquery(),
                ).where(Product.id == product_id)
            )
        ).one()
        if new is None:
            return
        regular = next((dp.regular_price for dp in depot_prices if dp.price == new and dp.regular_price), None)
        last_regular = await self.db.scalar(
            select(PriceHistory.regular_price)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.recorded_at.desc(), PriceHistory.id.desc())
            .limit(1)
        )
        if new != old or regular != last_regular:
            await self.db.execute(
                Product.__table__.update().where(Product.id == product_id).values(current_price=new)
            )
            self.db.add(
                PriceHistory(
                    product_id=product_id,
                    price=new,
                    regular_price=regular,
                    is_campaign=regular is not None,
                    recorded_at=self._now,
                )
            )
            self.stats.price_changes += 1


async def refresh_nearby_stores(
    db: AsyncSession, client: MarketFiyatiClient, latitude: float, longitude: float, distance_km: int
) -> list[int]:
    """Konum çevresindeki şubeleri marketfiyati'dan çekip kaydeder, store id'lerini döner."""
    depots = await client.nearest_depots(latitude, longitude, distance_km)
    ingestor = Ingestor(db)
    store_ids = await ingestor.upsert_depots(depots)
    await db.commit()
    return store_ids


async def sync_area(
    db: AsyncSession,
    client: MarketFiyatiClient,
    *,
    latitude: float,
    longitude: float,
    distance_km: int = settings.default_search_distance_km,
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
    categories: Sequence[str] = (),
    depot_ids: Sequence[str] = (),
    max_pages: int = 5,
    max_category_pages: int = 100,
) -> SyncStats:
    """Bir bölge (ve isteğe bağlı şube listesi) için fiyatları çeker: önce menü kategorilerinin
    tamamı (şubedeki tüm ürünler), sonra anahtar kelimeler.

    Her kategori/kelimeden sonra commit edilir; yarıda kesilen senkronizasyon o ana kadarki veriyi korur.
    """
    ingestor = Ingestor(db)
    queries = [(c, {"menu_category": c, "max_pages": max_category_pages}) for c in categories]
    queries += [(k, {"keywords": k, "max_pages": max_pages}) for k in keywords]
    for keyword, query in queries:
        try:
            products = await client.search_all(
                **query,
                latitude=latitude,
                longitude=longitude,
                distance_km=distance_km,
                depot_ids=depot_ids,
            )
        except Exception:
            log.exception("marketfiyati araması başarısız: %r", keyword)
            continue
        for product in products:
            await ingestor.ingest_product(product)
        await db.commit()
        log.info("'%s': %d ürün", keyword, len(products))
    return ingestor.stats


async def sync_selected_stores(
    db: AsyncSession,
    client: MarketFiyatiClient,
    keywords: Sequence[str] = (),
    store_ids: Sequence[int] | None = None,
    categories: Sequence[str] = MENU_CATEGORIES,
) -> SyncStats:
    """Kullanıcıların seçtiği şubeler için fiyatları günceller: varsayılan olarak şubelerin tüm ürünleri.

    Şubeler ~5 km'lik hücrelere bölünür. marketfiyati her ürün için zincir başına yalnızca bir şubenin
    fiyatını döndürdüğünden bir aramada her zincirden en fazla bir şube bulunur: aynı zincirin 3 şubesi
    seçildiyse hücre 3 turda taranır.
    """
    stmt = select(Store).where(Store.latitude.is_not(None), Store.longitude.is_not(None))
    if store_ids is None:
        stmt = stmt.where(Store.id.in_(select(UserStore.store_id).distinct()))
    else:
        stmt = stmt.where(Store.id.in_(store_ids))
    stores = (await db.scalars(stmt)).all()

    cells: dict[tuple[int, int], list[Store]] = defaultdict(list)
    for store in stores:
        cells[(round(float(store.latitude) * 20), round(float(store.longitude) * 20))].append(store)

    rounds: list[list[Store]] = []
    for cell in cells.values():
        by_market: dict[int, list[Store]] = defaultdict(list)
        for store in cell:
            by_market[store.market_id].append(store)
        for i in range(max(len(s) for s in by_market.values())):
            rounds.append([s[i] for s in by_market.values() if i < len(s)])

    total = SyncStats()
    for cell_stores in rounds:
        lat = sum(float(s.latitude) for s in cell_stores) / len(cell_stores)
        lon = sum(float(s.longitude) for s in cell_stores) / len(cell_stores)
        stats = await sync_area(
            db,
            client,
            latitude=lat,
            longitude=lon,
            distance_km=settings.default_search_distance_km,
            keywords=keywords,
            categories=categories,
            depot_ids=[s.external_id for s in cell_stores],
        )
        for name in ("products_seen", "products_upserted", "store_prices", "stores", "groups_created", "price_changes"):
            setattr(total, name, getattr(total, name) + getattr(stats, name))
        total.markets_created += stats.markets_created
    return total

