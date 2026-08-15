import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.org_member import OrgRole


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrgPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    plan: str
    created_at: datetime


class OrgMemberInvite(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER


class OrgMemberPublic(BaseModel):
    """A membership row joined with the public fields of the user it belongs to."""

    id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: OrgRole
    created_at: datetime
