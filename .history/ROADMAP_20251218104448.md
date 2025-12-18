# Roadmap

This roadmap outlines the development phases and tasks for litefs-py, a Python library for seamless SQLite replication via LiteFS with framework adapters for Django, FastAPI, and more.

## Legend

- **Phase**: Major milestone with specific goal and outcome
- **Task format**: `- [ ] TASK-{PREFIX}-XXX - Task description`
  - `[ ]` = Unchecked (not started/in progress)
  - `[x]` = Checked (completed)
  - `TASK-{PREFIX}-XXX` = Task ID with prefix and sequential number
- **Goal**: One sentence objective for the phase
- **Outcome**: What the phase achieves when completed
- **Future**: Low-priority items without specific timelines

## Current State

Project is in initial development phase. Core architecture and framework adapters are being established.

## Phase 1: Core + Django (MVP)

**Goal:** Deliver a minimal viable product with core LiteFS integration and Django adapter support.

- [ ] TASK-CORE-001 - Implement `litefs-py` core: settings, config generation, primary detection
- [ ] TASK-DJANGO-001 - Implement `litefs-django` adapter: settings reader, DB backend
- [ ] TASK-RAFT-001 - Implement static leader election (manual failover, 2-node minimum)
- [ ] TASK-CMD-001 - Create management commands (status, check)
- [ ] TASK-TEST-001 - Write unit tests with in-memory adapters
- [ ] TASK-EXAM-001 - Create example Django app in `examples/django-app/`

**Outcome:** A working Django application with LiteFS replication support, manual failover capability, and basic management tooling.

---

## Phase 2: Raft Leader Election

**Goal:** Implement automatic leader election using Raft consensus for high availability.

- [ ] TASK-RAFT-002 - Create `py-leader` package: Raft wrapper around PySyncObj (separate project)
- [ ] TASK-CORE-002 - Integrate `py-leader` into `litefs-py` as optional dependency
- [ ] TASK-RAFT-003 - Implement automatic failover (3-node quorum)
- [ ] TASK-HEALTH-001 - Add health checks with leader status
- [ ] TASK-TEST-002 - Write integration tests with multi-node Docker Compose

**Outcome:** Automatic leader election and failover with 3-node quorum support, eliminating manual intervention for high availability.

---

## Phase 3: FastAPI + Polish

**Goal:** Expand framework support and add production-ready features.

- [ ] TASK-FASTAPI-001 - Implement `litefs-fastapi` adapter: middleware, routes
- [ ] TASK-METRICS-001 - Add Prometheus metrics
- [ ] TASK-DEV-001 - Implement development mode (single-node, no replication)
- [ ] TASK-DOCS-001 - Create documentation site (ReadTheDocs or similar)

**Outcome:** FastAPI support, observability through metrics, developer-friendly single-node mode, and comprehensive documentation.

---

## Future

Ideas for future work without specific timelines:

- Graceful handling of split-brain scenarios (Raft handles this, document edge cases)
- Additional framework adapters (Flask, Starlette, etc.)
- Performance optimizations and benchmarking
- Advanced monitoring and alerting capabilities
