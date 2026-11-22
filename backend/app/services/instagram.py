"""Instagram Graph API ile fotoğraf yayını (içerik yayınlama).

Akış: kapsayıcı oluştur (POST /{ig-user}/media image_url+caption) -> status_code FINISHED olana kadar bekle
-> yayınla (POST /{ig-user}/media_publish) -> permalink al.
NOT: Meta dokümanı bu ortamdan okunamadı; istek biçimleri bilinen Graph API sözleşmesine göre yazıldı,
gerçek hesapla ilk denemede doğrulanmalı. Anahtar yalnız Authorization başlığında gider, günlüğe/hataya yazılmaz.
"""
import asyncio
import re
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Recipe, RecipePhoto
from app.models.recipe_photo import PHOTO_APPROVED

STALE_AFTER = timedelta(minutes=10)
POLL_SECONDS = 3.0
POLL_MAX_SECONDS = 60.0
CAPTION_MAX = 2200
MAX_HASHTAGS = 30


def is_configured() -> bool:
    return bool(settings.instagram_enabled and settings.instagram_access_token and settings.instagram_user_id
                and settings.public_base_url.startswith("https://"))


def _base() -> str:
    return f"{settings.instagram_graph_host.rstrip('/')}/{settings.instagram_api_version}"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.instagram_access_token}"}


def _redact(text: str) -> str:
    t = settings.instagram_access_token
    return text.replace(t, "***") if t else text


def image_url(photo_id: int) -> str:
    return f"{settings.public_base_url.rstrip('/')}/api/recipe-photos/{photo_id}/image"


def _clean_name(name: str | None) -> str:
    """Kullanıcı girdisi: bağlantı, @ ve # temizlenir"""
    n = re.sub(r"https?://\S+|www\.\S+", "", name or "")
    return re.sub(r"[@#\n\r]", "", n).strip()[:60]


def build_caption(recipe_name: str, credit_name: str | None) -> str:
    credit = _clean_name(credit_name)
    lines = [recipe_name.strip(), ""]
    lines.append(f"📸 {credit} tarafından eklendi" if credit else "📸 Bir kullanıcı tarafından eklendi")
    lines += ["", "Tarifi ve malzeme fiyatlarını Ucuzu uygulamasında gör.", ""]
    tags = [t for t in settings.instagram_hashtags.split() if t.startswith("#")][:MAX_HASHTAGS]
    lines.append(" ".join(tags))
    return "\n".join(lines).strip()[:CAPTION_MAX]


def _sanitize_caption(caption: str) -> str:
    caption = caption.strip()
    if len(caption) > CAPTION_MAX:
        raise HTTPException(422, f"Altyazı en fazla {CAPTION_MAX} karakter olabilir")
    if len(re.findall(r"#\w+", caption)) > MAX_HASHTAGS:
        raise HTTPException(422, f"En fazla {MAX_HASHTAGS} etiket kullanılabilir")
    return caption


async def account_status() -> dict:
    """Bağlantı durumu; anahtarın kendisi hiçbir zaman döndürülmez"""
    out = {"enabled": settings.instagram_enabled, "configured": is_configured(), "username": None, "error": None}
    if not out["configured"]:
        return out
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{_base()}/{settings.instagram_user_id}", params={"fields": "username"}, headers=_headers())
        if r.status_code == 200:
            out["username"] = r.json().get("username")
        else:
            out["error"] = _redact(_api_error(r))
    except httpx.HTTPError as e:
        out["error"] = _redact(f"Bağlantı kurulamadı: {type(e).__name__}")
    return out


def _api_error(r: httpx.Response) -> str:
    try:
        e = r.json().get("error", {})
        return f"Instagram hatası {e.get('code', r.status_code)}: {e.get('message', r.text[:200])}"
    except ValueError:
        return f"Instagram hatası {r.status_code}"


async def _wait_finished(c: httpx.AsyncClient, container_id: str) -> None:
    waited = 0.0
    while True:
        r = await c.get(f"{_base()}/{container_id}", params={"fields": "status_code"}, headers=_headers())
        if r.status_code != 200:
            raise RuntimeError(_api_error(r))
        code = r.json().get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram görseli işleyemedi ({code})")
        if waited >= POLL_MAX_SECONDS:
            raise RuntimeError("Instagram görseli zamanında işlemedi; birazdan tekrar dene")
        await asyncio.sleep(POLL_SECONDS)
        waited += POLL_SECONDS


