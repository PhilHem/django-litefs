# litefs-py Architecture

This document captures the architectural decisions for litefs-py, a framework-agnostic Python library for SQLite replication via LiteFS.

## Overview

- **Purpose**: Framework-agnostic LiteFS integration with clean API
- **Distribution**: Core package + framework adapters (all bundling LiteFS binary)
- **Target**: Python 3.10+
- **Use Case**: Multi-node HA deployments with synchronized SQLite (Kubernetes-like HA without Kubernetes)
- **Platform**: Self-hosted (Docker Compose, VMs, bare metal) — no external services required
- **Differentiator**: Embedded Raft leader election (no Consul/Fly.io dependency)

## Package Architecture

```
PyPI Packages:
├── litefs-py           # Core (framework-agnostic)
├── litefs-django       # Django adapter
└── litefs-fastapi      # FastAPI adapter (future)
```

| Package | Dependencies | Purpose |
|---------|--------------|---------|
| `litefs-py` | pydantic, pyyaml, httpx, PySyncObj (V2) | Core: config, Raft, health, binary |
| `litefs-django` | litefs-py, Django 5.x | Django: settings, DB backend, commands |
| `litefs-fastapi` | litefs-py, FastAPI, pydantic-settings | FastAPI: middleware, routes (future) |

## Deployment Architecture

### Target Topology

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │  (nginx/traefik)│
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Container 1   │ │   Container 2   │ │   Container 3   │
│   (Primary)     │ │   (Replica)     │ │   (Replica)     │
│                 │ │                 │ │                 │
│ LiteFS :8080 ───┼─│ LiteFS :8080 ───┼─│ LiteFS :8080    │
│   ↓ (proxy)     │ │   ↓ (proxy)     │ │   ↓ (proxy)     │
│ Django :8000    │ │ Django :8000    │ │ Django :8000    │
│   ↓             │ │   ↓             │ │   ↓             │
│ /litefs/db ◄────┼─┼───────◄─────────┼─┼───────◄────────│
│ (read/write)    │ │ (read-only)     │ │ (read-only)     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Container Architecture

LiteFS proxy is **not a separate service**—it runs inside each container as the entrypoint:

```
┌─────────────────────────────────────────────────────┐
│                    Container                         │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  LiteFS Process (entrypoint)                │    │
│  │  - FUSE mount at /litefs                    │    │
│  │  - HTTP proxy on :8080                      │    │
│  │  - Spawns Django as child process           │    │
│  │  - Forwards writes to primary automatically │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │ proxies to                     │
│                     ▼                                │
│  ┌─────────────────────────────────────────────┐    │
│  │  Django/Gunicorn on :8000 (internal)        │    │
│  │  - Uses /litefs/db.sqlite3                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  Port 8080 exposed ◄─── Load balancer connects here │
└─────────────────────────────────────────────────────┘
```

### Key Deployment Points

- **Load balancer ignorance**: LB can hit any node; LiteFS proxy handles write forwarding
- **Single primary**: One node holds write lease at a time
- **Failover**: Manual in V1 (static), automatic in V2 (Raft)
- **No Kubernetes required**: Works with Docker Compose, VMs, or bare metal

### Docker Compose Example

```yaml
services:
  loadbalancer:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - app1
      - app2
      - app3

  app1:
    build: .
    expose:
      - "8080"  # LiteFS proxy (LB connects here)
    volumes:
      - litefs-data-1:/var/lib/litefs
    devices:
      - /dev/fuse:/dev/fuse
    cap_add:
      - SYS_ADMIN

  app2:
    build: .
    expose:
      - "8080"
    volumes:
      - litefs-data-2:/var/lib/litefs
    devices:
      - /dev/fuse:/dev/fuse
    cap_add:
      - SYS_ADMIN

  app3:
    build: .
    expose:
      - "8080"
    volumes:
      - litefs-data-3:/var/lib/litefs
    devices:
      - /dev/fuse:/dev/fuse
    cap_add:
      - SYS_ADMIN

volumes:
  litefs-data-1:
  litefs-data-2:
  litefs-data-3:
```

### Leader Election

No external services required. Embedded Raft consensus via PySyncObj.

| Mode | Mechanism | Auto-Failover | Phase |
|------|-----------|---------------|-------|
| `static` | Fixed primary node | No | V1 |
| `raft` | Embedded Raft (PySyncObj) | Yes | V2 |

#### Raft Leader Election (V2)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Container 1   │     │   Container 2   │     │   Container 3   │
│                 │     │                 │     │                 │
│  Django + Raft ◄├─────┼► Django + Raft ◄├─────┼► Django + Raft  │
│  (Leader)       │     │  (Follower)     │     │  (Follower)     │
│       ↓         │     │       ↓         │     │       ↓         │
│  Writes .primary│     │  Reads .primary │     │  Reads .primary │
│       ↓         │     │       ↓         │     │       ↓         │
│  LiteFS (write) │     │  LiteFS (read)  │     │  LiteFS (read)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**How it works:**
1. PySyncObj runs embedded in each Django process
2. Raft elects a leader (quorum-based, automatic failover)
3. Leader writes `.primary` file to signal LiteFS
4. LiteFS uses static lease mode; we manage the `.primary` file externally
5. If leader dies, Raft elects new leader within seconds

## Architectural Style

**Clean Architecture** (Robert C. Martin)

