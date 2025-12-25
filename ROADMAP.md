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

- [x] TASK-CORE-001 - Implement `litefs-py` core: settings, config generation, primary detection (fixes CORE-001, CORE-011, CORE-012, CORE-015, PARSE-001; wontfix CORE-005, CORE-006, CORE-007, CORE-008, CORE-009, CORE-016, PARSE-002)
- [x] TASK-DJANGO-001 - Implement `litefs-django` adapter: settings reader, DB backend (fixes DJANGO-001, DJANGO-002, DJANGO-006, DJANGO-007, DJANGO-008, DJANGO-009, DJANGO-010, DJANGO-014, DJANGO-020, DJANGO-021, DJANGO-022, DJANGO-028, DJANGO-029, DJANGO-030, DJANGO-031, DJANGO-033, DJANGO-034, PERF-001, CONC-002, SQL-001, SQL-002, SQL-003, PROP-002; wontfix DJANGO-003, DJANGO-032, CONC-001, CONC-003, CONC-004, SQL-004, SQL-005, CONC-005, CONC-006, SQL-007, SQL-008, SQL-009, SQL-010, PROP-001)
- [ ] TASK-RAFT-001 - Implement static leader election (manual failover, 2-node minimum) (prerequisite issues fixed: RAFT-001, RAFT-002, RAFT-003, RAFT-004, RAFT-005, RAFT-006, RAFT-007)
- [ ] TASK-CMD-001 - Create management commands (status, check)
- [x] TASK-TEST-001 - Write unit tests with in-memory adapters (fixes ARCH-001, RAFT-001, RAFT-002, RAFT-003, RAFT-004, RAFT-005, RAFT-006, RAFT-007; concurrency tests added: Django backend - DJANGO-012, DJANGO-015, DJANGO-016, DJANGO-017, DJANGO-018, DJANGO-019, DJANGO-004, DJANGO-023, DJANGO-005, DJANGO-024, DJANGO-025, DJANGO-026, DJANGO-027; PrimaryDetector - CORE-002, CORE-013, CORE-014; property-based tests added: path sanitization - CORE-003-PBT, YAML generation - CORE-004, config determinism - CORE-010, SQL parsing - RAFT-005, RAFT-006)
- [ ] TASK-EXAM-001 - Create example Django app in `examples/django-app/`

**Outcome:** A working Django application with LiteFS replication support, manual failover capability, and basic management tooling.

---

## Phase 2: Raft Leader Election

**Goal:** Implement automatic leader election using Raft consensus for high availability.

- [ ] TASK-RAFT-002 - Create `py-leader` package: Raft wrapper around PySyncObj (separate project)
- [ ] TASK-CORE-002 - Integrate `py-leader` into `litefs-py` as optional dependency
- [ ] TASK-RAFT-003 - Implement automatic failover (3-node quorum)
- [ ] TASK-HEALTH-001 - Add health checks with leader status
- [ ] TASK-TEST-002 - Write integration tests with multi-node Docker Compose (infrastructure created, see DJANGO-011; infrastructure improvements: INTEG-001, INTEG-002, INTEG-004; multi-node tests deferred: INTEG-003)

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

