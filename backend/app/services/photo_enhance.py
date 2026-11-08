"""Fotoğraf iyileştirme (ücretsiz, sunucuda, Pillow): yön düzeltme, 4:5 kırpma, otomatik kontrast/renk, hafif keskinleştirme.
EXIF (konum dahil) temizlenir. Yapay zeka kullanılmaz: yemeğin kendisini değiştirmez."""

import io

from fastapi import HTTPException
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError

MAX_BYTES = 8 * 1024 * 1024
MIN_SIDE = 600
OUT_SIZE = (1200, 1500)  # 4:5 dikey
Image.MAX_IMAGE_PIXELS = 60_000_000


def enhance_photo(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Fotoğraf en fazla 8 MB olabilir")
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ("JPEG", "PNG", "WEBP", "MPO", "HEIF"):
            raise HTTPException(415, "Yalnızca JPEG, PNG veya WebP yükleyin")
        img.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(415, "Fotoğraf açılamadı") from None
    img = ImageOps.exif_transpose(img).convert("RGB")
    if min(img.size) < MIN_SIDE:
        raise HTTPException(422, f"Fotoğraf çok küçük (en az {MIN_SIDE} piksel)")
    img = ImageOps.fit(img, OUT_SIZE, method=Image.LANCZOS, centering=(0.5, 0.5))
    img = ImageOps.autocontrast(img, cutoff=1)
    luma = ImageOps.grayscale(img).resize((64, 80)).getdata()
    mean = sum(luma) / len(luma)
    if mean < 115:  # karanlık çekim: parlaklığı en fazla %35 artır
        img = ImageEnhance.Brightness(img).enhance(min(1.35, 125 / max(mean, 1)))
    img = ImageEnhance.Color(img).enhance(1.12)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=3))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85, optimize=True, progressive=True)  # EXIF yazılmaz
    return out.getvalue()
