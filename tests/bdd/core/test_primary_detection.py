"""Step definitions for primary detection feature."""

import pytest
from pathlib import Path
from pytest_bdd import scenario, given, when, then, parsers

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError


# Scenarios - link to feature file
# BDD tests are tier 1 (unit-level, no external dependencies)


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/primary_detection.feature",
    "Node is primary when .primary file exists",
)
def test_node_is_primary():
    """Test that node detects as primary when .primary file exists."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/primary_detection.feature",
    "Node is replica when .primary file does not exist",
)
def test_node_is_replica():
    """Test that node detects as replica when .primary file is absent."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/primary_detection.feature",
    "Error when LiteFS mount path does not exist",
)
def test_error_when_not_running():
    """Test that error is raised when mount path doesn't exist."""
    pass


# Fixtures for step state

@pytest.fixture
def context():
    """Shared context for passing state between steps."""
    return {}


# Given steps

@given("a LiteFS mount path")
def given_mount_path(mount_path: Path, context: dict):
    """Set up a valid mount path."""
    context["mount_path"] = mount_path


@given('the ".primary" file exists in the mount path')
def primary_file_exists(context: dict):
    """Create the .primary file in mount path."""
    mount_path = context["mount_path"]
    primary_file = mount_path / ".primary"
    primary_file.write_text("node-1")


@given('the ".primary" file does not exist in the mount path')
def primary_file_does_not_exist(context: dict):
    """Ensure .primary file does not exist (it doesn't by default)."""
    mount_path = context["mount_path"]
    primary_file = mount_path / ".primary"
    assert not primary_file.exists()


@given("the mount path does not exist")
def mount_path_does_not_exist(nonexistent_mount_path: Path, context: dict):
    """Use a mount path that doesn't exist."""
    context["mount_path"] = nonexistent_mount_path


# When steps

@when("I check if the node is primary")
def check_if_primary(context: dict):
    """Execute primary detection check."""
    mount_path = context["mount_path"]
    detector = PrimaryDetector(mount_path=str(mount_path))

    try:
        context["result"] = detector.is_primary()
        context["error"] = None
    except LiteFSNotRunningError as e:
        context["result"] = None
        context["error"] = e


# Then steps

@then("the result should be true")
def result_is_true(context: dict):
    """Assert the result is True."""
    assert context["error"] is None, f"Unexpected error: {context['error']}"
    assert context["result"] is True


@then("the result should be false")
def result_is_false(context: dict):
    """Assert the result is False."""
    assert context["error"] is None, f"Unexpected error: {context['error']}"
    assert context["result"] is False


@then("a LiteFSNotRunningError should be raised")
def error_is_raised(context: dict):
    """Assert that LiteFSNotRunningError was raised."""
    assert context["error"] is not None, "Expected LiteFSNotRunningError but no error was raised"
    assert isinstance(context["error"], LiteFSNotRunningError)


@then(parsers.parse('the error message should contain "{text}"'))
def error_message_contains(context: dict, text: str):
    """Assert error message contains expected text."""
    assert context["error"] is not None
    assert text in str(context["error"]), f"Expected '{text}' in '{context['error']}'"
