import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory


async def test_signup_and_login_on_fresh_db(client):
    """Tüm göçler boş veritabanına uygulandıktan sonra kayıt ve giriş çalışır (500 dönmez)."""
    body = {"email": "yeni@example.com", "password": "gizli-sifre-123", "full_name": "Yeni"}
    r = await client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    r = await client.post("/api/auth/login", json={"email": body["email"], "password": body["password"]})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == body["email"]


def test_single_migration_head():
    assert len(ScriptDirectory.from_config(Config("alembic.ini")).get_heads()) == 1


def test_server_starts_without_pillow():
    """Yeni bir bağımlılık kurulu değilse bile sunucu açılır; yalnız o özellik hata verir."""
    code = (
        "import sys; sys.modules['PIL'] = None; "
        "from app.main import app; print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "ok" in out.stdout, out.stderr
