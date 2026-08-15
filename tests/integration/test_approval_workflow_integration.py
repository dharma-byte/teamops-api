"""The approval workflow end-to-end against a real database.

tests/test_approval_workflow.py already unit-tests the pure guard function
in isolation. This proves the whole thing through the real HTTP + DB stack:
the PATCH guard, the RBAC gate on /approve (Manager+ only), the state
transitions, and — the actual reason this belongs in Step 8 — that the
approval_status enum persists its lowercase *value* ("approved") in Postgres,
not the Python member's name ("APPROVED"), which is the values_callable bug
class from Step 5.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.helpers import (
    create_org,
    create_project,
    create_task,
    invite_member,
    register_and_login,
)


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Password123!"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_task_cannot_reach_done_without_going_through_approval(
    client: AsyncClient,
) -> None:
    _, owner_headers = await register_and_login(client, "aowner@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    project_id = await create_project(client, owner_headers, org_id, "Q1 Launch")
    task = await create_task(client, owner_headers, project_id, "Ship it")

    direct_attempt = await client.patch(
        f"/api/v1/tasks/{task['id']}", json={"status": "done"}, headers=owner_headers
    )

    assert direct_attempt.status_code == 400


async def test_full_approval_cycle_persists_lowercase_enum_values(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, owner_headers = await register_and_login(client, "aowner2@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    await register_and_login(client, "amember2@example.com")
    await invite_member(client, owner_headers, org_id, "amember2@example.com", "member")
    member_headers = await _login(client, "amember2@example.com")

    project_id = await create_project(client, owner_headers, org_id, "Q1 Launch")
    task = await create_task(client, owner_headers, project_id, "Ship it")
    task_id = task["id"]

    requested = await client.post(
        f"/api/v1/tasks/{task_id}/request-approval", headers=member_headers
    )
    assert requested.status_code == 201
    approval_id = requested.json()["id"]

    task_after_request = await client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers)
    assert task_after_request.json()["status"] == "in_review"

    member_approve_attempt = await client.post(
        f"/api/v1/tasks/{task_id}/approve", json={}, headers=member_headers
    )
    assert member_approve_attempt.status_code == 403

    approved = await client.post(
        f"/api/v1/tasks/{task_id}/approve",
        json={"notes": "Looks good"},
        headers=owner_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    task_after_approval = await client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers)
    assert task_after_approval.json()["status"] == "done"

    # The actual point of running this against real Postgres: read the raw
    # column back as text and confirm it's the lowercase enum *value*, not
    # the Python member's name.
    raw_status = await db_session.scalar(
        text("SELECT status::text FROM approvals WHERE id = :id"),
        {"id": uuid.UUID(approval_id)},
    )
    assert raw_status == "approved"


async def test_rejected_task_returns_to_in_progress(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "aowner3@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    project_id = await create_project(client, owner_headers, org_id, "Q1 Launch")
    task = await create_task(client, owner_headers, project_id, "Ship it")
    task_id = task["id"]

    await client.post(f"/api/v1/tasks/{task_id}/request-approval", headers=owner_headers)
    rejected = await client.post(
        f"/api/v1/tasks/{task_id}/reject",
        json={"notes": "Not ready"},
        headers=owner_headers,
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    task_after_reject = await client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers)
    assert task_after_reject.json()["status"] == "in_progress"


async def test_approving_a_task_with_no_pending_request_is_conflict(
    client: AsyncClient,
) -> None:
    _, owner_headers = await register_and_login(client, "aowner4@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    project_id = await create_project(client, owner_headers, org_id, "Q1 Launch")
    task = await create_task(client, owner_headers, project_id, "Ship it")

    response = await client.post(
        f"/api/v1/tasks/{task['id']}/approve", json={}, headers=owner_headers
    )

    assert response.status_code == 409


async def test_requesting_approval_twice_is_conflict(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "aowner5@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    project_id = await create_project(client, owner_headers, org_id, "Q1 Launch")
    task = await create_task(client, owner_headers, project_id, "Ship it")
    task_id = task["id"]

    await client.post(f"/api/v1/tasks/{task_id}/request-approval", headers=owner_headers)
    second_request = await client.post(
        f"/api/v1/tasks/{task_id}/request-approval", headers=owner_headers
    )

    assert second_request.status_code == 409
