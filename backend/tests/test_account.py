import httpx
import pytest
from sqlalchemy import select

from app.api.routes import auth as auth_routes
from app.core.config import settings
from app.models import ShoppingList, User
from app.services import social

EMAIL, PASSWORD = "kemal@example.com", "gizli-sifre-123"
REAL_VERIFY_GOOGLE = social.verify_google_id_token


@pytest.fixture
def outbox(monkeypatch):
    """Gönderilen e-postaları yakalar (SMTP'ye gitmez)."""
    sent: list[tuple[str, str, str]] = []

    async def fake_send(to, subject, body):
        sent.append((to, subject, body))

    monkeypatch.setattr(auth_routes, "send_mail", fake_send)
    return sent


def _code(outbox) -> str:
    body = outbox[-1][2]
    return next(word for word in body.split() if word.isdigit() and len(word) == 6)


async def test_password_reset_flow(client, auth_headers, outbox):
    r = await client.post("/api/auth/password-reset/request", json={"email": "KEMAL@example.com"})
    assert r.status_code == 202
    assert outbox[-1][0] == EMAIL
    code = _code(outbox)

    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": code, "new_password": "yeni-sifre-456"})
    assert r.status_code == 200 and r.json()["access_token"]
    assert (await client.post("/api/auth/login", json={"email": EMAIL, "password": "yeni-sifre-456"})).status_code == 200
    assert (await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})).status_code == 401
    # Kod tek kullanımlık
    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": code, "new_password": "ucuncu-sifre-789"})
    assert r.status_code == 400


async def test_password_reset_does_not_reveal_accounts(client, outbox):
    r = await client.post("/api/auth/password-reset/request", json={"email": "yok@example.com"})
    assert r.status_code == 202 and outbox == []


async def test_password_reset_limits_attempts_and_requests(client, auth_headers, outbox):
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    code = _code(outbox)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(auth_routes.RESET_MAX_ATTEMPTS):
        r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": wrong, "new_password": "yeni-sifre-456"})
        assert r.status_code == 400
    # 5 yanlıştan sonra doğru kod da kabul edilmez
    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": code, "new_password": "yeni-sifre-456"})
    assert r.status_code == 400

    for _ in range(5):
        await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    assert len(outbox) == auth_routes.RESET_MAX_PER_WINDOW  # saatte en fazla 3 kod


async def test_new_code_invalidates_old_one(client, auth_headers, outbox):
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    first = _code(outbox)
    await client.post("/api/auth/password-reset/request", json={"email": EMAIL})
    second = _code(outbox)
    if first != second:
        r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": first, "new_password": "yeni-sifre-456"})
        assert r.status_code == 400
    r = await client.post("/api/auth/password-reset/confirm", json={"email": EMAIL, "code": second, "new_password": "yeni-sifre-456"})
    assert r.status_code == 200


async def test_delete_account_requires_password_and_removes_data(client, auth_headers, db):
    await client.post("/api/lists", json={"name": "Haftalık"}, headers=auth_headers)
    r = await client.request("DELETE", "/api/auth/me", json={"password": "yanlis-sifre"}, headers=auth_headers)
    assert r.status_code == 403
    r = await client.request("DELETE", "/api/auth/me", json={"password": PASSWORD}, headers=auth_headers)
    assert r.status_code == 204
    assert await db.scalar(select(User).where(User.email == EMAIL)) is None
    assert await db.scalar(select(ShoppingList)) is None
    assert (await client.get("/api/auth/me", headers=auth_headers)).status_code == 401


def _google(monkeypatch, payload: dict, status: int = 200):
    """Google'ın tokeninfo ucunu taklit eder."""
    monkeypatch.setattr(settings, "google_client_ids", "android-client.apps.googleusercontent.com")
    real = REAL_VERIFY_GOOGLE

    async def fake(id_token: str):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["id_token"] == id_token
            return httpx.Response(status, json=payload)
        return await real(id_token, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(social, "verify_google_id_token", fake)


GOOGLE_OK = {
    "aud": "android-client.apps.googleusercontent.com", "iss": "https://accounts.google.com",
    "sub": "1234567890", "email": "Ayse@Gmail.com", "email_verified": "true", "name": "Ayşe",
}


async def test_google_login_creates_account_without_password(client, monkeypatch, db):
    _google(monkeypatch, GOOGLE_OK)
    r = await client.post("/api/auth/google", json={"id_token": "google-id-token"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "ayse@gmail.com" and body["user"]["has_password"] is False
    # Aynı Google hesabı ikinci kez: aynı kullanıcı
    r2 = await client.post("/api/auth/google", json={"id_token": "google-id-token"})
    assert r2.json()["user"]["id"] == body["user"]["id"]
    # Şifresi olmayan hesap e-posta/şifre ile giremez, ama şifresiz silinebilir
    assert (await client.post("/api/auth/login", json={"email": "ayse@gmail.com", "password": "herhangi-bir"})).status_code == 401
    h = {"Authorization": f"Bearer {body['access_token']}"}
    assert (await client.request("DELETE", "/api/auth/me", json={}, headers=h)).status_code == 204


async def test_google_login_links_existing_verified_email(client, auth_headers, monkeypatch):
    _google(monkeypatch, {**GOOGLE_OK, "email": EMAIL})
    me = (await client.get("/api/auth/me", headers=auth_headers)).json()
    r = await client.post("/api/auth/google", json={"id_token": "google-id-token"})
    assert r.status_code == 200 and r.json()["user"]["id"] == me["id"]


async def test_google_login_rejects_other_apps_tokens(client, monkeypatch):
    _google(monkeypatch, {**GOOGLE_OK, "aud": "baska-uygulama"})
    assert (await client.post("/api/auth/google", json={"id_token": "google-id-token"})).status_code == 401
    _google(monkeypatch, {"error": "invalid_token"}, status=400)
    assert (await client.post("/api/auth/google", json={"id_token": "google-id-token"})).status_code == 401
