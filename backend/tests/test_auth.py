async def test_register_login_me(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "Kemal@Example.com", "password": "gizli-sifre-123", "full_name": "Kemal"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "kemal@example.com"

    r = await client.post(
        "/api/auth/login", json={"email": "KEMAL@example.com", "password": "gizli-sifre-123"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Kemal"


async def test_duplicate_email_rejected(client, auth_headers):
    r = await client.post(
        "/api/auth/register", json={"email": "kemal@example.com", "password": "baska-sifre-1"}
    )
    assert r.status_code == 409


async def test_wrong_password(client, auth_headers):
    r = await client.post("/api/auth/login", json={"email": "kemal@example.com", "password": "yanlis"})
    assert r.status_code == 401


async def test_me_requires_valid_token(client):
    assert (await client.get("/api/auth/me")).status_code == 401
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer bozuk.token.x"})
    assert r.status_code == 401


async def test_swagger_token_endpoint(client, auth_headers):
    r = await client.post(
        "/api/auth/token", data={"username": "kemal@example.com", "password": "gizli-sifre-123"}
    )
    assert r.status_code == 200
