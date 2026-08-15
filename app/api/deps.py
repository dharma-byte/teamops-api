import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import role_satisfies
from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.org_member import OrgMember, OrgRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the caller's identity from a Bearer access token.

    This proves *who* is calling, nothing more — org-scoped role checks
    (RBAC) are a separate dependency layered on top in Step 4.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except InvalidTokenError as exc:
        raise credentials_error from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise credentials_error from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    return user


async def get_org_membership(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgMember:
    """Resolve the caller's membership row for the org in the path.

    403, not 404: confirming an org exists to a non-member leaks information
    a non-member shouldn't have.
    """
    membership = await db.scalar(
        select(OrgMember).where(
            OrgMember.org_id == org_id, OrgMember.user_id == current_user.id
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    return membership


def require_org_role(
    minimum_role: OrgRole,
) -> Callable[[OrgMember], Coroutine[Any, Any, OrgMember]]:
    """Dependency factory: require at least `minimum_role` in the org from the path.

    Usage: Depends(require_org_role(OrgRole.ADMIN)) on any endpoint whose path
    includes {org_id}. RBAC lives here, server-side, not in frontend show/hide.
    """

    async def checker(membership: OrgMember = Depends(get_org_membership)) -> OrgMember:
        if not role_satisfies(membership.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return membership

    return checker
