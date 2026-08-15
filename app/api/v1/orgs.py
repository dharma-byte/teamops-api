import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_org_role
from app.db.session import get_db
from app.models.org_member import OrgMember, OrgRole
from app.models.user import User
from app.schemas.organization import OrgCreate, OrgMemberInvite, OrgMemberPublic, OrgPublic
from app.services.org_service import (
    AlreadyMemberError,
    UserNotFoundError,
    create_organization,
    invite_member,
    list_members,
)

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.post("", response_model=OrgPublic, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgPublic:
    org = await create_organization(db, owner=current_user, name=body.name)
    return OrgPublic.model_validate(org)


@router.post(
    "/{org_id}/invite", response_model=OrgMemberPublic, status_code=status.HTTP_201_CREATED
)
async def invite_org_member(
    org_id: uuid.UUID,
    body: OrgMemberInvite,
    db: AsyncSession = Depends(get_db),
    _membership: OrgMember = Depends(require_org_role(OrgRole.ADMIN)),
) -> OrgMemberPublic:
    try:
        membership, user = await invite_member(db, org_id, body.email, body.role)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered user found with that email",
        ) from exc
    except AlreadyMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already a member"
        ) from exc

    return OrgMemberPublic(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.get("/{org_id}/members", response_model=list[OrgMemberPublic])
async def get_org_members(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership: OrgMember = Depends(require_org_role(OrgRole.MEMBER)),
) -> list[OrgMemberPublic]:
    members = await list_members(db, org_id)
    return [
        OrgMemberPublic(
            id=member.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            created_at=member.created_at,
        )
        for member, user in members
    ]
