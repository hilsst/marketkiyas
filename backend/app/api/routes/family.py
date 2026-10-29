from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.family import FamilyCreate, FamilyInviteCreate, FamilyJoin, MyFamilyOut
from app.services import family as svc

router = APIRouter(prefix="/family", tags=["family"])


@router.get("", response_model=MyFamilyOut)
async def get_family(user: CurrentUser, db: DbSession) -> MyFamilyOut:
    """Ailem ve (ailesi yoksa) bana gelen davetler."""
    return await svc.my_family(db, user)


@router.post("", response_model=MyFamilyOut, status_code=status.HTTP_201_CREATED)
async def create_family(body: FamilyCreate, user: CurrentUser, db: DbSession) -> MyFamilyOut:
    return await svc.create_family(db, user, body.name)


@router.post("/join", response_model=MyFamilyOut)
async def join_family(body: FamilyJoin, user: CurrentUser, db: DbSession) -> MyFamilyOut:
    return await svc.join_by_code(db, user, body.code)


@router.post("/invites", response_model=MyFamilyOut)
async def invite(body: FamilyInviteCreate, user: CurrentUser, db: DbSession) -> MyFamilyOut:
    return await svc.invite_by_email(db, user, body.email)


@router.post("/invites/{invite_id}/accept", response_model=MyFamilyOut)
async def accept(invite_id: int, user: CurrentUser, db: DbSession) -> MyFamilyOut:
    return await svc.accept_invite(db, user, invite_id)


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def decline(invite_id: int, user: CurrentUser, db: DbSession) -> None:
    await svc.decline_invite(db, user, invite_id)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(member_id: int, user: CurrentUser, db: DbSession) -> None:
    """Kurucu üye çıkarır; üye kendi id'siyle aileden ayrılır."""
    await svc.remove_member(db, user, member_id)
