import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublic(BaseModel):
    """What a user is allowed to see about a user — never includes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
