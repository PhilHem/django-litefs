---
name: Architecture Review Actions - Test Organization
overview: "Complete P1 tasks for test organization: delete stale test directory, move Django config to pytest fixture, and reorganize concurrency tests from unit to integration."
todos:
  - id: task-8xq-1
    content: Delete stale tests/django/ directory and verify no tests collected from it
    status: completed
  - id: task-8xq-2
    content: Move Django configuration from __init__.py to conftest.py as session-scoped autouse fixture
    status: completed
  - id: task-8xq-3
    content: Create tests/core/integration/usecases/ directory and move concurrency tests from unit to integration
    status: completed
  - id: verify-tests
    content: Run full test suite for both packages and verify all tests pass
    status: completed
    dependencies:
      - task-8xq-1
      - task-8xq-2
      - task-8xq-3
  - id: update-beads
    content: Update beads statuses for completed tasks and check epic progress
    status: completed
    dependencies:
      - verify-tests
---

# Architecture Review Actions - Test Organization

## Selected Task Group

**Epic**: `django-litefs-8xq` - Architecture Review Actions**Selected Tasks** (P1 priority, same epic, test organization focus):

1. `django-litefs-8xq.1`: Delete stale `tests/django/` directory
2. `django-litefs-8xq.2`: Move Django configuration to pytest fixture
3. `django-litefs-8xq.3`: Create core integration test directory and move concurrency tests

**Why this group**: All three tasks focus on test organization and cleanup. They share code paths (test infrastructure) and can be completed together efficiently. Completing these will advance the epic toward completion.

## Phase 1: PLAN

### Test Command

From `pytest.ini` files, tests run from package directories:

- Core tests: `cd packages/litefs && uv run pytest -n auto -m "not no_parallel" --random-order --timeout=2.5 -x --tb=short -v 2>&1 | tee /tmp/pytest_output.txt`
- Django adapter tests: `cd packages/litefs-django && uv run pytest -n auto -m "not no_parallel" --random-order --timeout=2.5 -x --tb=short -v 2>&1 | tee /tmp/pytest_output.txt`

### Test Files Affected

- `tests/django/` (to be deleted)
- `tests/django_adapter/unit/__init__.py` (to be emptied)
- `tests/django_adapter/unit/conftest.py` (to be updated)
- `tests/core/unit/usecases/test_primary_detector.py` (to be split)
- `tests/core/integration/usecases/test_primary_detector_concurrency.py` (to be created)

### Planned Test Cases

**Task 8xq.1 - Delete stale directory**:

- No new tests needed
- Verification: `pytest --collect-only` shows no tests from `tests/django/`

**Task 8xq.2 - Move Django config to fixture**:

- No new tests needed (refactor only)
- Verification: Existing tests pass with fixture-based setup

**Task 8xq.3 - Move concurrency tests**:

- No new tests needed (reorganization only)
- Verification: 
- `pytest -m unit` runs fast (no threading tests)
- `pytest -m integration` includes concurrency tests

### Beads Plan

**Status transitions**:

- `django-litefs-8xq.1`: `open` → `resolved`
- `django-litefs-8xq.2`: `open` → `resolved`
- `django-litefs-8xq.3`: `open` → `resolved`

**Epic progress**: After completing these 3 tasks, epic `django-litefs-8xq` will have 6 remaining tasks (P2 and P3).

### PBT, PCT, and Concurrency Boundary Opportunities

**No PBT opportunities identified** - These are organizational/refactoring tasks, not logic changes.**No PCT opportunities identified** - Task 8xq.3 moves existing concurrency tests but doesn't add new ones.**Concurrency boundary check**: Task 8xq.3 correctly moves concurrency tests from `@pytest.mark.unit` to `@pytest.mark.integration`, which aligns with Clean Architecture (concurrency at edges, not in domain unit tests).

### Advanced Testing Decision

**SKIP**: These are refactoring/organizational tasks. No new test logic needed.

### Contract Compliance

No `.claude/test-architecture.yaml` found. Using defaults:

- Markers: `unit`, `integration`, `concurrency`, `no_parallel` (all present)
- Tier system: Not used in this project
- Concurrency boundaries: Task 8xq.3 correctly moves concurrency tests to integration layer

### Test Execution Workflow

**Phase 2 (RED)**:

- Command: `cd packages/litefs-django && uv run pytest --collect-only 2>&1 | tee /tmp/pytest_output.txt`
- Result analysis: `grep -E "tests/django" /tmp/pytest_output.txt` (should be empty)
- Verification: No tests collected from stale directory

**Phase 3 (GREEN)**:

- Command: `cd packages/litefs-django && uv run pytest -n auto -m "not no_parallel" --random-order --timeout=2.5 -x --tb=short -v 2>&1 | tee /tmp/pytest_output.txt`
- Result analysis: `grep -E "FAILED|ERROR|passed|failed" /tmp/pytest_output.txt`
- Error analysis (if needed): `grep -A 30 "FAILED\|Error\|Assertion\|Exception\|Traceback" /tmp/pytest_output.txt | head -50`
- Verification: All tests pass with fixture-based Django setup

**Phase 4 (REFACTOR)**:

- Command: `cd packages/litefs && uv run pytest -m unit -v 2>&1 | tee /tmp/pytest_output.txt` (verify unit tests are fast)
- Command: `cd packages/litefs && uv run pytest -m integration -v 2>&1 | tee -a /tmp/pytest_output.txt` (verify concurrency tests moved)
- Result analysis: `grep -E "FAILED|ERROR|passed|failed" /tmp/pytest_output.txt`
- Verification: Unit tests run fast, integration tests include concurrency

**Phase 6 (FINAL)**:

- Command: Full suite for both packages (parallel + sequential stages)
- Result analysis: `grep -E "FAILED|ERROR|passed|failed" /tmp/pytest_output.txt`
- Verification: Zero failures

All result checking and error analysis will be done via grep from `/tmp/pytest_output.txt`, never by re-running pytest.

## Phase 2: RED (Batch Write)

**Task 8xq.1**: Verify stale directory exists and contains tests**Task 8xq.2**: Verify Django config is in `__init__.py` (will be moved)**Task 8xq.3**: Verify concurrency tests are in unit directory (will be moved)

## Phase 3: GREEN (Batch Implement)

**Task 8xq.1**: Delete `tests/django/` directory**Task 8xq.2**:

- Move Django configuration from `tests/django_adapter/unit/__init__.py` to `tests/django_adapter/unit/conftest.py` as session-scoped autouse fixture
- Empty `tests/django_adapter/unit/__init__.py`
- Remove duplicate Django setup from `tests/django_adapter/unit/conftest.py` (keep only fixture)

**Task 8xq.3**:

- Create `tests/core/integration/` directory structure
- Move concurrency test class (lines 42-265) from `test_primary_detector.py` to `test_primary_detector_concurrency.py`
- Update markers: `@pytest.mark.unit` → `@pytest.mark.integration`, keep `@pytest.mark.concurrency`
- Keep simple unit tests (lines 10-39) in original file

## Phase 4: REFACTOR (Batch Cleanup)

- Verify no duplicate Django setup code
- Verify test markers are correct
- Verify directory structure is clean

## Phase 5: ITERATE (If Needed)

Fix any test failures or import issues discovered during refactoring.

## Phase 6: FINAL

Run full test suite for both packages, verify all tests pass, update beads statuses.

## Phase 7: AUDIT

Launch verification sub-agent to confirm:

- Tempfiles exist and are recent
- Tests actually passed
- Type check passed
- Full suite ran (not just 1-2 tests)
- Both parallel and sequential tests ran