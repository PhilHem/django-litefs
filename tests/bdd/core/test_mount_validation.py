"""Step definitions for mount path validation feature."""

import pytest
import tempfile
from pathlib import Path
from pytest_bdd import scenario, given, when, then, parsers

from litefs.usecases.mount_validator import MountValidator
from litefs.usecases.primary_detector import LiteFSNotRunningError
from litefs.domain.exceptions import LiteFSConfigError


# ---------------------------------------------------------------------------
# Scenarios - Configuration Validation
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.MountValidator")
@scenario(
    "../../features/core/mount_validation.feature",
    "Relative path is rejected",
)
def test_relative_path_rejected():
    """Test relative path is rejected."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.MountValidator")
@scenario(
    "../../features/core/mount_validation.feature",
    "Dot-relative path is rejected",
)
def test_dot_relative_rejected():
    """Test dot-relative path is rejected."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Runtime Validation
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.MountValidator")
@scenario(
    "../../features/core/mount_validation.feature",
    "Existing path is valid",
)
def test_existing_path_valid():
    """Test existing path is valid."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.MountValidator")
@scenario(
    "../../features/core/mount_validation.feature",
    "Non-existent path raises LiteFSNotRunningError",
)
def test_nonexistent_path_error():
    """Test non-existent path raises LiteFSNotRunningError."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Error Message Clarity
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.MountValidator")
@scenario(
    "../../features/core/mount_validation.feature",
    "Config error includes the invalid path",
)
def test_config_error_includes_path():
    """Test config error includes the invalid path."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.MountValidator")
@scenario(
    "../../features/core/mount_validation.feature",
    "Runtime error includes the missing path",
)
def test_runtime_error_includes_path():
    """Test runtime error includes the missing path."""
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    """Shared context for passing state between steps."""
    return {}


@pytest.fixture
def mount_validator():
    """Create MountValidator instance."""
    return MountValidator()


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(parsers.parse('a mount path "{path}"'))
def given_mount_path(context: dict, path: str):
    """Set mount path for validation."""
    context["mount_path"] = Path(path)
    context["path_exists"] = True  # Default assumption


@given("a mount path that exists on the filesystem")
def given_existing_mount_path(context: dict):
    """Create a temporary directory as mount path."""
    # Create a real temporary directory
    temp_dir = tempfile.mkdtemp()
    context["mount_path"] = Path(temp_dir)
    context["temp_dir"] = temp_dir
    context["path_exists"] = True


@given("the path does not exist on the filesystem")
def path_does_not_exist(context: dict):
    """Mark that the path should not exist."""
    context["path_exists"] = False


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("I validate the mount path")
def validate_mount_path(context: dict, mount_validator: MountValidator):
    """Execute mount path validation."""
    mount_path = context["mount_path"]

    try:
        mount_validator.validate(mount_path)
        context["error"] = None
        context["validation_succeeded"] = True
    except LiteFSNotRunningError as e:
        context["error"] = e
        context["validation_succeeded"] = False
    except LiteFSConfigError as e:
        context["error"] = e
        context["validation_succeeded"] = False


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("validation should succeed")
def validation_succeeds(context: dict):
    """Assert validation succeeded."""
    assert context.get("validation_succeeded") is True, (
        f"Expected validation to succeed but got error: {context.get('error')}"
    )


@then("a LiteFSConfigError should be raised")
def config_error_raised(context: dict):
    """Assert LiteFSConfigError was raised."""
    assert context["error"] is not None, (
        "Expected LiteFSConfigError but no error was raised"
    )
    assert isinstance(context["error"], LiteFSConfigError), (
        f"Expected LiteFSConfigError but got {type(context['error']).__name__}"
    )


@then("a LiteFSNotRunningError should be raised")
def not_running_error_raised(context: dict):
    """Assert LiteFSNotRunningError was raised."""
    assert context["error"] is not None, (
        "Expected LiteFSNotRunningError but no error was raised"
    )
    assert isinstance(context["error"], LiteFSNotRunningError), (
        f"Expected LiteFSNotRunningError but got {type(context['error']).__name__}"
    )


@then(parsers.parse('the error message should contain "{text}"'))
def error_message_contains(context: dict, text: str):
    """Assert error message contains expected text."""
    assert context["error"] is not None, "No error was raised"
    assert text in str(context["error"]), (
        f"Expected '{text}' in error message: '{context['error']}'"
    )
