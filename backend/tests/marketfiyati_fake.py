"""Testler için marketfiyati.org.tr taklidi (httpx.MockTransport)."""

import json
from pathlib import Path

import httpx

from app.services.marketfiyati.client import MarketFiyatiClient

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeMarketFiyati:
    def __init__(self, search: dict | None = None, nearest: list | None = None) -> None:
        self.search = search if search is not None else load("marketfiyati_search_sut.json")
        self.nearest = nearest if nearest is not None else load("marketfiyati_nearest.json")
        self.requests: list[httpx.Request] = []
        self.fail_with: int | None = None
        self.identity: dict = {"numberOfFound": 0, "content": []}  # /searchByIdentity yanıtı
        self.similar: dict = {"numberOfFound": 0, "content": []}  # /searchSmilarProduct yanıtı

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail_with:
            return httpx.Response(self.fail_with)
        if request.url.path == "/api/v2/nearest":
            return httpx.Response(200, json=self.nearest)
        if request.url.path in ("/api/v2/search", "/api/v2/searchByCategories"):
            body = json.loads(request.content)
            # tek sayfa: ikinci sayfa boş
            return httpx.Response(200, json=self.search if body["pages"] == 0 else {"numberOfFound": 0, "content": []})
        if request.url.path == "/api/v2/searchByIdentity":
            return httpx.Response(200, json=self.identity)
        if request.url.path == "/api/v2/searchSmilarProduct":
            return httpx.Response(200, json=self.similar)
        return httpx.Response(404)

    def client(self, **kwargs) -> MarketFiyatiClient:
        kwargs.setdefault("min_interval", 0)
        kwargs.setdefault("max_retries", 0)
        return MarketFiyatiClient("https://api.test", transport=httpx.MockTransport(self.handler), **kwargs)
