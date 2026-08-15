"""Org bootstrap + membership, against a real database.

Curl already proved these routes work; what this proves that curl couldn't is
that the org_role Postgres enum round-trips correctly (the values_callable
fix from Step 5) and that the unique org_id+user_id membership constraint is
actually enforced by Postgres, not just assumed.
"""

import uuid

from httpx import AsyncClient

from tests.integration.helpers import create_org, invite_member, register_and_login


async def test_org_creator_becomes_owner(client: AsyncClient) -> None:
    _, headers = await register_and_login(client, "owner@example.com")
    org_id = await create_org(client, headers, "Acme Inc")

    response = await client.get(f"/api/v1/orgs/{org_id}/members", headers=headers)

    assert response.status_code == 200
    members = response.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


async def test_invited_member_appears_with_requested_role(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "owner2@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    await register_and_login(client, "member2@example.com")

    invited = await invite_member(
        client, owner_headers, org_id, "member2@example.com", "manager"
    )
    assert invited["role"] == "manager"

    response = await client.get(f"/api/v1/orgs/{org_id}/members", headers=owner_headers)
    roles = {member["email"]: member["role"] for member in response.json()}
    assert roles == {"owner2@example.com": "owner", "member2@example.com": "manager"}


async def test_non_member_cannot_list_org_members(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "owner3@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    _, outsider_headers = await register_and_login(client, "outsider@example.com")

    response = await client.get(f"/api/v1/orgs/{org_id}/members", headers=outsider_headers)

    assert response.status_code == 403


async def test_member_role_cannot_invite(client: AsyncClient) -> None:
    """Inviting requires Admin+; a plain Member must be rejected server-side."""
    _, owner_headers = await register_and_login(client, "owner4@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    await register_and_login(client, "member4@example.com")
    await invite_member(client, owner_headers, org_id, "member4@example.com", "member")

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "member4@example.com", "password": "Password123!"},
    )
    member_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = await client.post(
        f"/api/v1/orgs/{org_id}/invite",
        json={"email": "someone-else@example.com", "role": "member"},
        headers=member_headers,
    )

    assert response.status_code == 403


async def test_inviting_already_registered_member_twice_is_conflict(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "owner5@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")
    await register_and_login(client, "member5@example.com")
    await invite_member(client, owner_headers, org_id, "member5@example.com", "member")

    response = await client.post(
        f"/api/v1/orgs/{org_id}/invite",
        json={"email": "member5@example.com", "role": "member"},
        headers=owner_headers,
    )

    assert response.status_code == 409


async def test_inviting_unregistered_email_is_not_found(client: AsyncClient) -> None:
    _, owner_headers = await register_and_login(client, "owner6@example.com")
    org_id = await create_org(client, owner_headers, "Acme Inc")

    response = await client.post(
        f"/api/v1/orgs/{org_id}/invite",
        json={"email": f"{uuid.uuid4()}@nowhere.com", "role": "member"},
        headers=owner_headers,
    )

    assert response.status_code == 404
