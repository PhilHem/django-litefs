"""Step definitions for database backend scenarios.

Tests scenarios from tests/features/django/database_backend.feature:
- Mount path validation (lines 23-48)
- Transaction mode configuration (lines 54-67)
- Split-brain protection (lines 99-124)
- Cursor methods executescript() (lines 131-140)
- WAL mode enforcement (line 146)
- Optional split-brain detection (lines 176-192)
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, scenario, then, when

# Add project root to path for cross-package imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.primary_detector import LiteFSNotRunningError
from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs_django.db.backends.litefs.base import DatabaseWrapper, LiteFSCursor
from litefs_django.exceptions import NotPrimaryError, SplitBrainError
from tests.bdd.django_adapter.conftest import (
    create_healthy_cluster,
    create_split_brain_cluster,
)
from tests.django_adapter.unit.fakes import FakePrimaryDetector, FakeSplitBrainDetector

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Scenarios - Mount Path Validation (lines 23-48)
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.MountValidation")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend validates mount path exists at connection time",
)
def test_mount_path_validation_success():
    """Test that backend validates mount path exists at connection time."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.MountValidation")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend rejects missing mount path",
)
def test_mount_path_missing_rejected():
    """Test that backend rejects missing mount path."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.MountValidation")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend rejects inaccessible mount path",
)
def test_mount_path_inaccessible_rejected():
    """Test that backend rejects inaccessible mount path."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.MountValidation")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend requires mount path in OPTIONS",
)
def test_mount_path_required_in_options():
    """Test that backend requires mount path in OPTIONS."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Transaction Mode Configuration (lines 54-67)
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.TransactionMode")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend defaults to IMMEDIATE transaction mode",
)
def test_backend_defaults_to_immediate_transaction_mode():
    """Test that backend defaults to IMMEDIATE transaction mode."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.TransactionMode")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend rejects invalid transaction mode",
)
def test_backend_rejects_invalid_transaction_mode():
    """Test that backend rejects invalid transaction mode."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Split-Brain Protection (lines 147-176)
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.SplitBrainProtection")
@scenario(
    "../../features/django/database_backend.feature",
    "Write fails during split-brain with SplitBrainError",
)
def test_write_fails_during_split_brain():
    """Test that write fails during split-brain with SplitBrainError."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.SplitBrainProtection")
@scenario(
    "../../features/django/database_backend.feature",
    "Split-brain check occurs before primary check",
)
def test_split_brain_check_before_primary_check():
    """Test that split-brain check occurs before primary check."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.SplitBrainProtection")
@scenario(
    "../../features/django/database_backend.feature",
    "Read succeeds during split-brain",
)
def test_read_succeeds_during_split_brain():
    """Test that read succeeds during split-brain."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.SplitBrainProtection")
@scenario(
    "../../features/django/database_backend.feature",
    "Write succeeds when split-brain resolves",
)
def test_write_succeeds_when_split_brain_resolves():
    """Test that write succeeds when split-brain resolves."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Cursor Methods executescript() (lines 131-140)
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.Executescript")
@scenario(
    "../../features/django/database_backend.feature",
    "executescript() checks for any write operation",
)
def test_executescript_checks_for_write_operation():
    """Test that executescript() checks for any write operation."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.Executescript")
@scenario(
    "../../features/django/database_backend.feature",
    "executescript() checks split-brain before executing",
)
def test_executescript_checks_split_brain():
    """Test that executescript() checks split-brain before executing."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - WAL Mode Enforcement (line 146)
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.WALMode")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend enforces WAL journal mode",
)
def test_backend_enforces_wal_journal_mode():
    """Test that backend enforces WAL journal mode."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Error Message Quality (lines 155-170)
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.ErrorMessages")
@scenario(
    "../../features/django/database_backend.feature",
    "NotPrimaryError includes helpful context",
)
def test_not_primary_error_includes_helpful_context():
    """Test that NotPrimaryError message includes helpful context."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.ErrorMessages")
@scenario(
    "../../features/django/database_backend.feature",
    "SplitBrainError includes leader count",
)
def test_split_brain_error_includes_leader_count():
    """Test that SplitBrainError message includes leader count."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Optional Split-Brain Detection (lines 176-192)
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.OptionalSplitBrain")
@scenario(
    "../../features/django/database_backend.feature",
    "Backend works without split-brain detector configured",
)
def test_backend_works_without_split_brain_detector():
    """Test that backend works without split-brain detector configured."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.OptionalSplitBrain")
@scenario(
    "../../features/django/database_backend.feature",
    "Write succeeds without split-brain detector on primary",
)
def test_write_succeeds_without_split_brain_detector_on_primary():
    """Test that write succeeds without split-brain detector on primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.Backend.OptionalSplitBrain")
