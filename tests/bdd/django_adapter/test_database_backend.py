"""Step definitions for database backend split-brain protection scenarios.

Tests scenarios from tests/features/django/database_backend.feature:
- Write fails during split-brain with SplitBrainError (lines 151-156)
- Split-brain check occurs before primary check (lines 158-163)
- Read succeeds during split-brain (lines 165-169)
- Write succeeds when split-brain resolves (lines 171-175)
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

from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs_django.db.backends.litefs.base import LiteFSCursor
from litefs_django.exceptions import NotPrimaryError, SplitBrainError
from tests.bdd.django_adapter.conftest import (
    create_healthy_cluster,
    create_split_brain_cluster,
)
from tests.django_adapter.unit.fakes import FakePrimaryDetector, FakeSplitBrainDetector

if TYPE_CHECKING:
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
# Fixtures are provided by conftest.py:
# - context: shared dict for BDD step state
# - in_memory_connection: SQLite connection for cursor testing
# ---------------------------------------------------------------------------


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
