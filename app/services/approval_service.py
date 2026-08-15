import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval, ApprovalStatus
from app.models.task import Task, TaskStatus


class ApprovalAlreadyPendingError(Exception):
    """Raised when requesting approval on a task that already has one pending."""


class NoPendingApprovalError(Exception):
    """Raised when approving/rejecting a task with no pending approval request."""


async def _get_pending_approval(db: AsyncSession, task_id: uuid.UUID) -> Approval | None:
    result: Approval | None = await db.scalar(
        select(Approval).where(
            Approval.task_id == task_id, Approval.status == ApprovalStatus.PENDING
        )
    )
    return result


async def request_approval(db: AsyncSession, task: Task, requested_by: uuid.UUID) -> Approval:
    if await _get_pending_approval(db, task.id) is not None:
        raise ApprovalAlreadyPendingError()

    approval = Approval(task_id=task.id, requested_by=requested_by, status=ApprovalStatus.PENDING)
    db.add(approval)
    task.status = TaskStatus.IN_REVIEW
    await db.commit()
    await db.refresh(approval)
    return approval


async def approve_task(
    db: AsyncSession, task: Task, reviewer_id: uuid.UUID, notes: str | None
) -> Approval:
    approval = await _get_pending_approval(db, task.id)
    if approval is None:
        raise NoPendingApprovalError()

    approval.status = ApprovalStatus.APPROVED
    approval.reviewed_by = reviewer_id
    approval.reviewed_at = datetime.now(UTC)
    approval.notes = notes
    task.status = TaskStatus.DONE  # the only code path that can set this
    await db.commit()
    await db.refresh(approval)
    return approval


async def reject_task(
    db: AsyncSession, task: Task, reviewer_id: uuid.UUID, notes: str | None
) -> Approval:
    approval = await _get_pending_approval(db, task.id)
    if approval is None:
        raise NoPendingApprovalError()

    approval.status = ApprovalStatus.REJECTED
    approval.reviewed_by = reviewer_id
    approval.reviewed_at = datetime.now(UTC)
    approval.notes = notes
    task.status = TaskStatus.IN_PROGRESS  # back to active work, not backlog
    await db.commit()
    await db.refresh(approval)
    return approval
