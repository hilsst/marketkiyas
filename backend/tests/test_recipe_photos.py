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


# ---- Instagram yayını ----

import httpx  # noqa: E402

from app.services import instagram as ig_svc  # noqa: E402


class FakeGraph:
    """Instagram Graph API taklidi (ağa çıkmaz)"""

    def __init__(self, fail_publish=False):
        self.calls, self.fail_publish = [], fail_publish

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path, request.content.decode()))
        assert request.headers["authorization"] == "Bearer tok-gizli"
        assert "tok-gizli" not in str(request.url)
        path = request.url.path
        if request.method == "POST" and path.endswith("/media"):
            return httpx.Response(200, json={"id": "C1"})
        if request.method == "POST" and path.endswith("/media_publish"):
            if self.fail_publish:
                return httpx.Response(400, json={"error": {"code": 9007, "message": "bozuk tok-gizli"}})
            return httpx.Response(200, json={"id": "M1"})
        if path.endswith("/C1"):
            return httpx.Response(200, json={"status_code": "FINISHED"})
        if path.endswith("/M1"):
            return httpx.Response(200, json={"permalink": "https://instagram.com/p/abc"})
        return httpx.Response(200, json={"username": "ucuzu"})


@pytest.fixture
def ig(monkeypatch, tmp_path):
    monkeypatch.setattr(photo_svc, "ENHANCED_DIR", tmp_path / "e")
    monkeypatch.setattr(photo_svc, "ORIGINAL_DIR", tmp_path / "o")
    monkeypatch.setattr(settings, "admin_emails", "yonetici@example.com")
    for k, v in dict(instagram_enabled=True, instagram_access_token="tok-gizli", instagram_user_id="123",
                     public_base_url="https://ucuzu.test").items():
        monkeypatch.setattr(settings, k, v)
    graph = FakeGraph()
    real = httpx.AsyncClient

    def factory(*a, **kw):
        return real(*a, transport=httpx.MockTransport(lambda r: graph.handler(r)), **{k: v for k, v in kw.items() if k != "transport"})

    monkeypatch.setattr(ig_svc.httpx, "AsyncClient", factory)
    monkeypatch.setattr(ig_svc, "POLL_SECONDS", 0)
    return graph


async def _approved_photo(client, headers, admin, consent):
    rid = await _recipe_id(client)
    res = await client.post(f"/api/recipes/{rid}/photos", headers=headers, data={"instagram_consent": str(consent).lower()},
                            files={"file": ("a.jpg", _jpeg(), "image/jpeg")})
    pid = res.json()["id"]
    await client.post(f"/api/admin/recipe-photos/{pid}/approve", headers=admin)
    return pid


async def test_instagram_publish_flow(client, auth_headers, ig):
    admin = await _register(client, "yonetici@example.com")
    pid = await _approved_photo(client, auth_headers, admin, True)
    assert (await client.get("/api/admin/instagram/status", headers=auth_headers)).status_code == 403
    st = (await client.get("/api/admin/instagram/status", headers=admin)).json()
    assert st["configured"] and st["username"] == "ucuzu" and "tok-gizli" not in str(st)
    cap = (await client.get(f"/api/admin/instagram/caption/{pid}", headers=admin)).json()["caption"]
    assert "Bir kullanıcı tarafından eklendi" in cap and "#ucuzu" in cap

    r = await client.post(f"/api/admin/recipe-photos/{pid}/instagram", headers=admin, json={})
    assert r.status_code == 200 and r.json()["ig_status"] == "published"
    assert r.json()["ig_permalink"] == "https://instagram.com/p/abc"
    media_call = next(c for c in ig.calls if c[1].endswith("/media"))
    assert f"https%3A%2F%2Fucuzu.test%2Fapi%2Frecipe-photos%2F{pid}%2Fimage" in media_call[2]
    # ikinci kez yayınlanamaz
    assert (await client.post(f"/api/admin/recipe-photos/{pid}/instagram", headers=admin, json={})).status_code == 409


async def test_instagram_requires_consent_approval_and_config(client, auth_headers, ig, monkeypatch):
    admin = await _register(client, "yonetici@example.com")
    no_consent = await _approved_photo(client, auth_headers, admin, False)
    r = await client.post(f"/api/admin/recipe-photos/{no_consent}/instagram", headers=admin, json={})
    assert r.status_code == 403 and ig.calls == []
    rid = await _recipe_id(client)
    pending = (await client.post(f"/api/recipes/{rid}/photos", headers=auth_headers, data={"instagram_consent": "true"},
                                 files={"file": ("a.jpg", _jpeg(), "image/jpeg")})).json()["id"]
    assert (await client.post(f"/api/admin/recipe-photos/{pending}/instagram", headers=admin, json={})).status_code == 409
    monkeypatch.setattr(settings, "instagram_enabled", False)
    ok = await _approved_photo(client, auth_headers, admin, True)
    assert (await client.post(f"/api/admin/recipe-photos/{ok}/instagram", headers=admin, json={})).status_code == 409


async def test_instagram_failure_is_recorded_redacted_and_retryable(client, auth_headers, ig):
    admin = await _register(client, "yonetici@example.com")
    pid = await _approved_photo(client, auth_headers, admin, True)
    ig.fail_publish = True
    r = await client.post(f"/api/admin/recipe-photos/{pid}/instagram", headers=admin, json={})
    assert r.json()["ig_status"] == "failed" and "tok-gizli" not in r.json()["ig_error"]
    ig.fail_publish = False
    r = await client.post(f"/api/admin/recipe-photos/{pid}/instagram", headers=admin, json={})
    assert r.json()["ig_status"] == "published"
    assert len([c for c in ig.calls if c[1].endswith("/media")]) == 1  # kapsayıcı yeniden kullanıldı


def test_caption_sanitizes_credit_and_limits():
    cap = ig_svc.build_caption("Mercimek Çorbası", "Ali @spam http://x.co #tag")
    assert "@" not in cap and "http" not in cap.replace("https://", "") and len(cap) <= 2200


async def test_instagram_resolve_and_delete_keeps_track(client, auth_headers, ig):
    admin = await _register(client, "yonetici@example.com")
    pid = await _approved_photo(client, auth_headers, admin, True)
    ig.fail_publish = True
    await client.post(f"/api/admin/recipe-photos/{pid}/instagram", headers=admin, json={})
    r = await client.post(f"/api/admin/recipe-photos/{pid}/instagram/resolve", headers=admin, json={"published": False})
    assert r.json()["ig_status"] is None
    ig.fail_publish = False
    r = await client.post(f"/api/admin/recipe-photos/{pid}/instagram", headers=admin, json={})
    assert r.json()["ig_status"] == "published"
    assert (await client.post(f"/api/admin/recipe-photos/{pid}/instagram/resolve", headers=admin,
                              json={"published": True})).status_code == 409
    # sahibi silince satır kalır, elle kaldırma için işaretlenir
    assert (await client.delete(f"/api/recipe-photos/{pid}", headers=auth_headers)).status_code == 204
    rows = (await client.get("/api/admin/recipe-photos?status=rejected", headers=admin)).json()
    assert len(rows) == 1 and rows[0]["ig_needs_removal"] is True
