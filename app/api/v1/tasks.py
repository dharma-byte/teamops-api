import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_task_role
from app.db.session import get_db
from app.models.label import Label
from app.models.org_member import OrgRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.approval import ApprovalDecision, ApprovalPublic
from app.schemas.task import TaskPublic, TaskUpdate
from app.services.approval_service import (
    ApprovalAlreadyPendingError,
    NoPendingApprovalError,
    approve_task,
    reject_task,
    request_approval,
)
from app.services.label_service import attach_label, detach_label
from app.services.task_service import (
    DirectDoneTransitionError,
    ensure_not_direct_done_transition,
    update_task,
)

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
    try:
        ensure_not_direct_done_transition(updates)
    except DirectDoneTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tasks can only reach Done through the approval workflow "
            "(POST /tasks/{task_id}/approve)",
        ) from exc
    updated = await update_task(db, task, updates)
    return TaskPublic.model_validate(updated)


@router.post(
    "/{task_id}/request-approval",
    response_model=ApprovalPublic,
    status_code=status.HTTP_201_CREATED,
)
async def request_approval_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    task: Task = Depends(require_task_role(OrgRole.MEMBER)),
) -> ApprovalPublic:
    try:
        approval = await request_approval(db, task, requested_by=current_user.id)
    except ApprovalAlreadyPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An approval is already pending for this task",
        ) from exc
    return ApprovalPublic.model_validate(approval)


@router.post("/{task_id}/approve", response_model=ApprovalPublic)
async def approve_task_endpoint(
    body: ApprovalDecision,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    task: Task = Depends(require_task_role(OrgRole.MANAGER)),
) -> ApprovalPublic:
    try:
        approval = await approve_task(db, task, reviewer_id=current_user.id, notes=body.notes)
    except NoPendingApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="No pending approval for this task"
        ) from exc
    return ApprovalPublic.model_validate(approval)


@router.post("/{task_id}/reject", response_model=ApprovalPublic)
async def reject_task_endpoint(
    body: ApprovalDecision,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    task: Task = Depends(require_task_role(OrgRole.MANAGER)),
) -> ApprovalPublic:
    try:
        approval = await reject_task(db, task, reviewer_id=current_user.id, notes=body.notes)
    except NoPendingApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="No pending approval for this task"
        ) from exc
    return ApprovalPublic.model_validate(approval)


async def _get_label_in_tasks_org(db: AsyncSession, task: Task, label_id: uuid.UUID) -> Label:
    """A label can only be attached to a task in the same org it belongs to —
    without this check, a caller could tag a task with another org's label.
    """
    project = await db.get(Project, task.project_id)
    label = await db.get(Label, label_id)
    if project is None or label is None or label.org_id != project.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Label not found in this org"
        )
    return label


@router.post("/{task_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def attach_label_endpoint(
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    task: Task = Depends(require_task_role(OrgRole.MEMBER)),
) -> None:
    await _get_label_in_tasks_org(db, task, label_id)
    await attach_label(db, task_id=task.id, label_id=label_id)


@router.delete("/{task_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_label_endpoint(
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    task: Task = Depends(require_task_role(OrgRole.MEMBER)),
) -> None:
    await detach_label(db, task_id=task.id, label_id=label_id)
