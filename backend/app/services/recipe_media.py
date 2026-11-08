"""Tarif fotoğrafları: backend/media/recipes/<slug>.jpg dosyası varsa tarifin görseli odur.

Veritabanındaki image_url doluysa o kullanılır (ör. harici/CDN adresi); boşsa dosya klasöründe aranır.
Dönen yol göreli ("/media/recipes/x.jpg"); mobil uygulama API adresine ekler.
"""

from functools import lru_cache
from pathlib import Path

RECIPE_MEDIA_DIR = Path(__file__).resolve().parents[2] / "media" / "recipes"
_EXTS = (".jpg", ".jpeg", ".png", ".webp")


@lru_cache(maxsize=4)
def _files(dir_mtime: float) -> dict[str, str]:
    found: dict[str, str] = {}
    if RECIPE_MEDIA_DIR.is_dir():
        for p in sorted(RECIPE_MEDIA_DIR.iterdir()):
            if p.suffix.lower() in _EXTS:
                found.setdefault(p.stem, p.name)
    return found


def recipe_image_url(slug: str, stored: str | None) -> str | None:
    if stored:
        return stored
    try:
        mtime = RECIPE_MEDIA_DIR.stat().st_mtime
    except OSError:
        return None
    name = _files(mtime).get(slug)
    return f"/media/recipes/{name}" if name else None
