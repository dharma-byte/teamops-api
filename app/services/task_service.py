import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskPriority, TaskStatus


class DirectDoneTransitionError(Exception):
    """Raised when a caller tries to PATCH a task's status straight to Done.

    Done is only reachable through the approval workflow (request_approval +
    approve_task in approval_service) so there's always an auditable approver
    on record — this is the actual enforcement of that rule, not a UI nicety.
    """


def ensure_not_direct_done_transition(updates: dict[str, Any]) -> None:
    if updates.get("status") == TaskStatus.DONE:
        raise DirectDoneTransitionError()


async def create_task(
    db: AsyncSession,
    project_id: uuid.UUID,
    reporter_id: uuid.UUID,
    title: str,
    description: str | None,
    status: TaskStatus,
    priority: TaskPriority,
    assignee_id: uuid.UUID | None,
    due_date: date | None,
) -> Task:
    task = Task(
        project_id=project_id,
        reporter_id=reporter_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        due_date=due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession, project_id: uuid.UUID, limit: int, offset: int
) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def update_task(db: AsyncSession, task: Task, updates: dict[str, Any]) -> Task:
    for field, value in updates.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task
