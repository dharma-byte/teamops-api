import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_org_role, require_project_role
from app.db.session import get_db
from app.models.org_member import OrgMember, OrgRole
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectPublic
from app.services.project_service import create_project, list_projects

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
