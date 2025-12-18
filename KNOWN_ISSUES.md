# Known Issues

## Legend

- **ID**: `{PREFIX}-XXX` format (e.g., `AUTH-001`, `CACHE-002`)
- **Complexity**: `EASY` (< 30 min) | `MED` (30 min - 2 hours) | `HARD` (> 2 hours)
- **Status**: `unconfirmed` | `confirmed` | `fixed` | `wontfix`
- **Source**: `hex-analysis` | `property-test` | `concurrency-test` | `differential-test` | `unit-test` | `manual` | `roadmap-update` | `roadmap-migration` | `tech-debt`
- **Description**: Brief issue description
- **Location**: File path, function name, or component where issue occurs
- **Timestamp**: ISO 8601 format `YYYY-MM-DD`

## Unconfirmed Issues

| ID  | Complexity | Status | Source | Description | Location | Timestamp |
| --- | ---------- | ------ | ------ | ----------- | -------- | --------- |
| CORE-001 | MED | unconfirmed | arch-analysis | Config generation may not preserve all settings in round-trip (parse(generate(x)) != x). Missing property-based test for idempotence. | `litefs/usecases/config_generator.py`, `litefs/domain/settings.py` | 2025-12-18 |
| CORE-002 | MED | unconfirmed | arch-analysis | Primary detection may have race condition when multiple threads check `.primary` file simultaneously during failover. No concurrency test coverage. | `litefs/usecases/primary_detector.py` | 2025-12-18 |
| CORE-003-PBT | EASY | unconfirmed | arch-analysis | Missing property-based test for path sanitization (unit tests exist, but PBT would cover more edge cases). | `litefs/domain/settings.py` | 2025-12-18 |
| CORE-004 | MED | unconfirmed | arch-analysis | Config generation may produce invalid YAML for edge cases (empty strings, special chars, unicode). Missing property-based test for YAML validity. | `litefs/usecases/config_generator.py` | 2025-12-18 |
| CORE-005 | MED | unconfirmed | arch-analysis | Primary detection may return stale result if `.primary` file is deleted/created between check and read. No test for file system race conditions. | `litefs/usecases/primary_detector.py` | 2025-12-18 |
| CORE-006 | EASY | unconfirmed | arch-analysis | Settings normalization may not be idempotent (normalize(normalize(x)) != normalize(x)). Missing property-based test. | `litefs/domain/settings.py` | 2025-12-18 |
| CORE-007 | MED | unconfirmed | arch-analysis | Config generation may fail silently or produce partial config if required settings are missing. Missing differential test against reference LiteFS config format. | `litefs/usecases/config_generator.py` | 2025-12-18 |
| CORE-008 | MED | unconfirmed | arch-analysis | Primary detection may not handle concurrent writes to `.primary` file during leader election (V2 Raft). Missing probabilistic concurrency test. | `litefs/usecases/primary_detector.py` | 2025-12-18 |
| CORE-009 | EASY | unconfirmed | arch-analysis | Settings may accept invalid port numbers (negative, >65535, non-integer). Missing property-based test for bounds validation. | `litefs/domain/settings.py` | 2025-12-18 |
| CORE-010 | MED | unconfirmed | arch-analysis | Config generation may not preserve ordering of settings fields, causing diff noise. Missing differential test for deterministic output. | `litefs/usecases/config_generator.py` | 2025-12-18 |

## Confirmed Issues

| ID  | Complexity | Status | Source | Description | Location | Timestamp |
| --- | ---------- | ------ | ------ | ----------- | -------- | --------- |

## Resolved Issues

| ID  | Complexity | Status | Source | Description | Location | Timestamp |
| --- | ---------- | ------ | ------ | ----------- | -------- | --------- |
| CORE-003 | EASY | fixed | unit-test | Settings validation rejects path traversal attacks (e.g., `../../../etc/passwd`). Unit tests implemented. | `litefs/domain/settings.py` | 2025-12-18 |
