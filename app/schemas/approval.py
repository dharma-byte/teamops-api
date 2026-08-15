import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.approval import ApprovalStatus


class ApprovalDecision(BaseModel):
    """Body for both /approve and /reject — an optional note from the reviewer."""

    notes: str | None = Field(default=None, max_length=1000)


class ApprovalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    requested_by: uuid.UUID
    status: ApprovalStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    notes: str | None
    created_at: datetime
