import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_member import OrgMember, OrgRole
from app.models.organization import Organization
from app.models.user import User


class UserNotFoundError(Exception):
    """Raised when inviting an email with no registered account yet.

    v1 keeps invites simple: the invitee must already have an account.
    Inviting a not-yet-registered email (pending-invite-by-token) is a
    reasonable Phase 2 addition, not a Phase 1 requirement.
    """


class AlreadyMemberError(Exception):
    """Raised when inviting someone who is already a member of the org."""


async def create_organization(
    db: AsyncSession, owner: User, name: str, plan: str = "free"
) -> Organization:
    """Create an org and make the creator its Owner in the same transaction."""
    org = Organization(name=name, plan=plan)
    db.add(org)
    await db.flush()  # assign org.id before the membership row references it

    membership = OrgMember(org_id=org.id, user_id=owner.id, role=OrgRole.OWNER)
    db.add(membership)

    await db.commit()
    await db.refresh(org)
    return org


async def invite_member(
    db: AsyncSession, org_id: uuid.UUID, email: str, role: OrgRole
) -> tuple[OrgMember, User]:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise UserNotFoundError(email)

    existing = await db.scalar(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user.id)
    )
    if existing is not None:
        raise AlreadyMemberError(email)

    membership = OrgMember(org_id=org_id, user_id=user.id, role=role)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership, user


async def list_members(db: AsyncSession, org_id: uuid.UUID) -> list[tuple[OrgMember, User]]:
    result = await db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(OrgMember.org_id == org_id)
        .order_by(OrgMember.created_at)
    )
    return [(member, user) for member, user in result.all()]
