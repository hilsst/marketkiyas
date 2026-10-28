from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class FamilyJoin(BaseModel):
    code: str = Field(min_length=4, max_length=16)


class FamilyInviteCreate(BaseModel):
    email: EmailStr


class FamilyMemberOut(BaseModel):
    user_id: int
    name: str
    is_owner: bool
    joined_at: datetime


class FamilyOut(BaseModel):
    id: int
    name: str
    owner_id: int
    invite_code: str
    members: list[FamilyMemberOut]
    pending_invites: list[EmailStr]  # kabul edilmemiş e-posta davetleri
    month_saved: Decimal  # ailedeki herkesin bu ayki tasarrufu
    max_members: int


class FamilyInviteOut(BaseModel):
    """Bana gelen aile daveti (kabul kartı)."""

    id: int
    family_name: str
    invited_by: str | None


class MyFamilyOut(BaseModel):
    family: FamilyOut | None
    invites: list[FamilyInviteOut]
