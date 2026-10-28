"""Aile: üyeler birbirinin bütün listelerini görür (görünürlük: services/lists._visible_to).

- Kullanıcı aynı anda tek ailededir; aile en fazla MAX_MEMBERS kişidir.
- Katılım bir kez: aile davet koduyla ya da e-postaya gelen davetin kabulüyle.
- Kurucu üyeleri çıkarabilir; herkes ayrılabilir. Kurucu ayrılırsa kuruculuk en eski üyeye geçer,
  son kişi ayrılınca aile silinir.
"""

import secrets
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Family, FamilyInvite, FamilyMember, SavingsRecord, User
from app.schemas.family import FamilyInviteOut, FamilyMemberOut, FamilyOut, MyFamilyOut

MAX_MEMBERS = 8
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 0/O, 1/I yok
CODE_LENGTH = 8


def _name(user: User) -> str:
    return user.full_name or user.email.split("@")[0]


async def _family_of(db: AsyncSession, user: User) -> Family | None:
    return await db.scalar(
        select(Family)
        .join(FamilyMember, FamilyMember.family_id == Family.id)
        .where(FamilyMember.user_id == user.id)
        .options(selectinload(Family.members).selectinload(FamilyMember.user), selectinload(Family.invites))
        .execution_options(populate_existing=True)
    )


async def _new_code(db: AsyncSession) -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if await db.scalar(select(Family.id).where(Family.invite_code == code)) is None:
            return code


async def _ensure_free(db: AsyncSession, user: User) -> None:
    if await db.scalar(select(FamilyMember.family_id).where(FamilyMember.user_id == user.id)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Zaten bir ailedesin; önce ondan ayrılmalısın")


def _ensure_room(family: Family) -> None:
    if len(family.members) >= MAX_MEMBERS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Aile en fazla {MAX_MEMBERS} kişi olabilir")


async def my_family(db: AsyncSession, user: User) -> MyFamilyOut:
    family = await _family_of(db, user)
    invites = []
    if family is None:
        rows = await db.scalars(
            select(FamilyInvite)
            .where(func.lower(FamilyInvite.email) == user.email.lower(), FamilyInvite.accepted_at.is_(None))
            .options(selectinload(FamilyInvite.family), selectinload(FamilyInvite.invited_by))
            .order_by(FamilyInvite.created_at.desc())
        )
        invites = [
            FamilyInviteOut(id=i.id, family_name=i.family.name, invited_by=_name(i.invited_by) if i.invited_by else None)
            for i in rows
        ]
    return MyFamilyOut(family=await _family_out(db, family) if family else None, invites=invites)


async def _family_out(db: AsyncSession, family: Family) -> FamilyOut:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_saved = await db.scalar(
        select(func.coalesce(func.sum(SavingsRecord.saved_amount), 0)).where(
            SavingsRecord.user_id.in_([m.user_id for m in family.members]),
            SavingsRecord.created_at >= month_start,
        )
    )
    return FamilyOut(
        id=family.id,
        name=family.name,
        owner_id=family.owner_id,
        invite_code=family.invite_code,
        members=[
            FamilyMemberOut(user_id=m.user_id, name=_name(m.user), is_owner=m.user_id == family.owner_id, joined_at=m.joined_at)
            for m in family.members
        ],
        pending_invites=[i.email for i in family.invites if i.accepted_at is None],
        month_saved=Decimal(month_saved),
        max_members=MAX_MEMBERS,
    )


async def create_family(db: AsyncSession, user: User, name: str) -> MyFamilyOut:
    await _ensure_free(db, user)
    family = Family(name=name.strip(), owner_id=user.id, invite_code=await _new_code(db))
    family.members.append(FamilyMember(user_id=user.id))
    db.add(family)
    await db.commit()
    return await my_family(db, user)


async def _join(db: AsyncSession, user: User, family: Family) -> None:
    await _ensure_free(db, user)
    _ensure_room(family)
    family.members.append(FamilyMember(user_id=user.id))
    for invite in family.invites:
        if invite.accepted_at is None and invite.email.lower() == user.email.lower():
            invite.accepted_at = datetime.now(timezone.utc)
    await db.commit()


async def join_by_code(db: AsyncSession, user: User, code: str) -> MyFamilyOut:
    family = await db.scalar(
        select(Family)
        .where(Family.invite_code == code.strip().upper())
        .options(selectinload(Family.members), selectinload(Family.invites))
    )
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu kodla bir aile bulunamadı")
    if any(m.user_id == user.id for m in family.members):
        return await my_family(db, user)
    await _join(db, user, family)
    return await my_family(db, user)


async def accept_invite(db: AsyncSession, user: User, invite_id: int) -> MyFamilyOut:
    invite = await db.scalar(
        select(FamilyInvite)
        .where(FamilyInvite.id == invite_id, FamilyInvite.accepted_at.is_(None))
        .options(selectinload(FamilyInvite.family).selectinload(Family.members), selectinload(FamilyInvite.family).selectinload(Family.invites))
    )
    if invite is None or invite.email.lower() != user.email.lower():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Davet bulunamadı")
    await _join(db, user, invite.family)
    return await my_family(db, user)


async def decline_invite(db: AsyncSession, user: User, invite_id: int) -> None:
    invite = await db.get(FamilyInvite, invite_id)
    if invite is None or invite.email.lower() != user.email.lower():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Davet bulunamadı")
    await db.delete(invite)
    await db.commit()


async def invite_by_email(db: AsyncSession, user: User, email: str) -> MyFamilyOut:
    family = await _family_of(db, user)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Önce bir aile oluşturmalısın")
    _ensure_room(family)
    email = email.lower()
    if any(m.user.email.lower() == email for m in family.members):
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu kişi zaten ailede")
    if not any(i.email.lower() == email and i.accepted_at is None for i in family.invites):
        family.invites.append(FamilyInvite(email=email, invited_by_id=user.id))
        await db.commit()
    return await my_family(db, user)


async def remove_member(db: AsyncSession, user: User, member_id: int) -> None:
    """Kurucu herkesi çıkarabilir; diğerleri yalnızca kendini (ayrılma)."""
    family = await _family_of(db, user)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bir ailede değilsin")
    if member_id != user.id and family.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Başka bir üyeyi yalnızca ailenin kurucusu çıkarabilir")
    member = next((m for m in family.members if m.user_id == member_id), None)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu kişi ailede değil")
    family.members.remove(member)
    if not family.members:
        await db.delete(family)
    elif member_id == family.owner_id:
        family.owner_id = family.members[0].user_id  # en eski üye kurucu olur
    await db.commit()