```
┌─────────────────────────────────────────────────────────┐
│  Frameworks & Drivers (outermost)                       │
│  - Django framework, LiteFS binary, SQLite              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Interface Adapters                              │   │
│  │  - Database backend, management commands         │   │
│  │  ┌─────────────────────────────────────────┐    │   │
│  │  │  Use Cases (Application Layer)          │    │   │
│  │  │  - Process management, config generation│    │   │
│  │  │  ┌─────────────────────────────────┐   │    │   │
│  │  │  │  Entities (Domain Layer)        │   │    │   │
│  │  │  │  - Settings, LiteFSConfig       │   │    │   │
│  │  │  └─────────────────────────────────┘   │    │   │
│  │  └─────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Dependency Rule

- Dependencies point **inward only**
- Inner layers know nothing about outer layers
- Domain layer has zero external dependencies (no Django imports)

## Decision Log

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| **Criticality** | Application-critical | Errors surface to app layer; user handles recovery |
| **Domain complexity** | Moderate orchestration | Multiple coordinated concerns: config, process, health |
| **Consistency model** | Strong (single primary) | LiteFS architecture dictates single-writer model |
| **Concurrency model** | Thread-safe sync | Django's default; one connection per thread |
| **Flow style** | Configuration + Commands | Standard Django plugin pattern |
| **State ownership** | LiteFS owns all state | No caching; always query LiteFS for fresh state |
| **Error semantics** | Django exceptions + custom | `DatabaseError` subclasses + `LiteFSNotRunningError` |
| **Retry strategy** | None | Application-critical: exceptions propagate |
| **Observability** | Logging + checks + Prometheus | Full observability for production deployments |
| **Configuration** | Django settings only | `LITEFS = {...}` dict; no separate config files |
| **Testing** | Unit + PBT + Integration | Property-based testing for config/settings |
| **Versioning** | Semantic strict | Major bump for breaking changes; deprecation period |

## Layer Mapping

| Layer | Package | Location | Responsibility |
|-------|---------|----------|----------------|
| Entities | litefs-py | `litefs/domain/` | `LiteFSSettings`, `ClusterConfig`, value objects |
| Use Cases | litefs-py | `litefs/usecases/` | `ConfigGenerator`, `LeaderElection`, `HealthChecker`, `PrimaryDetector` |
| Adapters (generic) | litefs-py | `litefs/adapters/` | File writer, subprocess runner |
| Adapters (Django) | litefs-django | `litefs_django/` | Settings reader, DB backend, commands |
| Adapters (FastAPI) | litefs-fastapi | `litefs_fastapi/` | Middleware, routes (future) |
| Frameworks | all | N/A | Django, FastAPI, LiteFS binary |

## Key Constraints

### Clean Architecture Violations to Flag

- ❌ Domain layer importing Django
- ❌ Use cases importing from interface adapters
- ❌ Business logic in management commands
- ❌ Database backend containing business rules
- ❌ Direct LiteFS process calls outside use cases

### LiteFS Constraints

- Single primary node holds write lease
- Replicas are read-only
- State queries must read from LiteFS (`.primary` file, HTTP endpoints)
- ~100 txn/sec throughput limit via FUSE

### Django Constraints

- Thread-safe sync operations (Django ORM model)
- Database backend inherits from `django.db.backends.sqlite3`
- Configuration via settings dict
- Management commands for operations

## Observability

| Component | Implementation |
|-----------|----------------|
| Logging | Standard Python logging; structured messages |
| Health checks | `./manage.py check` integration |
| Metrics | Prometheus (optional dependency) |

**Metrics exposed:**
- `litefs_is_primary` (gauge)
- `litefs_replica_lag_seconds` (gauge)
- `litefs_process_running` (gauge)

## Error Handling

| Error Type | Exception Class | When |
|------------|-----------------|------|
| Process not running | `LiteFSNotRunningError` | LiteFS process unavailable |
| Write on replica | `NotPrimaryError` | Write attempt on non-primary node |
| Config invalid | `LiteFSConfigError` | Invalid settings |
| Database errors | Django's `DatabaseError` subclasses | SQLite/connection issues |

## Testing Strategy

| Layer | Test Type | Tools |
|-------|-----------|-------|
| Domain | Unit + Property-based | pytest, Hypothesis |
| Use Cases | Unit with in-memory adapters | pytest |
| Adapters | Integration | pytest, subprocess |
| Database Backend | Integration | Docker, FUSE |

### Property-Based Testing Candidates

- Config generation: `parse(generate(settings)) == settings`
- Settings validation: All valid inputs → valid config
- Path handling: Absolute paths, no traversal

### Development Dependencies

| Dependency | Purpose                  |
|------------|--------------------------|
| pytest     | Test runner              |
| pytest-cov | Coverage reporting       |
| hypothesis | Property-based testing   |
| ruff       | Linting and formatting   |
| mypy       | Static type checking     |
| pre-commit | Git hooks                |
| tox        | Multi-env testing        |
| docker     | Integration tests (FUSE) |

## Versioning Policy

- **Semantic Versioning** (MAJOR.MINOR.PATCH)
- Breaking changes require major version bump
- Deprecation warnings for at least one minor version before removal
- LiteFS version pinned; upgrades documented in changelog

## Project Decisions

| Item | Decision |
|------|----------|
| License | MIT |
| Repository | Monorepo |
| Package name | `litefs-py` |
| Platform support | Linux and macOS (FUSE required) |
| Min cluster size | 2 nodes (static), 3+ nodes (Raft quorum) |

## Networking

LiteFS requires HTTP connectivity between nodes. Cross-network setups need external VPN/tunneling (e.g., Tailscale).

| Port | Purpose |
|------|---------|
| 20202 | LiteFS replication |
| 8080 | LiteFS proxy |
| 4321 | Raft (V2) |

