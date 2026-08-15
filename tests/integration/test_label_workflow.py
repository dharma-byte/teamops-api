"""Labels: uniqueness enforced by a real Postgres constraint, and idempotent
attach/detach against the task_labels join table.
"""

from httpx import AsyncClient

from tests.integration.helpers import create_org, create_project, create_task, register_and_login


async def _create_label(
    client: AsyncClient, headers: dict[str, str], org_id: object, name: str
) -> dict[str, object]:
    response = await client.post(
        f"/api/v1/orgs/{org_id}/labels",
        json={"name": name, "color": "#3B82F6"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


async def test_duplicate_label_name_in_same_org_is_rejected_by_the_db(
    client: AsyncClient,
) -> None:
    _, headers = await register_and_login(client, "lblowner@example.com")
    org_id = await create_org(client, headers, "Acme Inc")
    await _create_label(client, headers, org_id, "bug")

    response = await client.post(
        f"/api/v1/orgs/{org_id}/labels",
        json={"name": "bug", "color": "#EF4444"},
        headers=headers,
    )

    assert response.status_code == 409


async def test_same_label_name_is_allowed_in_a_different_org(client: AsyncClient) -> None:
    _, headers = await register_and_login(client, "lblowner2@example.com")
    org_a = await create_org(client, headers, "Org A")
    org_b = await create_org(client, headers, "Org B")

    first = await _create_label(client, headers, org_a, "bug")
    second = await _create_label(client, headers, org_b, "bug")

    assert first["id"] != second["id"]


async def test_attach_and_detach_label_are_idempotent(client: AsyncClient) -> None:
    _, headers = await register_and_login(client, "lblowner3@example.com")
    org_id = await create_org(client, headers, "Acme Inc")
    project_id = await create_project(client, headers, org_id, "Q1 Launch")
    task = await create_task(client, headers, project_id, "Fix the thing")
    label = await _create_label(client, headers, org_id, "bug")
    task_id, label_id = task["id"], label["id"]

    first_attach = await client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers
    )
    second_attach = await client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers
    )
    assert first_attach.status_code == 204
    assert second_attach.status_code == 204

    first_detach = await client.delete(
        f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers
    )
    second_detach = await client.delete(
        f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers
    )
    assert first_detach.status_code == 204
    assert second_detach.status_code == 204


async def test_label_from_another_org_cannot_be_attached(client: AsyncClient) -> None:
    _, headers = await register_and_login(client, "lblowner4@example.com")
    org_a = await create_org(client, headers, "Org A")
    org_b = await create_org(client, headers, "Org B")
    project_id = await create_project(client, headers, org_a, "Q1 Launch")
    task = await create_task(client, headers, project_id, "Fix the thing")
    foreign_label = await _create_label(client, headers, org_b, "urgent")

    response = await client.post(
        f"/api/v1/tasks/{task['id']}/labels/{foreign_label['id']}", headers=headers
    )

    assert response.status_code == 404
