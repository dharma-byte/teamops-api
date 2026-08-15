from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_task_role
from app.db.session import get_db
from app.models.org_member import OrgRole
from app.models.task import Task
from app.schemas.task import TaskPublic, TaskUpdate
from app.services.task_service import update_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskPublic)
async def get_task_endpoint(
    task: Task = Depends(require_task_role(OrgRole.MEMBER)),
) -> TaskPublic:
    return TaskPublic.model_validate(task)


@router.patch("/{task_id}", response_model=TaskPublic)
async def update_task_endpoint(
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    task: Task = Depends(require_task_role(OrgRole.MEMBER)),
) -> TaskPublic:
    updates = body.model_dump(exclude_unset=True)
    updated = await update_task(db, task, updates)
    return TaskPublic.model_validate(updated)
