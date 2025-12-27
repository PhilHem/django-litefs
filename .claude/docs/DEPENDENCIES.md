# Dependencies

## Core (litefs-py)

| Dependency        | Required | Purpose                            |
| ----------------- | -------- | ---------------------------------- |
| pydantic          | Yes      | Domain models, settings validation |
| pyyaml            | Yes      | LiteFS YAML config generation      |
| httpx             | Yes      | LiteFS HTTP API (health, primary)  |
| PySyncObj         | V2 only  | Raft leader election               |
| prometheus-client | Optional | Metrics                            |

## Django Adapter (litefs-django)

| Dependency | Required | Purpose               |
| ---------- | -------- | --------------------- |
| litefs-py  | Yes      | Core functionality    |
| Django 5.x | Yes      | Framework integration |

## FastAPI Adapter (litefs-fastapi) - Future

| Dependency        | Required | Purpose               |
| ----------------- | -------- | --------------------- |
| litefs-py         | Yes      | Core functionality    |
| FastAPI           | Yes      | Framework integration |
| pydantic-settings | Yes      | Settings management   |

## Development Dependencies

| Dependency | Purpose                  |
| ---------- | ------------------------ |
| pytest     | Test runner              |
| pytest-cov | Coverage reporting       |
| hypothesis | Property-based testing   |
| ruff       | Linting and formatting   |
| mypy       | Static type checking     |
| pre-commit | Git hooks                |
| tox        | Multi-env testing        |
| docker     | Integration tests (FUSE) |





