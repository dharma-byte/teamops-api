"""Fixtures for DB-backed integration tests.

Unlike the rest of the suite (pure functions, or dependency-overridden routes
with no real database), these tests run against an actual, ephemeral Postgres
container migrated with the real Alembic scripts — the same ones applied in
production. That's the point of Step 8: prove the real SQL, constraints, and
enum-value round-tripping, not mocked calls.

One container is shared for the whole test session (starting one per test
would dominate the runtime); each test still gets full isolation via an outer
transaction that is always rolled back, so tests never see each other's data.
"""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.db.session import get_db
from app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    """Start one Postgres container for the session and migrate it to head."""
    with PostgresContainer("postgres:16-alpine", driver=None) as container:
        raw_url = container.get_connection_url()
        async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option(
            "script_location", str(REPO_ROOT / "app" / "db" / "migrations")
        )
        # Explicit override — env.py prefers this over app settings, see
        # app/db/migrations/env.py.
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)
        command.upgrade(alembic_cfg, "head")

        yield async_url


@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_url: str) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(postgres_url)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """One outer transaction per test, always rolled back at teardown.

    Service-layer code calls `db.commit()` freely (e.g. approval_service);
    `join_transaction_mode="create_savepoint"` makes those commits only
    release a SAVEPOINT, leaving the outer transaction — and therefore full
    rollback at teardown — intact.

    `expire_on_commit=False` mirrors app/db/session.py's production
    sessionmaker: without it, ORM objects returned by a service after its own
    `db.commit()` (e.g. org_service.invite_member's `user`) are expired, and
    the endpoint's plain attribute access on them (`user.id`) tries an
    implicit lazy-load outside the async greenlet bridge and blows up with
    MissingGreenlet — a fixture-only failure mode that doesn't happen in the
    real app.
    """
    async with db_engine.connect() as connection:
        await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await connection.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """An httpx client against the real ASGI app, DB calls routed to the
    per-test transaction above instead of the module-level production engine.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            yield async_client
    finally:
        app.dependency_overrides.clear()
