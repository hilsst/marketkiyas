from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturum geçersiz veya süresi dolmuş",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_account_user(user: CurrentUser) -> User:
    """Paylaşma ve aile gibi başka kişilere açılan işlemler gerçek hesap ister (misafir olmaz)."""
    if user.is_guest:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bunun için ücretsiz hesap açmalısın")
    return user


AccountUser = Annotated[User, Depends(get_account_user)]


async def get_optional_user(
    db: DbSession, token: Annotated[str | None, Depends(optional_oauth2_scheme)]
) -> User | None:
    """Giriş zorunlu olmayan uçlar için: geçerli token varsa kullanıcı, yoksa None."""
    if not token:
        return None
    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def get_admin_user(user: AccountUser) -> User:
    """Yönetici: e-postası ADMIN_EMAILS listesinde olan üye."""
    from app.core.config import settings

    if not user.email or user.email.lower() not in settings.admin_email_list:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu işlem için yönetici olmalısın")
    return user


AdminUser = Annotated[User, Depends(get_admin_user)]
