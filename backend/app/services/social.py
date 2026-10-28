"""Google (ve Faz 2b'de Apple) ile giriş: telefonun aldığı kimlik belirtecini doğrular."""

from dataclasses import dataclass

import httpx

from app.core.config import settings

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class SocialAuthError(Exception):
    pass


@dataclass(frozen=True)
class SocialIdentity:
    subject: str  # sağlayıcının kalıcı kullanıcı kimliği
    email: str
    email_verified: bool
    name: str | None


async def verify_google_id_token(id_token: str, *, transport: httpx.AsyncBaseTransport | None = None) -> SocialIdentity:
    """Google'ın tokeninfo ucu imzayı ve süreyi doğrular; burada uygulamamıza verildiğini (aud) ve
    Google'dan geldiğini (iss) kontrol ederiz."""
    allowed = settings.google_client_id_list
    if not allowed:
        raise SocialAuthError("Google ile giriş henüz ayarlanmadı")
    async with httpx.AsyncClient(timeout=10, transport=transport) as client:
        res = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
    if res.status_code != 200:
        raise SocialAuthError("Google oturumu doğrulanamadı")
    data = res.json()
    if data.get("aud") not in allowed or data.get("iss") not in GOOGLE_ISSUERS or not data.get("sub") or not data.get("email"):
        raise SocialAuthError("Google oturumu bu uygulama için değil")
    return SocialIdentity(
        subject=str(data["sub"]),
        email=str(data["email"]).lower(),
        email_verified=str(data.get("email_verified")).lower() == "true",
        name=data.get("name"),
    )