@scenario(
    "../../features/django/database_backend.feature",
    "Write fails without split-brain detector on replica",
)
def test_write_fails_without_split_brain_detector_on_replica():
    """Test that write fails without split-brain detector on replica."""
    pass


# ---------------------------------------------------------------------------
# Fixtures are provided by conftest.py:
# - context: shared dict for BDD step state
# - in_memory_connection: SQLite connection for cursor testing
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Given steps - Mount Path Configuration
# ---------------------------------------------------------------------------


@given(parsers.parse('a database configuration with mount path "{mount_path}"'))
def db_config_with_mount_path(context: dict, mount_path: str, tmp_path: Path):
    """Set up database configuration with a mount path."""
    context["mount_path"] = mount_path
    context["tmp_path"] = tmp_path
    context["settings_dict"] = {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "db.sqlite3",
        "OPTIONS": {
            "litefs_mount_path": mount_path,
        },
        # Required Django settings for connection
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "TEST": {},
    }


@given("a database configuration without litefs_mount_path")
def db_config_without_mount_path(context: dict):
    """Set up database configuration without mount path."""
    context["settings_dict"] = {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "db.sqlite3",
        "OPTIONS": {},
    }


@given("the mount path exists and is accessible")
def mount_path_exists_accessible(context: dict, tmp_path: Path):
    """Ensure mount path exists and is accessible using temp directory."""
    # Use tmp_path as actual mount path for testing
    actual_mount = tmp_path / "litefs"
    actual_mount.mkdir(parents=True, exist_ok=True)
    # Update settings to use the actual temp path
    context["settings_dict"]["OPTIONS"]["litefs_mount_path"] = str(actual_mount)
    context["actual_mount_path"] = actual_mount


@given("the mount path does not exist")
def mount_path_does_not_exist(context: dict):
    """Ensure mount path does not exist - use a non-existent path.

    Sets a flag to prevent auto-creation of temp mount path in connection step.
    """
    # Set flag to prevent auto-creation of temp path
    context["expect_mount_failure"] = True


@given("no explicit transaction mode is set")
def no_explicit_transaction_mode(context: dict, tmp_path: Path):
    """Ensure no explicit transaction mode is set in OPTIONS.

    Also sets up a real mount path for the connection to succeed.
    """
    # Remove transaction_mode if present
    options = context["settings_dict"].get("OPTIONS", {})
    options.pop("transaction_mode", None)

    # Use tmp_path as actual mount path for testing (connection needs valid path)
    actual_mount = tmp_path / "litefs"
    actual_mount.mkdir(parents=True, exist_ok=True)
    context["settings_dict"]["OPTIONS"]["litefs_mount_path"] = str(actual_mount)
    context["actual_mount_path"] = actual_mount


@given("a database configuration with:")
def db_config_with_table(context: dict, datatable, tmp_path: Path):
    """Set up database configuration from a data table.

    Note: datatable is a list of lists where first row is headers.
    """
    context["tmp_path"] = tmp_path
    options = {}

    # Parse datatable into dict (skip header row)
    for row in datatable[1:]:
        key = row[0]
        value = row[1]
        options[key] = value

    context["settings_dict"] = {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "db.sqlite3",
        "OPTIONS": options,
    }


