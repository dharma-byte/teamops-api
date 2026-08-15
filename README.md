# TeamOps API

Backend for **TeamOps** — a multi-tenant project management platform with
role-based access control, an auditable approval workflow, and (planned)
real-time collaboration.

Every task's move to **Done** is gated behind a Manager+ approval, recorded
as its own auditable row — that gate is the product's core differentiator,
not a UI nicety. See [Approval workflow](#approval-workflow) below.

## Tech stack

| Layer          | Choice                                                   |
| -------------- | --------------------------------------------------------- |
| Language       | Python 3.12                                                |
| Web framework  | FastAPI (async)                                             |
| ORM            | SQLAlchemy 2.0 (async) + asyncpg                            |
| Migrations     | Alembic (async template)                                    |
| Database       | PostgreSQL 16                                                |
| Auth           | JWT (access + refresh) via python-jose, bcrypt password hashing |
| Package manager| [uv](https://docs.astral.sh/uv/)                             |
| Lint / types   | Ruff + mypy (strict)                                         |
| Testing        | pytest, pytest-asyncio, httpx, Testcontainers (real Postgres)|
| Local infra    | Docker Compose (Postgres, Redis, MinIO)                      |

## Project structure

```
app/
  main.py                 FastAPI app, /healthz, router mounting
  core/
    config.py              Settings (pydantic-settings, reads .env)
    security.py             Password hashing, JWT issue/verify
    rbac.py                  Role hierarchy (role_satisfies)
  db/
    session.py               Async engine + get_db() dependency
    migrations/               Alembic env + versioned migration scripts
  models/                    SQLAlchemy ORM models (one file per resource)
  schemas/                    Pydantic request/response models
  services/                    Business logic, framework-free
  api/
    deps.py                    Auth + RBAC dependency chain
    v1/                         Versioned routers (auth, orgs, projects, tasks, labels, users)
tests/
  test_*.py                   Fast, DB-free unit tests
  integration/                Testcontainers-backed tests against real Postgres
```

### RBAC model

Roles form a hierarchy: `owner > admin > manager > member`. Since most
endpoints only have a project or task id in the URL — not an org id — the
RBAC dependency chain in `app/api/deps.py` resolves upward as needed:

- `require_org_role`    — org id is in the path
- `require_project_role` — resolves project → org, then checks role
- `require_task_role`    — resolves task → project → org, then checks role

Every dependency factory takes a **minimum** role; a caller must have that
role or higher in the relevant org.

### Approval workflow

`PATCH /tasks/{id}` refuses to set `status=done` directly (400). The only
path to Done is:

1. `POST /tasks/{id}/request-approval` — task moves to `in_review`, an
   `Approval` row is created (`pending`)
2. `POST /tasks/{id}/approve` (Manager+ only) — task moves to `done`, the
   approval row is stamped with reviewer, timestamp, and optional notes
3. `POST /tasks/{id}/reject` (Manager+ only) — task returns to
   `in_progress`, approval row marked `rejected`

This guarantees every task that reaches Done has an auditable approver on
record.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker Desktop (for Postgres/Redis/MinIO locally, and for the
  Testcontainers integration tests)

## Getting started

```bash
git clone <this-repo>
cd teamops-api
uv sync                              # installs runtime + dev dependencies
cp .env.example .env                 # defaults work as-is for local dev
docker compose up -d db              # Postgres 16 on localhost:5432
uv run alembic upgrade head          # apply all migrations
uv run uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Interactive docs (Swagger UI) are
at `http://localhost:8000/docs`; a liveness check is at `GET /healthz`.

To also bring up Redis and MinIO (not yet wired into the app, reserved for
Phase 2 features):

```bash
docker compose up -d
```

There is no `api` service in `docker-compose.yml` yet — the FastAPI app runs
directly via `uv run uvicorn` against the Dockerized Postgres above. A
`Dockerfile` exists for building a standalone image of the API (e.g. for
deployment):

```bash
docker build -t teamops-api .
docker run --rm -p 8000:8000 --env-file .env teamops-api
```

### Environment variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable                       | Default                                                         | Purpose                                  |
| ------------------------------- | ---------------------------------------------------------------- | ----------------------------------------- |
| `APP_NAME`                        | `TeamOps API`                                                       | Display name                                |
| `ENVIRONMENT`                     | `development`                                                       | `development` \| `staging` \| `production`  |
| `DEBUG`                           | `true`                                                               | Echoes SQL when true                        |
| `DATABASE_URL`                    | `postgresql+asyncpg://teamops:teamops@localhost:5432/teamops`        | Async Postgres connection string            |
| `REDIS_URL`                       | `redis://localhost:6379/0`                                           | Reserved for Phase 2 (caching, rate limits) |
| `JWT_SECRET_KEY`                  | `change-me-in-production`                                            | **Must be overridden outside local dev**    |
| `JWT_ALGORITHM`                   | `HS256`                                                               | JWT signing algorithm                       |
| `ACCESS_TOKEN_EXPIRE_MINUTES`     | `15`                                                                  | Access token lifetime                       |
| `REFRESH_TOKEN_EXPIRE_DAYS`       | `7`                                                                   | Refresh token lifetime                      |

## Database migrations

Migrations live in `app/db/migrations/versions/`, generated with Alembic's
autogenerate and hand-cleaned for style.

```bash
uv run alembic upgrade head                        # apply all pending migrations
uv run alembic revision --autogenerate -m "message" # generate a new migration from model changes
uv run alembic check                                # fail if models and migrations have drifted
uv run alembic downgrade -1                         # roll back one migration
```

## Testing

```bash
uv run pytest                 # everything: unit + integration
uv run pytest tests -k "not integration"   # fast, DB-free unit tests only
uv run pytest tests/integration             # Testcontainers integration tests only
```

`tests/integration/` spins up a real, ephemeral Postgres container per test
session (via Testcontainers), migrates it with the actual Alembic scripts,
and runs every test inside a transaction that's rolled back afterward for
isolation. **Docker must be running** for these — they will not run without
it. The first run pulls `postgres:16-alpine` if it isn't cached locally.

## Linting and type-checking

```bash
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy app          # strict type-check
```

All three run in CI on every PR and on push to `main` (`.github/workflows/ci.yml`).

## API overview

Base path for all versioned routes: `/api/v1`. All routes except
`/auth/register`, `/auth/login`, `/auth/refresh`, and `/healthz` require a
`Authorization: Bearer <access_token>` header.

### Auth

| Method | Path             | Description                          |
| ------ | ---------------- | ------------------------------------- |
| POST   | `/auth/register` | Create a user account                  |
| POST   | `/auth/login`    | Exchange credentials for a token pair  |
| POST   | `/auth/refresh`  | Exchange a refresh token for a new pair|

### Users

| Method | Path        | Description              |
| ------ | ----------- | -------------------------- |
| GET    | `/users/me` | The authenticated caller    |

### Organizations

| Method | Path                     | Min. role | Description                          |
| ------ | ------------------------ | --------- | ------------------------------------- |
| POST   | `/orgs`                  | —         | Create an org (creator becomes Owner)  |
| POST   | `/orgs/{org_id}/invite`  | Admin     | Invite an existing registered user      |
| GET    | `/orgs/{org_id}/members` | Member    | List org members                        |

### Labels

| Method | Path                     | Min. role | Description                |
| ------ | ------------------------ | --------- | ---------------------------- |
| POST   | `/orgs/{org_id}/labels`  | Member    | Create a label (unique per org)|
| GET    | `/orgs/{org_id}/labels`  | Member    | List labels in an org           |

### Projects

| Method | Path                              | Min. role | Description                     |
| ------ | ---------------------------------- | --------- | --------------------------------- |
| POST   | `/projects?org_id={org_id}`         | Manager   | Create a project                    |
| GET    | `/projects?org_id={org_id}`         | Member    | List projects (paginated)            |
| GET    | `/projects/{project_id}`            | Member    | Get a project                         |
| POST   | `/projects/{project_id}/tasks`      | Member    | Create a task under a project           |
| GET    | `/projects/{project_id}/tasks`      | Member    | List tasks under a project (paginated)   |

### Tasks

| Method | Path                                    | Min. role | Description                                  |
| ------ | ---------------------------------------- | --------- | ----------------------------------------------- |
| GET    | `/tasks/{task_id}`                        | Member    | Get a task                                        |
| PATCH  | `/tasks/{task_id}`                        | Member    | Update a task (rejects `status=done` directly)      |
| POST   | `/tasks/{task_id}/request-approval`        | Member    | Request approval to close the task                   |
| POST   | `/tasks/{task_id}/approve`                 | Manager   | Approve → task becomes `done`                          |
| POST   | `/tasks/{task_id}/reject`                  | Manager   | Reject → task returns to `in_progress`                  |
| POST   | `/tasks/{task_id}/labels/{label_id}`       | Member    | Attach a label (idempotent)                               |
| DELETE | `/tasks/{task_id}/labels/{label_id}`       | Member    | Detach a label (idempotent)                                |

List endpoints accept `limit` (default 20, max 100) and `offset` (default 0)
query parameters.

## Roadmap

The backend build followed an 8-step route: scaffold & tooling → data layer
→ auth → RBAC → Organizations vertical slice → Projects/Tasks/Labels →
approval workflow → Testcontainers integration tests. All eight are done.

Not yet started: real-time collaboration (WebSockets), Redis-backed refresh
token revocation, and the `teamops-web` frontend.
