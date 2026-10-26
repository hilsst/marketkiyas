"""marketfiyati.org.tr HTTP istemcisi.

- Hız sınırı: istekler arasında en az `min_interval` saniye (tek paylaşılan kilit).
- Tekrar deneme: ağ hataları, 429 ve 5xx için üstel bekleme + jitter; Retry-After başlığına uyulur.
- Kimlik: istemci kendini açıkça "MarketKiyas" olarak tanıtır. Tarayıcı taklidi (User-Agent
  rotasyonu, sahte Origin/Referer) bilerek yapılmaz; kaynak erişimi kısıtlarsa çözüm resmi
  erişim izni istemektir.
"""

import asyncio
import logging
import random
import time
from collections.abc import Sequence
from typing import Any

import httpx

from app.core.config import settings
from app.services.marketfiyati.schemas import Depot, SearchPage

log = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_PAGE_SIZE = 100


class MarketFiyatiError(RuntimeError):
    pass


class MarketFiyatiClient:
    def __init__(
        self,
        base_url: str = settings.marketfiyati_base_url,
        *,
        min_interval: float = settings.marketfiyati_min_interval_seconds,
        max_retries: int = settings.marketfiyati_max_retries,
        timeout: float = settings.marketfiyati_timeout_seconds,
        transport: httpx.AsyncBaseTransport | None = None,
        user_agent: str = settings.marketfiyati_user_agent,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": user_agent,
            },
        )
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def __aenter__(self) -> "MarketFiyatiClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _throttle(self) -> None:
        async with self._lock:
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    @staticmethod
    def _backoff(attempt: int, response: httpx.Response | None) -> float:
        if response is not None and (retry_after := response.headers.get("Retry-After")):
            try:
                return min(float(retry_after), 60.0)
            except ValueError:
                pass
        return min(2**attempt, 30) + random.uniform(0, 1)

    async def _request(self, method: str, path: str, json: dict | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            await self._throttle()
            response = None
            try:
                response = await self._http.request(method, path, json=json)
                if response.status_code not in RETRY_STATUSES:
                    response.raise_for_status()
                    return response.json()
                last_error = MarketFiyatiError(f"{method} {path} -> HTTP {response.status_code}")
            except httpx.TransportError as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:  # 4xx: tekrar denemenin anlamı yok
                raise MarketFiyatiError(f"{method} {path} -> HTTP {exc.response.status_code}") from exc

            if attempt < self._max_retries:
                delay = self._backoff(attempt, response)
                log.warning("marketfiyati %s %s başarısız (%s), %.1fs sonra tekrar", method, path, last_error, delay)
                await asyncio.sleep(delay)
        raise MarketFiyatiError(f"{method} {path} {self._max_retries + 1} denemede başarısız") from last_error

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

    async def search_all(self, max_pages: int = 20, **kwargs) -> list:
        """Tüm sayfaları dolaşır (max_pages güvenlik sınırı)."""
        products = []
        for page in range(max_pages):
            result = await self.search(page=page, **kwargs)
            products.extend(result.products)
            if not result.products or len(products) >= result.total:
                break
        return products
