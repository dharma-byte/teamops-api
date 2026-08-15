import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label, TaskLabel


class DuplicateLabelNameError(Exception):
    """Raised when creating a label whose name already exists in the org."""


async def create_label(db: AsyncSession, org_id: uuid.UUID, name: str, color: str) -> Label:
    label = Label(org_id=org_id, name=name, color=color)
    db.add(label)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateLabelNameError(name) from exc
    await db.refresh(label)
    return label


async def list_labels(db: AsyncSession, org_id: uuid.UUID) -> list[Label]:
    result = await db.execute(select(Label).where(Label.org_id == org_id).order_by(Label.name))
    return list(result.scalars().all())


async def attach_label(db: AsyncSession, task_id: uuid.UUID, label_id: uuid.UUID) -> None:
    """Idempotent: attaching an already-attached label is a no-op, not an error."""
    existing = await db.scalar(
        select(TaskLabel).where(TaskLabel.task_id == task_id, TaskLabel.label_id == label_id)
    )
    if existing is None:
        db.add(TaskLabel(task_id=task_id, label_id=label_id))
        await db.commit()


async def detach_label(db: AsyncSession, task_id: uuid.UUID, label_id: uuid.UUID) -> None:
    """Idempotent: detaching a label that isn't attached is a no-op, not an error."""
    existing = await db.scalar(
        select(TaskLabel).where(TaskLabel.task_id == task_id, TaskLabel.label_id == label_id)
    )
    if existing is not None:
        await db.delete(existing)
        await db.commit()
