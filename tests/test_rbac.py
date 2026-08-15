import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api import deps as api_deps
from app.core.rbac import role_satisfies
from app.models.org_member import OrgMember, OrgRole

# --- pure hierarchy logic -----------------------------------------------


@pytest.mark.parametrize(
    ("actual", "minimum", "expected"),
    [
        (OrgRole.OWNER, OrgRole.MEMBER, True),
        (OrgRole.OWNER, OrgRole.OWNER, True),
        (OrgRole.ADMIN, OrgRole.OWNER, False),
        (OrgRole.MEMBER, OrgRole.MANAGER, False),
        (OrgRole.MANAGER, OrgRole.MANAGER, True),
        (OrgRole.MANAGER, OrgRole.MEMBER, True),
    ],
)
def test_role_satisfies(actual: OrgRole, minimum: OrgRole, expected: bool) -> None:
    assert role_satisfies(actual, minimum) is expected


# --- the 403 permission suite: proves RBAC is enforced on a real route --


def _fake_membership(role: OrgRole) -> OrgMember:
    return OrgMember(id=uuid.uuid4(), org_id=uuid.uuid4(), user_id=uuid.uuid4(), role=role)


rbac_test_app = FastAPI()


@rbac_test_app.get("/admin-only")
async def admin_only_route(
    membership: OrgMember = Depends(api_deps.require_org_role(OrgRole.ADMIN)),
) -> dict[str, bool]:
    return {"ok": True}


@pytest.fixture
def client() -> TestClient:
    return TestClient(rbac_test_app)


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        (OrgRole.MEMBER, 403),
        (OrgRole.MANAGER, 403),
        (OrgRole.ADMIN, 200),
        (OrgRole.OWNER, 200),
    ],
)
def test_admin_only_route_enforces_role(
    client: TestClient, role: OrgRole, expected_status: int
) -> None:
    rbac_test_app.dependency_overrides[api_deps.get_org_membership] = lambda: _fake_membership(
        role
    )
    try:
        response = client.get("/admin-only")
        assert response.status_code == expected_status
    finally:
        rbac_test_app.dependency_overrides.clear()
