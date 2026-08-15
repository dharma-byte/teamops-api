"""Small request helpers shared across integration tests — thin wrappers over
the real HTTP endpoints so each test reads as the workflow it's proving, not
a wall of boilerplate register/login calls.
"""

import uuid
from typing import Any

from httpx import AsyncClient

DEFAULT_PASSWORD = "Password123!"


async def register_and_login(
    client: AsyncClient, email: str, full_name: str = "Test User"
) -> tuple[uuid.UUID, dict[str, str]]:
    """Register + log in a fresh user, return (user_id, auth headers)."""
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": DEFAULT_PASSWORD, "full_name": full_name},
    )
    assert register_response.status_code == 201, register_response.text
    user_id = uuid.UUID(register_response.json()["id"])

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": DEFAULT_PASSWORD}
    )
    assert login_response.status_code == 200, login_response.text
    access_token = login_response.json()["access_token"]

    return user_id, {"Authorization": f"Bearer {access_token}"}


async def create_org(client: AsyncClient, headers: dict[str, str], name: str) -> uuid.UUID:
    response = await client.post("/api/v1/orgs", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def invite_member(
    client: AsyncClient,
    headers: dict[str, str],
    org_id: uuid.UUID,
    email: str,
    role: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/orgs/{org_id}/invite",
        json={"email": email, "role": role},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def create_project(
    client: AsyncClient, headers: dict[str, str], org_id: uuid.UUID, name: str
) -> uuid.UUID:
    response = await client.post(
        "/api/v1/projects", params={"org_id": str(org_id)}, json={"name": name}, headers=headers
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def create_task(
    client: AsyncClient, headers: dict[str, str], project_id: uuid.UUID, title: str
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/projects/{project_id}/tasks", json={"title": title}, headers=headers
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result