async def publish_photo(db: AsyncSession, photo_id: int, admin_id: int, caption: str | None) -> RecipePhoto:
    """Kısa işlem 1: kontrol + 'publishing' (kilit yalnız burada). Dış çağrılar kilitsiz. Kısa işlem 2: sonuç."""
    if not is_configured():
        raise HTTPException(409, "Instagram bağlantısı kurulu değil")
    now = datetime.now(timezone.utc)
    photo = await db.get(RecipePhoto, photo_id, with_for_update=True)
    if photo is None:
        raise HTTPException(404, "Fotoğraf bulunamadı")
    if photo.status != PHOTO_APPROVED:
        raise HTTPException(409, "Yalnız onaylı fotoğraf yayınlanır")
    if not photo.ig_consent:
        raise HTTPException(403, "Yükleyen Instagram'da yayınlanmasına izin vermedi")
    if photo.ig_status == "published":
        raise HTTPException(409, "Bu fotoğraf zaten Instagram'da yayınlandı")
    if photo.ig_status == "publishing" and photo.ig_started_at and now - photo.ig_started_at < STALE_AFTER:
        raise HTTPException(409, "Yayın sürüyor")
    recipe = await db.get(Recipe, photo.recipe_id)
    text = _sanitize_caption(caption) if caption else build_caption(recipe.name if recipe else "Tarif", photo.credit_name)
    old_container = photo.ig_container_id
    photo.ig_status, photo.ig_started_at, photo.ig_error = "publishing", now, None
    await db.commit()

    media_id = permalink = None
    container_id = old_container
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            reuse = False
            if old_container and not caption:  # önceki deneme yarım kaldıysa aynı kapsayıcıyı kontrol et (çift yayını önler)
                r = await c.get(f"{_base()}/{old_container}", params={"fields": "status_code"}, headers=_headers())
                code = r.json().get("status_code") if r.status_code == 200 else None
                if code == "PUBLISHED":
                    raise RuntimeError("Önceki deneme yayınlanmış olabilir; Instagram profilini kontrol edip elle işaretle")
                reuse = code in ("FINISHED", "IN_PROGRESS")
            if not reuse:
                r = await c.post(f"{_base()}/{settings.instagram_user_id}/media", headers=_headers(),
                                 data={"image_url": image_url(photo_id), "caption": text})
                if r.status_code != 200:
                    raise RuntimeError(_api_error(r))
                container_id = r.json()["id"]
                photo.ig_container_id = container_id
                await db.commit()
            await _wait_finished(c, container_id)
            r = await c.post(f"{_base()}/{settings.instagram_user_id}/media_publish", headers=_headers(),
                             data={"creation_id": container_id})
            if r.status_code != 200:
                raise RuntimeError(_api_error(r))
            media_id = r.json()["id"]
            r = await c.get(f"{_base()}/{media_id}", params={"fields": "permalink"}, headers=_headers())
            if r.status_code == 200:
                permalink = r.json().get("permalink")
    except (RuntimeError, httpx.HTTPError, KeyError, ValueError) as e:
        photo = await db.get(RecipePhoto, photo_id, populate_existing=True)
        if photo is None:
            raise HTTPException(409, "Fotoğraf yayın sırasında silindi")
        photo.ig_status = "failed"
        photo.ig_error = _redact(str(e) or type(e).__name__)[:500]
        await db.commit()
        return photo

    photo = await db.get(RecipePhoto, photo_id, populate_existing=True)
    if photo is None:  # yayın sürerken silindi: gönderi canlı ama kayıt yok
        raise HTTPException(409, "Fotoğraf yayın sırasında silindi; gönderi Instagram'da yayında olabilir, profili kontrol edin")
    photo.ig_status, photo.ig_media_id, photo.ig_permalink = "published", media_id, permalink
    photo.ig_published_at, photo.ig_published_by, photo.ig_error = datetime.now(timezone.utc), admin_id, None
    await db.commit()
    return photo


async def resolve_unconfirmed(db: AsyncSession, photo_id: int, admin_id: int, published: bool, permalink: str | None) -> RecipePhoto:
    """Yayın sonucu belirsiz kaldıysa (Instagram'a bakıp) yönetici elle çözer: yayınlandı işaretle ya da yeniden denemeye aç"""
    photo = await db.get(RecipePhoto, photo_id, with_for_update=True)
    if photo is None:
        raise HTTPException(404, "Fotoğraf bulunamadı")
    if photo.ig_status not in ("failed", "publishing"):
        raise HTTPException(409, "Bu fotoğrafın çözülecek bir Instagram durumu yok")
    if published:
        photo.ig_status, photo.ig_permalink = "published", (permalink or None)
        photo.ig_published_at, photo.ig_published_by, photo.ig_error = datetime.now(timezone.utc), admin_id, None
    else:
        photo.ig_status = photo.ig_container_id = photo.ig_error = None
    await db.commit()
    return photo
