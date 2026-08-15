"""Import every model here so Base.metadata is fully populated for Alembic autogenerate."""

from app.models.base import Base
from app.models.label import Label, TaskLabel
from app.models.org_member import OrgMember, OrgRole
from app.models.organization import Organization
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User

__all__ = [
    "Base",
    "Label",
    "OrgMember",
    "OrgRole",
    "Organization",
    "Project",
    "ProjectStatus",
    "Task",
    "TaskLabel",
    "TaskPriority",
    "TaskStatus",
    "User",
]
