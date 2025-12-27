# Package Structure (Clean Architecture)

## Monorepo Layout

```
litefs-py/
├── packages/
│   ├── litefs/                        # Core package (PyPI: litefs-py)
│   │   ├── pyproject.toml
│   │   └── src/litefs/
│   │       ├── __init__.py
│   │       ├── domain/                # [Entities] Zero external deps
│   │       │   ├── __init__.py
│   │       │   ├── settings.py        # LiteFSSettings dataclass
│   │       │   ├── config.py          # ClusterConfig, DatabaseConfig
│   │       │   └── exceptions.py      # Domain exceptions
│   │       │
│   │       ├── usecases/              # [Use Cases] Application logic
│   │       │   ├── __init__.py
│   │       │   ├── config_generator.py
│   │       │   ├── health_checker.py
│   │       │   ├── primary_detector.py
│   │       │   └── leader_election.py # V2: Raft (PySyncObj)
│   │       │
│   │       ├── adapters/              # [Interface Adapters] Generic
│   │       │   ├── __init__.py
│   │       │   ├── file_writer.py
│   │       │   └── subprocess_runner.py
│   │       │
│   │       └── bin/                   # Bundled LiteFS binaries
│   │           └── .gitkeep
│   │
│   └── litefs-django/                 # Django adapter (PyPI: litefs-django)
│       ├── pyproject.toml             # depends on litefs-py
│       └── src/litefs_django/
│           ├── __init__.py
│           ├── apps.py                # AppConfig startup hooks
│           ├── settings.py            # Read from Django settings
│           ├── db/backends/litefs/    # Django database backend
│           │   ├── __init__.py
│           │   ├── base.py
│           │   ├── features.py
│           │   └── operations.py
│           └── management/commands/
│               ├── litefs_status.py
│               └── litefs_check.py
│
├── tests/
│   ├── core/                          # Tests for litefs-py
│   │   ├── unit/
│   │   └── integration/
│   └── django/                        # Tests for django-litefs
│       ├── unit/
│       └── integration/
│
├── scripts/
│   └── download_litefs.py
├── CLAUDE.md
└── README.md
```

## Future: FastAPI Adapter

```
packages/
└── litefs-fastapi/                    # PyPI: litefs-fastapi
    ├── pyproject.toml                 # depends on litefs-py
    └── src/litefs_fastapi/
        ├── __init__.py
        ├── settings.py                # Pydantic settings integration
        ├── middleware.py              # Request middleware
        └── routes.py                  # Health endpoints
```

## Layer Mapping

| Layer              | Package        | Location           | Contents                                             |
| ------------------ | -------------- | ------------------ | ---------------------------------------------------- |
| Entities           | litefs-py      | `litefs/domain/`   | `LiteFSSettings`, `ClusterConfig`, value objects     |
| Use Cases          | litefs-py      | `litefs/usecases/` | `ConfigGenerator`, `LeaderElection`, `HealthChecker` |
| Adapters (generic) | litefs-py      | `litefs/adapters/` | File writer, subprocess runner                       |
| Adapters (Django)  | litefs-django  | `litefs_django/`   | DB backend, settings reader, commands                |
| Adapters (FastAPI) | litefs-fastapi | `litefs_fastapi/`  | Middleware, routes (future)                          |
| Frameworks         | both           | N/A                | Django, FastAPI, LiteFS binary                       |

## Architectural Charter

Decisions made via structured architecture review.

| Decision Area     | Choice                                            |
| ----------------- | ------------------------------------------------- |
| Criticality       | Application-critical                              |
| Domain complexity | Moderate orchestration                            |
| Consistency model | Strong (single primary, LiteFS-dictated)          |
| Concurrency model | Thread-safe sync (Django default)                 |
| Flow style        | Configuration + Management commands               |
| State ownership   | LiteFS owns all state (no caching)                |
| Error semantics   | Django exceptions + custom LiteFS errors          |
| Retry strategy    | None (application handles)                        |
| Observability     | Logging + Django checks + Prometheus metrics      |
| Configuration     | Django settings only (`LITEFS = {...}`)           |
| Testing           | Unit + Property-Based + Integration (Docker/FUSE) |
| Versioning        | Semantic versioning strict                        |

### Key Constraints

- Dependencies point inward only (Clean Architecture)
- LiteFS is the source of truth for cluster state
- No library-level retry; exceptions propagate to application
- PBT required for config generation and settings validation
- Deprecation warnings for at least one minor version before removal





