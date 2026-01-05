# Known Issues

## Legend

- **ID**: `{PREFIX}-XXX` format (e.g., `AUTH-001`, `CACHE-002`)
- **Verification**: `unit` | `fake-adapter` | `property` | `concurrency` | `differential` | `parallel-isolation` | `tra`
- **Complexity**: `EASY` (< 30 min) | `MED` (30 min - 2 hours) | `HARD` (> 2 hours)
- **Status**: `unconfirmed` | `confirmed` | `fixed` | `wontfix`
- **Source**: `hex-analysis` | `property-test` | `concurrency-test` | `differential-test` | `unit-test` | `manual` | `roadmap-update` | `roadmap-migration` | `tech-debt`
- **Description**: Brief issue description
- **Location**: File path, function name, or component where issue occurs
- **Timestamp**: ISO 8601 format `YYYY-MM-DD`

## Unconfirmed Issues

| ID         | Verification | Complexity | Status      | Source       | Description                                                                                                                                                          | Location                                                                      | Timestamp  |
| ---------- | ------------ | ---------- | ----------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------- |

## Confirmed Issues

| ID         | Verification | Complexity | Status    | Source           | Description                                                                                                                                                                                   | Location                                                                          | Timestamp  |
| ---------- | ------------ | ---------- | --------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------- |
| DJANGO-011 | unit         | MED        | confirmed | tech-debt        | [testing] [blocking] Integration test infrastructure created with placeholder tests. Tests skip gracefully when Docker/FUSE not available. Full implementation requires Docker Compose setup. | `tests/django_adapter/integration/`                                               | 2025-12-18 |
