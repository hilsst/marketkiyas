"""marketfiyati.org.tr HTTP istemcisi (hız sınırı ve tekrar deneme: app/services/http.py)."""

from collections.abc import Sequence
from typing import Any

import httpx

from app.core.config import settings
from app.services.http import HttpError, PoliteClient
from app.services.marketfiyati.schemas import Depot, SearchPage

MAX_PAGE_SIZE = 100


class MarketFiyatiError(HttpError):
    pass


class MarketFiyatiClient(PoliteClient):
    error_class = MarketFiyatiError

    def __init__(
        self,
        base_url: str = settings.marketfiyati_base_url,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            base_url,
            transport=transport,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            **kwargs,
        )

    async def _request(self, method: str, path: str, json: dict | None = None) -> Any:
        return (await self.fetch(method, path, json=json)).json()

    async def nearest_depots(self, latitude: float, longitude: float, distance_km: int) -> list[Depot]:
        data = await self._request(
            "POST",
            "/api/v2/nearest",
            {"latitude": latitude, "longitude": longitude, "distance": distance_km},
        )
        rows = data if isinstance(data, list) else (data or {}).get("content", [])
        return [d for d in (Depot.from_nearest(r) for r in rows) if d]

    async def search(
        self,
        *,
        keywords: str | None = None,
        menu_category: str | None = None,
        latitude: float,
        longitude: float,
        distance_km: int,
        depot_ids: Sequence[str] = (),
        page: int = 0,
        size: int = MAX_PAGE_SIZE,
    ) -> SearchPage:
        body: dict[str, Any] = {
            "keywords": keywords or "",
            "pages": page,
            "size": min(size, MAX_PAGE_SIZE),
            "latitude": latitude,
            "longitude": longitude,
            "distance": distance_km,
            "depots": list(depot_ids),
        }
        if menu_category:
            body["menuCategory"] = menu_category
        return SearchPage.from_raw(await self._request("POST", "/api/v2/search", body) or {})

    async def search_category(
        self,
        menu_category: str,
        *,
        latitude: float,
        longitude: float,
        distance_km: int,
        depot_ids: Sequence[str] = (),
        page: int = 0,
        size: int = MAX_PAGE_SIZE,
    ) -> SearchPage:
        """Sitenin kategori menüsündeki bir kategorinin tüm ürünleri (anahtar kelime gerekmez)."""
        body: dict[str, Any] = {
            "keywords": menu_category,
            "menuCategory": True,
            "pages": page,
            "size": min(size, MAX_PAGE_SIZE),
            "latitude": latitude,
            "longitude": longitude,
            "distance": distance_km,
            "depots": list(depot_ids),
        }
        return SearchPage.from_raw(await self._request("POST", "/api/v2/searchByCategories", body) or {})

    async def search_all(self, max_pages: int = 20, *, menu_category: str | None = None, **kwargs) -> list:
        """Tüm sayfaları dolaşır (max_pages güvenlik sınırı). menu_category verilirse o kategori taranır."""
        products = []
        for page in range(max_pages):
            if menu_category:
                result = await self.search_category(menu_category, page=page, **kwargs)
            else:
                result = await self.search(page=page, **kwargs)
            products.extend(result.products)
            if not result.products or len(products) >= result.total:
                break
        return products
