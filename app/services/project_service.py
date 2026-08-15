import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus


async def create_project(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str,
    status: ProjectStatus,
    start_date: date | None,
    target_date: date | None,
) -> Project:
    project = Project(
        org_id=org_id,
        name=name,
        status=status,
        start_date=start_date,
        target_date=target_date,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def list_projects(
    db: AsyncSession, org_id: uuid.UUID, limit: int, offset: int
) -> list[Project]:
    result = await db.execute(
        select(Project)
        .where(Project.org_id == org_id)
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
