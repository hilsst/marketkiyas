import io

import pytest
from fastapi import HTTPException
from PIL import Image

from app.core.config import settings
from app.services import recipe_photos as photo_svc
from app.services.photo_enhance import enhance_photo


def _jpeg(w=1600, h=1000, color=(120, 60, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG")
    return buf.getvalue()


def test_enhance_outputs_4x5_jpeg_without_exif():
    out = Image.open(io.BytesIO(enhance_photo(_jpeg())))
    assert out.size == (1200, 1500) and out.format == "JPEG"
    assert not out.getexif()


def test_enhance_rejects_non_image_and_small():
    with pytest.raises(HTTPException) as e:
        enhance_photo(b"not an image")
    assert e.value.status_code == 415
    with pytest.raises(HTTPException) as e:
        enhance_photo(_jpeg(300, 300))
    assert e.value.status_code == 422


def test_credit_text():
    assert photo_svc.credit_text("Ayşe") == "Ayşe tarafından eklendi"
    assert photo_svc.credit_text(None) == "Bir kullanıcı tarafından eklendi"


async def _register(client, email, name=None):
    r = await client.post("/api/auth/register", json={"email": email, "password": "gizli-sifre-123", **({"full_name": name} if name else {})})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _recipe_id(client):
    return (await client.get("/api/recipes")).json()[0]["id"]


async def test_guest_cannot_upload(client):
    r = await client.post("/api/auth/guest")
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rid = await _recipe_id(client)
    res = await client.post(f"/api/recipes/{rid}/photos", headers=h, files={"file": ("a.jpg", _jpeg(), "image/jpeg")})
    assert res.status_code == 403


async def test_upload_needs_approval_then_visible(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(photo_svc, "ENHANCED_DIR", tmp_path / "e")
    monkeypatch.setattr(photo_svc, "ORIGINAL_DIR", tmp_path / "o")
    monkeypatch.setattr(settings, "admin_emails", "yonetici@example.com")
    admin = await _register(client, "yonetici@example.com")
    rid = await _recipe_id(client)

    res = await client.post(f"/api/recipes/{rid}/photos", headers=auth_headers, data={"share_name": "false"},
                            files={"file": ("a.jpg", _jpeg(), "image/jpeg")})
    assert res.status_code == 201
    pid = res.json()["id"]
    assert res.json()["status"] == "pending" and res.json()["credit"] == "Bir kullanıcı tarafından eklendi"

    # onaylanana kadar tarifte ve herkese açık adreste görünmez
    assert (await client.get(f"/api/recipes/{rid}")).json()["photo_credit"] is None
    assert (await client.get(f"/api/recipe-photos/{pid}/image")).status_code == 404
    # sahibi görebilir, başka üye göremez
    assert (await client.get(f"/api/recipe-photos/{pid}/image", headers=auth_headers)).status_code == 200
    other = await _register(client, "baska@example.com")
    assert (await client.get(f"/api/recipe-photos/{pid}/image", headers=other)).status_code == 404

    # yönetici olmayan onaylayamaz
    assert (await client.post(f"/api/admin/recipe-photos/{pid}/approve", headers=auth_headers)).status_code == 403
    # yönetici bekleyen fotoğrafı da ham halini de görebilir
    r = await client.get(f"/api/recipe-photos/{pid}/image", headers=admin)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and len(r.content) > 1000
    assert (await client.get(f"/api/recipe-photos/{pid}/image?original=1", headers=admin)).status_code == 200
    assert len((await client.get("/api/admin/recipe-photos", headers=admin)).json()) == 1
    assert (await client.post(f"/api/admin/recipe-photos/{pid}/approve", headers=admin)).status_code == 200

    d = (await client.get(f"/api/recipes/{rid}")).json()
    assert d["image_url"] == f"/recipe-photos/{pid}/image"
    assert d["photo_credit"] == "Bir kullanıcı tarafından eklendi"
    assert (await client.get(f"/api/recipe-photos/{pid}/image")).status_code == 200
    assert (await client.get(f"/api/recipe-photos/{pid}/image?original=1")).status_code == 404

    # sahibi silince varsayılan görsele döner
    assert (await client.delete(f"/api/recipe-photos/{pid}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/recipes/{rid}")).json()["photo_credit"] is None
