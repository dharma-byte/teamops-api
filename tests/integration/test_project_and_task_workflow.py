"""Project + task CRUD and pagination, against a real database.

Covers what curl testing didn't automate: the org->project role-resolution
chain (require_project_role) enforcing Manager+ for project creation, the
composite indexes not silently breaking inserts, and limit/offset pagination
actually slicing real rows.
"""

from httpx import AsyncClient

from tests.integration.helpers import (
    create_org,
    create_project,
    create_task,
    invite_member,
    register_and_login,
)


async def test_manager_can_create_project_but_member_cannot(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "powner@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    await register_and_login(client, "pmember@example.com")
    await invite_member(client, owner_headers, org_id, "pmember@example.com", "member")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "pmember@example.com", "password": "Password123!"},
    )
    member_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    member_attempt = await client.post(
        "/api/v1/projects",
        params={"org_id": str(org_id)},
        json={"name": "Should fail"},
        headers=member_headers,
    )
    assert member_attempt.status_code == 403

    owner_attempt = await client.post(
        "/api/v1/projects",
        params={"org_id": str(org_id)},
        json={"name": "Q1 Launch"},
        headers=owner_headers,
    )
    assert owner_attempt.status_code == 201
    assert owner_attempt.json()["status"] == "planning"


async def test_task_created_under_project_defaults_to_backlog(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "towner@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    project_id = await create_project(client, owner_headers, org_id, "Q1 Launch")

    task = await create_task(client, owner_headers, project_id, "Write spec")

    assert task["status"] == "backlog"
    assert task["priority"] == "medium"
    assert task["reporter_id"] is not None


async def test_task_list_pagination_slices_real_rows(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "lowner@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    project_id = await create_project(client, owner_headers, org_id, "Backlog Project")

    for i in range(5):
        await create_task(client, owner_headers, project_id, f"Task {i}")

    first_page = await client.get(
        f"/api/v1/projects/{project_id}/tasks",
        params={"limit": 2, "offset": 0},
        headers=owner_headers,
    )
    second_page = await client.get(
        f"/api/v1/projects/{project_id}/tasks",
        params={"limit": 2, "offset": 2},
        headers=owner_headers,
    )

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
    first_ids = {t["id"] for t in first_page.json()}
    second_ids = {t["id"] for t in second_page.json()}
    assert first_ids.isdisjoint(second_ids)


async def test_outsider_cannot_see_project(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "sowner@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    project_id = await create_project(client, owner_headers, org_id, "Secret Project")
    _, outsider_headers = await register_and_login(client, "soutsider@example.com")

    response = await client.get(f"/api/v1/projects/{project_id}", headers=outsider_headers)

    assert response.status_code == 403
