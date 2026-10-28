import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select, update

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import PasswordReset, User
from app.schemas.auth import (
    AuthResponse,
    DeleteAccountRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    SocialLoginRequest,
    TokenResponse,
    UserOut,
)
from app.services import social
from app.services.mail import send_mail

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_CODE_TTL = timedelta(hours=1)
RESET_MAX_ATTEMPTS = 5  # kod başına yanlış deneme
RESET_WINDOW = timedelta(hours=1)
RESET_MAX_PER_WINDOW = 3  # bir saatte gönderilen kod (e-posta bombardımanına karşı)


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


async def _authenticate(db: DbSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if (
        user is None
        or user.password_hash is None  # Google/Apple ile açılmış hesap
        or not verify_password(password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-posta veya şifre hatalı")
    return user


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DbSession) -> AuthResponse:
    email = body.email.lower()
    if await db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu e-posta ile kayıtlı bir hesap var")

    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: DbSession) -> AuthResponse:
    """Next.js frontend'in kullandığı JSON login."""
    return _auth_response(await _authenticate(db, body.email, body.password))


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
async def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> TokenResponse:
    """Swagger UI'daki "Authorize" butonu için OAuth2 form login."""
    user = await _authenticate(db, form.username, form.password)
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(body: DeleteAccountRequest, user: CurrentUser, db: DbSession) -> None:
    """Hesabı ve ona bağlı her şeyi (listeler, tasarruf kasası, alarmlar, şubeler) kalıcı siler.
    Mağazalar uygulama içinden hesap silmeyi zorunlu tutar. Şifreli hesapta şifre istenir."""
    if user.password_hash is not None and not verify_password(body.password or "", user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Şifre hatalı")
    await db.delete(user)
    await db.commit()


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(body: PasswordResetRequest, db: DbSession) -> dict:
    """E-postaya 6 haneli kod gönderir. Hesap olsun olmasın aynı yanıt döner (kayıtlı e-postalar sızmasın)."""
    user = await db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is not None and user.is_active:
        now = datetime.now(timezone.utc)
        recent = await db.scalar(
            select(func.count()).select_from(PasswordReset).where(
                PasswordReset.user_id == user.id, PasswordReset.created_at > now - RESET_WINDOW
            )
        )
        if recent < RESET_MAX_PER_WINDOW:
            # Önceki kodlar geçersiz: yalnız son kod kullanılabilir
            await db.execute(
                update(PasswordReset)
                .where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))
                .values(used_at=now)
            )
            code = f"{secrets.randbelow(1_000_000):06d}"
            db.add(PasswordReset(user_id=user.id, code_hash=hash_password(code), expires_at=now + RESET_CODE_TTL))
            await db.commit()
            await send_mail(
                user.email,
                "MarketKıyas şifre sıfırlama kodunuz",
                f"Şifre sıfırlama kodunuz: {code}\n\nKod 1 saat geçerlidir. Bu isteği siz yapmadıysanız bu e-postayı yok sayın.",
            )
    return {"detail": "Kayıtlı bir hesapsa e-postasına kod gönderildi"}


@router.post("/password-reset/confirm", response_model=AuthResponse)
async def confirm_password_reset(body: PasswordResetConfirm, db: DbSession) -> AuthResponse:
    """Kod doğruysa yeni şifreyi kaydeder ve oturum açar. Kod başına en fazla 5 deneme."""
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "Kod hatalı ya da süresi dolmuş")
    user = await db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is None or not user.is_active:
        raise invalid
    now = datetime.now(timezone.utc)
    reset = await db.scalar(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None), PasswordReset.expires_at > now)
        .order_by(PasswordReset.created_at.desc())
        .limit(1)
    )
    if reset is None or reset.attempts >= RESET_MAX_ATTEMPTS:
        raise invalid
    if not verify_password(body.code, reset.code_hash):
        reset.attempts += 1
        await db.commit()
        raise invalid
    reset.used_at = now
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return _auth_response(user)


@router.post("/google", response_model=AuthResponse)
async def google_login(body: SocialLoginRequest, db: DbSession) -> AuthResponse:
    """Google ile giriş/üyelik. Aynı doğrulanmış e-postayla açılmış hesap varsa ona bağlanır."""
    try:
        identity = await social.verify_google_id_token(body.id_token)
    except social.SocialAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e

    user = await db.scalar(select(User).where(User.google_sub == identity.subject))
    if user is None:
        user = await db.scalar(select(User).where(func.lower(User.email) == identity.email))
        if user is not None:
            if not identity.email_verified:
                raise HTTPException(status.HTTP_409_CONFLICT, "Bu e-posta ile kayıtlı bir hesap var; şifrenizle giriş yapın")
            user.google_sub = identity.subject
        else:
            user = User(email=identity.email, full_name=identity.name, google_sub=identity.subject, password_hash=None)
            db.add(user)
        await db.commit()
        await db.refresh(user)
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Hesap kullanılamıyor")
    return _auth_response(user)
