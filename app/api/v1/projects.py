import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_org_role, require_project_role
from app.db.session import get_db
from app.models.org_member import OrgMember, OrgRole
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectPublic
from app.schemas.task import TaskCreate, TaskPublic
from app.services.project_service import create_project, list_projects
from app.services.task_service import create_task, list_tasks

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
async def create_project_endpoint(
    org_id: uuid.UUID,
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    _membership: OrgMember = Depends(require_org_role(OrgRole.MANAGER)),
) -> ProjectPublic:
    project = await create_project(
        db,
        org_id=org_id,
        name=body.name,
        status=body.status,
        start_date=body.start_date,
        target_date=body.target_date,
    )
    return ProjectPublic.model_validate(project)


@router.get("", response_model=list[ProjectPublic])
async def list_projects_endpoint(
    org_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _membership: OrgMember = Depends(require_org_role(OrgRole.MEMBER)),
) -> list[ProjectPublic]:
    projects = await list_projects(db, org_id=org_id, limit=limit, offset=offset)
    return [ProjectPublic.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectPublic)
async def get_project_endpoint(
    project: Project = Depends(require_project_role(OrgRole.MEMBER)),
) -> ProjectPublic:
    return ProjectPublic.model_validate(project)


@router.post(
    "/{project_id}/tasks", response_model=TaskPublic, status_code=status.HTTP_201_CREATED
)
async def create_task_endpoint(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    project: Project = Depends(require_project_role(OrgRole.MEMBER)),
) -> TaskPublic:
    task = await create_task(
        db,
        project_id=project.id,
        reporter_id=current_user.id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
    )
    return TaskPublic.model_validate(task)


@router.get("/{project_id}/tasks", response_model=list[TaskPublic])
async def list_tasks_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    project: Project = Depends(require_project_role(OrgRole.MEMBER)),
) -> list[TaskPublic]:
    tasks = await list_tasks(db, project_id=project.id, limit=limit, offset=offset)
    return [TaskPublic.model_validate(t) for t in tasks]