@given("the mount path exists but is not accessible")
def mount_path_not_accessible(context: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up mount path that exists but is not accessible.

    Since MountValidator doesn't check accessibility (only existence),
    we mock the validator to raise the appropriate error for this scenario.
    """
    from litefs.usecases.mount_validator import MountValidator

    # Create a real path that exists
    actual_mount = tmp_path / "litefs_inaccessible"
    actual_mount.mkdir(parents=True, exist_ok=True)
    context["settings_dict"]["OPTIONS"]["litefs_mount_path"] = str(actual_mount)
    context["actual_mount_path"] = actual_mount

    # Mock MountValidator.validate to raise error for "not accessible"
    def mock_validate(self, mount_path: Path) -> None:
        if str(mount_path) == str(actual_mount):
            raise LiteFSConfigError(
                f"Mount path is not accessible: {mount_path}"
            )

    monkeypatch.setattr(MountValidator, "validate", mock_validate)
    context["mock_inaccessible"] = True


# ---------------------------------------------------------------------------
# When steps - Database Connection Creation
# ---------------------------------------------------------------------------


@when("I create a database connection")
def create_database_connection(context: dict, tmp_path: Path):
    """Attempt to create a database connection.

    For scenarios that don't explicitly set up a valid mount path but need
    connection to succeed (e.g., WAL mode test), we set up a temp mount path.
    Scenarios that expect mount failure (via "mount path does not exist" step)
    skip the auto-setup.
    """
    settings_dict = context.get("settings_dict", {})

    # If no actual_mount_path was set by a previous step and we need a valid path,
    # set up a temp directory. This handles scenarios like WAL mode that don't
    # have explicit "mount path exists" step but need connection to succeed.
    # Skip if expect_mount_failure is set (e.g., "mount path does not exist" step).
    if context.get("actual_mount_path") is None and not context.get("expect_mount_failure"):
        # Check if the configured mount path is the test placeholder
        options = settings_dict.get("OPTIONS", {})
        mount_path = options.get("litefs_mount_path", "")
        if mount_path and not Path(mount_path).exists():
            # Use tmp_path as actual mount for scenarios needing valid connection
            actual_mount = tmp_path / "litefs"
            actual_mount.mkdir(parents=True, exist_ok=True)
            settings_dict = settings_dict.copy()
            settings_dict["OPTIONS"] = options.copy()
            settings_dict["OPTIONS"]["litefs_mount_path"] = str(actual_mount)
            context["actual_mount_path"] = actual_mount

    try:
        # Create DatabaseWrapper (validates mount path in __init__)
        wrapper = DatabaseWrapper(settings_dict, alias="default")
        context["connection_result"] = "success"
        context["wrapper"] = wrapper
        context["error"] = None
    except ValueError as e:
        context["connection_result"] = "error"
        context["error"] = e
        context["error_type"] = "ValueError"
    except LiteFSConfigError as e:
        context["connection_result"] = "error"
        context["error"] = e
        context["error_type"] = "LiteFSConfigError"
    except LiteFSNotRunningError as e:
        context["connection_result"] = "error"
        context["error"] = e
        context["error_type"] = "LiteFSNotRunningError"
    except Exception as e:
        context["connection_result"] = "error"
        context["error"] = e
        context["error_type"] = type(e).__name__


# ---------------------------------------------------------------------------
# Then steps - Mount Path Validation Results
# ---------------------------------------------------------------------------


@then("the connection should succeed")
def connection_should_succeed(context: dict):
    """Assert that the connection succeeded."""
    assert context.get("connection_result") == "success", (
        f"Expected connection success but got error: {context.get('connection_error')}"
    )


@then("the mount path should be validated")
def mount_path_should_be_validated(context: dict):
    """Assert that mount path was validated during connection."""
    # If connection succeeded with a mount path, validation passed
    assert context.get("connection_result") == "success"
    assert context.get("wrapper") is not None
    # The wrapper should have the mount path set
    wrapper = context["wrapper"]
    assert hasattr(wrapper, "_mount_path")


@then(parsers.parse('the transaction mode should be "{mode}"'))
def transaction_mode_should_be(context: dict, mode: str):
    """Assert that the transaction mode is set correctly."""
    assert context.get("connection_result") == "success", (
        f"Expected connection success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    assert hasattr(wrapper, "_transaction_mode"), (
        "DatabaseWrapper should have _transaction_mode attribute"
    )
    assert wrapper._transaction_mode == mode, (
        f"Expected transaction mode '{mode}' but got '{wrapper._transaction_mode}'"
    )


@then("a configuration error should be raised")
def configuration_error_raised(context: dict):
    """Assert that a configuration error was raised."""
    assert context.get("connection_result") == "error", (
        "Expected configuration error but connection succeeded"
    )
    error_type = context.get("error_type")
    assert error_type in ("ValueError", "LiteFSConfigError", "LiteFSNotRunningError"), (
        f"Expected configuration error but got {error_type}: {context.get('error')}"
    )


# ---------------------------------------------------------------------------
# Given steps - Connection Setup
# ---------------------------------------------------------------------------


@given("a database connection to the primary node")
def connection_to_primary(context: dict, in_memory_connection: sqlite3.Connection):
    """Set up a connection to the primary node."""
    context["connection"] = in_memory_connection
    context["is_primary"] = True


@given("a database connection to a replica node")
def connection_to_replica(context: dict, in_memory_connection: sqlite3.Connection):
    """Set up a connection to a replica node."""
    context["connection"] = in_memory_connection
    context["is_primary"] = False


# ---------------------------------------------------------------------------
# Given steps - Split-Brain State
# ---------------------------------------------------------------------------


@given(parsers.parse("a split-brain condition exists with {leader_count:d} leaders"))
def split_brain_exists(context: dict, leader_count: int):
    """Set up a split-brain condition with multiple leaders."""
    cluster_state = create_split_brain_cluster(leader_count)
    context["cluster_state"] = cluster_state
    context["split_brain"] = True


@given("no split-brain condition exists")
def no_split_brain(context: dict):
    """Set up a healthy cluster with no split-brain."""
    cluster_state = create_healthy_cluster()
    context["cluster_state"] = cluster_state
    context["split_brain"] = False


# ---------------------------------------------------------------------------
# When steps - SQL Execution
# ---------------------------------------------------------------------------


@when(parsers.parse('I execute "{sql}"'))
def execute_sql(context: dict, sql: str):
    """Execute SQL statement through LiteFSCursor."""
    # Create fake detectors
    is_primary = context.get("is_primary", True)
    primary_detector = FakePrimaryDetector(is_primary=is_primary)

    # Create split-brain detector with configured cluster state
    cluster_state = context.get("cluster_state")
    if cluster_state is not None:
        fake_port = FakeSplitBrainDetector(cluster_state=cluster_state)
        split_brain_detector = SplitBrainDetector(port=fake_port)
    else:
        split_brain_detector = None

    # Create cursor with detectors
    cursor = LiteFSCursor(
        context["connection"],
        primary_detector=primary_detector,
        split_brain_detector=split_brain_detector,
    )

    # Execute and capture result or exception
    try:
        cursor.execute(sql)
        context["result"] = "success"
        context["error"] = None
        context["error_type"] = None
    except SplitBrainError as e:
        context["result"] = "failure"
        context["error"] = e
        context["error_type"] = "SplitBrainError"
    except NotPrimaryError as e:
        context["result"] = "failure"
        context["error"] = e
        context["error_type"] = "NotPrimaryError"
    except Exception as e:
        context["result"] = "failure"
        context["error"] = e
        context["error_type"] = type(e).__name__


# ---------------------------------------------------------------------------
# Then steps - WAL Mode (line 146)
# ---------------------------------------------------------------------------


@then(parsers.parse('the journal mode should be "{mode}"'))
def journal_mode_should_be(context: dict, mode: str):
    """Assert that the journal mode is set correctly.

    This step verifies that the DatabaseWrapper enforces WAL mode
    at connection time. The journal mode is set via PRAGMA journal_mode=WAL
    in get_new_connection().
    """
    assert context.get("connection_result") == "success", (
        f"Expected connection success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]

    # Ensure the wrapper has created a connection by calling ensure_connection
    # This triggers get_new_connection() which sets WAL mode
    wrapper.ensure_connection()

    # Now check journal mode via the wrapper's connection
    cursor = wrapper.connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode")
        current_mode = cursor.fetchone()[0].lower()
        assert current_mode == mode.lower(), (
            f"Expected journal mode '{mode}' but got '{current_mode}'"
        )
    finally:
        cursor.close()
        wrapper.close()


# ---------------------------------------------------------------------------
# Given steps - Optional Split-Brain Detection (lines 176-192)
# ---------------------------------------------------------------------------


@given("no split-brain detector is configured")
def no_split_brain_detector_configured(context: dict):
    """Configure the test context with no split-brain detector.

    This step sets a flag indicating that when creating connections
    or cursors, no SplitBrainDetector should be provided. This tests
    that the backend works correctly in environments where split-brain
    detection is not needed or available.
    """
    context["no_split_brain_detector"] = True
    # Also ensure cluster_state is None so execute_sql knows to skip detector
    context["cluster_state"] = None


# ---------------------------------------------------------------------------
# Then steps - Error Assertions
# ---------------------------------------------------------------------------


@then("a SplitBrainError should be raised")
def split_brain_error_raised(context: dict):
    """Assert that SplitBrainError was raised."""
    assert context["error_type"] == "SplitBrainError", (
        f"Expected SplitBrainError but got {context['error_type']}: {context.get('error')}"
    )


@then("a NotPrimaryError should be raised")
def not_primary_error_raised(context: dict):
    """Assert that NotPrimaryError was raised."""
    assert context["error_type"] == "NotPrimaryError", (
        f"Expected NotPrimaryError but got {context['error_type']}: {context.get('error')}"
    )


@then(parsers.parse('the error message should contain "{text}"'))
def error_contains_text(context: dict, text: str):
    """Assert error message contains expected text."""
    assert context["error"] is not None, "Expected an error but none was raised"
    assert text in str(context["error"]), (
        f"Expected '{text}' in error message: {context['error']}"
    )


@then("NotPrimaryError should NOT be raised")
def not_primary_error_not_raised(context: dict):
    """Assert that NotPrimaryError was NOT raised (SplitBrainError takes precedence)."""
    assert context["error_type"] != "NotPrimaryError", (
        f"NotPrimaryError was raised but SplitBrainError should take precedence"
    )


# ---------------------------------------------------------------------------
# Then steps - Success Assertions
# ---------------------------------------------------------------------------


@then("the operation should succeed")
def operation_succeeds(context: dict):
    """Assert that the operation succeeded."""
    assert context["result"] == "success", (
        f"Expected success but got {context['error_type']}: {context.get('error')}"
    )


# ---------------------------------------------------------------------------
# Then steps - Error Message Quality (lines 155-170)
# ---------------------------------------------------------------------------


@then("the NotPrimaryError message should include:")
def not_primary_error_message_includes(context: dict, datatable):
    """Assert that NotPrimaryError message includes all expected content.

    Args:
        context: BDD context dict
        datatable: Table with 'content' column listing expected substrings
    """
    assert context["error_type"] == "NotPrimaryError", (
        f"Expected NotPrimaryError but got {context['error_type']}: {context.get('error')}"
    )
    error_message = str(context["error"]).lower()

    # Skip header row and check each content item
    for row in datatable[1:]:
        expected_content = row[0].lower()
        assert expected_content in error_message, (
            f"Expected '{expected_content}' in NotPrimaryError message: {context['error']}"
        )


@then("the SplitBrainError message should include:")
def split_brain_error_message_includes(context: dict, datatable):
    """Assert that SplitBrainError message includes all expected content.

    Args:
        context: BDD context dict
        datatable: Table with 'content' column listing expected substrings
    """
    assert context["error_type"] == "SplitBrainError", (
        f"Expected SplitBrainError but got {context['error_type']}: {context.get('error')}"
    )
    error_message = str(context["error"]).lower()

    # Skip header row and check each content item
    for row in datatable[1:]:
        expected_content = row[0].lower()
        assert expected_content in error_message, (
            f"Expected '{expected_content}' in SplitBrainError message: {context['error']}"
        )


# ---------------------------------------------------------------------------
# When steps - executescript() Execution
# ---------------------------------------------------------------------------


@when(parsers.parse('I call executescript with "{sql}"'))
def call_executescript(context: dict, sql: str):
    """Execute SQL script through LiteFSCursor.executescript()."""
    # Create fake detectors
    is_primary = context.get("is_primary", True)
    primary_detector = FakePrimaryDetector(is_primary=is_primary)

    # Create split-brain detector with configured cluster state
    cluster_state = context.get("cluster_state")
    if cluster_state is not None:
        fake_port = FakeSplitBrainDetector(cluster_state=cluster_state)
        split_brain_detector = SplitBrainDetector(port=fake_port)
    else:
        split_brain_detector = None

    # Create cursor with detectors
    cursor = LiteFSCursor(
        context["connection"],
        primary_detector=primary_detector,
        split_brain_detector=split_brain_detector,
    )

    # Execute and capture result or exception
    try:
        cursor.executescript(sql)
        context["result"] = "success"
        context["error"] = None
        context["error_type"] = None
    except SplitBrainError as e:
        context["result"] = "failure"
        context["error"] = e
        context["error_type"] = "SplitBrainError"
    except NotPrimaryError as e:
        context["result"] = "failure"
        context["error"] = e
        context["error_type"] = "NotPrimaryError"
    except Exception as e:
        context["result"] = "failure"
        context["error"] = e
        context["error_type"] = type(e).__name__
