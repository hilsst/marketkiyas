"""Kibar HTTP istemcisi: tüm dış kaynaklar (marketfiyati, market siteleri) bunun üzerinden çağrılır.

- Hız sınırı: istekler arasında en az `min_interval` saniye (tek paylaşılan kilit).
- Tekrar deneme: ağ hataları, 429 ve 5xx için üstel bekleme + jitter; Retry-After başlığına uyulur.
  4xx hatalarında tekrar denenmez.
- Kimlik: istemci kendini açıkça "MarketKiyas" olarak tanıtır. Tarayıcı taklidi (User-Agent
  rotasyonu, sahte Origin/Referer) bilerek yapılmaz; kaynak erişimi kısıtlarsa çözüm izin istemektir.
"""

import asyncio
import logging
import random
import time
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PoliteClient:
    error_class: type[HttpError] = HttpError

    def __init__(
        self,
        base_url: str = "",
        *,
        min_interval: float = settings.marketfiyati_min_interval_seconds,
        max_retries: int = settings.marketfiyati_max_retries,
        timeout: float = settings.marketfiyati_timeout_seconds,
        transport: httpx.AsyncBaseTransport | None = None,
        user_agent: str = settings.marketfiyati_user_agent,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
            headers={"User-Agent": user_agent, **(headers or {})},
        )
        self.user_agent = user_agent
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def throttle(self) -> None:
        """İstek dışı işler (ör. tarayıcı render) için de aynı hız sınırını uygular."""
        await self._throttle()

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

    async def fetch(self, method: str, url: str, json: Any = None) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            await self._throttle()
            response = None
            try:
                response = await self._http.request(method, url, json=json)
                if response.status_code not in RETRY_STATUSES:
                    if response.is_error:
                        raise self.error_class(f"{method} {url} -> HTTP {response.status_code}", response.status_code)
                    return response
                last_error = self.error_class(f"{method} {url} -> HTTP {response.status_code}", response.status_code)
            except httpx.TransportError as exc:
                last_error = exc

            if attempt < self._max_retries:
                delay = self._backoff(attempt, response)
                log.warning("%s %s başarısız (%s), %.1fs sonra tekrar", method, url, last_error, delay)
                await asyncio.sleep(delay)
        raise self.error_class(f"{method} {url} {self._max_retries + 1} denemede başarısız") from last_error
