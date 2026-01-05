# Roadmap

This roadmap outlines the development phases for litefs-py, a Python library for seamless SQLite replication via LiteFS with framework adapters for Django, FastAPI, and more.

> **Note**: Task tracking has been migrated to beads. Run `bd ready` to see available work.

## Current State

Phase 1 (Core + Django MVP) is in progress with core architecture and Django adapter established.

## Phase 1: Core + Django MVP (`django-litefs-6un`)

**Goal:** Deliver a minimal viable product with core LiteFS integration and Django adapter support.

| Task | Beads ID | Status |
|------|----------|--------|
| Core: settings, config generation, primary detection | — | ✅ Done |
| Django adapter: settings reader, DB backend | — | ✅ Done |
| Unit tests with in-memory adapters | — | ✅ Done |
| Static leader election (manual failover, 2-node) | `django-litefs-s98` | Ready |
| Management commands (status, check) | `django-litefs-tyv` | Ready |
| Example Django app | `django-litefs-49f` | Ready |

**Outcome:** A working Django application with LiteFS replication support, manual failover capability, and basic management tooling.

---

## Phase 2: Raft Leader Election (`django-litefs-zjj`)

**Goal:** Implement automatic leader election using Raft consensus for high availability.

| Task | Beads ID | Status |
|------|----------|--------|
| py-leader package: Raft wrapper around PySyncObj | `django-litefs-zjj.1` | Blocked by Phase 1 |
| Integrate py-leader into litefs-py | `django-litefs-zjj.2` | Blocked by Phase 1 |
| Automatic failover (3-node quorum) | `django-litefs-zjj.3` | Blocked by Phase 1 |
| Health checks with leader status | `django-litefs-zjj.4` | Blocked by Phase 1 |
| Multi-node Docker Compose integration tests | `django-litefs-zjj.5` | Blocked by Phase 1 |

**Outcome:** Automatic leader election and failover with 3-node quorum support.

---

## Phase 3: FastAPI + Polish (`django-litefs-kq9`)

**Goal:** Expand framework support and add production-ready features.

| Task | Beads ID | Status |
|------|----------|--------|
| litefs-fastapi adapter: middleware, routes | `django-litefs-kq9.1` | Blocked by Phase 2 |
| Prometheus metrics | `django-litefs-kq9.2` | Blocked by Phase 2 |
| Development mode (single-node, no replication) | `django-litefs-kq9.3` | Blocked by Phase 2 |
| Documentation site | `django-litefs-kq9.4` | Blocked by Phase 2 |

**Outcome:** FastAPI support, observability through metrics, developer-friendly single-node mode, and comprehensive documentation.

---

## Future Ideas

Ideas for future work (not yet scheduled):

- Graceful handling of split-brain scenarios
- Additional framework adapters (Flask, Starlette)
- Performance optimizations and benchmarking
- Advanced monitoring and alerting
