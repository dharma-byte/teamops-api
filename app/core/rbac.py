from app.models.org_member import OrgRole

_ROLE_RANK: dict[OrgRole, int] = {
    OrgRole.MEMBER: 1,
    OrgRole.MANAGER: 2,
    OrgRole.ADMIN: 3,
    OrgRole.OWNER: 4,
}


def role_satisfies(actual: OrgRole, minimum: OrgRole) -> bool:
    """True if `actual` is at or above `minimum` in the role hierarchy.

    Each role inherits every permission of the roles below it
    (owner > admin > manager > member) — never left to the frontend to enforce.
    """
    return _ROLE_RANK[actual] >= _ROLE_RANK[minimum]
