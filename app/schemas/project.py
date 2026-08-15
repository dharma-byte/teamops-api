import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    status: ProjectStatus = ProjectStatus.PLANNING
    start_date: date | None = None
    target_date: date | None = None


class ProjectPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    status: ProjectStatus
    start_date: date | None
    target_date: date | None
    created_at: datetime
