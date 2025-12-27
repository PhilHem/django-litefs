"""Step definitions for litefs_process.feature.

BDD tests for LiteFS process detection covering:
- LiteFS mount detection
- Primary node detection
- Primary URL discovery
- Mount path validation
- Caching behavior
"""

import pytest
from pathlib import Path
from pytest_bdd import scenario, given, when, then, parsers

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs.usecases.primary_url_detector import PrimaryURLDetector
from litefs.usecases.cached_primary_detector import CachedPrimaryDetector
from litefs.domain.settings import LiteFSSettings
from litefs.domain.exceptions import LiteFSConfigError


# ===========================================================================
# Scenarios - LiteFS Mount Detection
# ===========================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "LiteFS detected when mount path exists",
)
def test_litefs_detected_when_mount_exists():
    """Test LiteFS is detected when mount path exists."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "LiteFS not detected when mount path missing",
)
def test_litefs_not_detected_when_mount_missing():
    """Test LiteFS not detected when mount path missing."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "LiteFSNotRunningError raised for operations requiring LiteFS",
)
def test_error_raised_for_operations_requiring_litefs():
    """Test error raised when LiteFS required but not running."""
    pass


# ===========================================================================
# Scenarios - Primary Node Detection
# ===========================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Node is primary when .primary file exists",
)
def test_node_is_primary_when_file_exists():
    """Test node detected as primary when .primary file exists."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Node is replica when .primary file missing",
)
def test_node_is_replica_when_file_missing():
    """Test node detected as replica when .primary file missing."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Primary check is idempotent",
)
def test_primary_check_is_idempotent():
    """Test primary check is idempotent."""
    pass


# ===========================================================================
# Scenarios - Primary URL Discovery
# ===========================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryURLDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Primary URL read from .primary file content",
)
def test_primary_url_read_from_file():
    """Test primary URL is read from .primary file content."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryURLDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Primary URL unavailable on primary node",
)
def test_primary_url_unavailable_on_primary_node():
    """Test primary URL is empty string on primary node."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryURLDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Primary URL unavailable when no primary elected",
)
def test_primary_url_unavailable_when_no_primary():
    """Test primary URL is None when no primary elected."""
    pass


# ===========================================================================
# Scenarios - Mount Path Validation
# ===========================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Mount path must be absolute",
)
def test_mount_path_must_be_absolute():
    """Test mount path validation requires absolute path."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Mount path validated at settings creation",
)
def test_mount_path_validated_at_creation():
    """Test mount path validated when settings created."""
    pass


# ===========================================================================
# Scenarios - Caching Behavior
# ===========================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.CachedPrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Primary status not cached by default",
)
def test_primary_status_not_cached_by_default():
    """Test primary status not cached when TTL is 0."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.CachedPrimaryDetector")
@scenario(
    "../../features/core/litefs_process.feature",
    "Primary status can be cached with TTL",
)
def test_primary_status_cached_with_ttl():
    """Test primary status cached when TTL > 0."""
    pass


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def context() -> dict:
    """Shared context for passing state between steps."""
    return {}


# ===========================================================================
# Given Steps - Mount Detection
# ===========================================================================


@given(parsers.parse('LiteFS is configured with mount_path "{path}"'))
def given_configured_mount_path(context: dict, path: str, tmp_path: Path):
    """Configure LiteFS with a specific mount path."""
    # Use tmp_path as base for the configured path
    context["configured_path"] = path
    context["actual_mount_path"] = tmp_path / path.lstrip("/")


@given(parsers.parse('the directory "{path}" exists'))
def directory_exists(context: dict, path: str):
    """Ensure the configured directory exists."""
    context["actual_mount_path"].mkdir(parents=True, exist_ok=True)


@given(parsers.parse('the directory "{path}" does not exist'))
def directory_does_not_exist(context: dict, path: str):
    """Ensure the configured directory does not exist."""
    # Don't create the directory - it doesn't exist by default
    assert not context["actual_mount_path"].exists()


# ===========================================================================
# Given Steps - Primary Detection
# ===========================================================================


@given(parsers.parse('LiteFS mount path "{path}" exists'))
def mount_path_exists(context: dict, path: str, tmp_path: Path):
    """Set up an existing mount path."""
    context["configured_path"] = path
    context["actual_mount_path"] = tmp_path / path.lstrip("/")
    context["actual_mount_path"].mkdir(parents=True, exist_ok=True)


@given(parsers.parse('the file "{path}" exists'))
def file_exists(context: dict, path: str):
    """Create the specified file in the mount path."""
    # Extract filename from path (e.g., "/mnt/litefs/.primary" -> ".primary")
    filename = Path(path).name
    primary_file = context["actual_mount_path"] / filename
    primary_file.write_text("node-1")


@given(parsers.parse('the file "{path}" does not exist'))
def file_does_not_exist(context: dict, path: str):
    """Ensure the specified file does not exist."""
    filename = Path(path).name
    primary_file = context["actual_mount_path"] / filename
    assert not primary_file.exists()


@given(parsers.parse('the file "{path}" contains "{content}"'))
def file_contains_content(context: dict, path: str, content: str):
    """Create file with specific content."""
    filename = Path(path).name
    primary_file = context["actual_mount_path"] / filename
    primary_file.write_text(content)


@given(parsers.parse('the file "{path}" exists but is empty'))
def file_exists_but_empty(context: dict, path: str):
    """Create an empty file."""
    filename = Path(path).name
    primary_file = context["actual_mount_path"] / filename
    primary_file.write_text("")


# ===========================================================================
# Given Steps - Validation
# ===========================================================================


@given(parsers.parse('LiteFS settings with mount_path "{path}"'))
def settings_with_mount_path(context: dict, path: str):
    """Prepare to create settings with specified mount path."""
    context["mount_path_to_validate"] = path


# ===========================================================================
# Given Steps - Caching
# ===========================================================================


@given(parsers.parse("primary status caching is enabled with TTL {ttl:d} seconds"))
def caching_enabled_with_ttl(context: dict, ttl: int):
    """Enable caching with specified TTL."""
    context["cache_ttl"] = float(ttl)


# ===========================================================================
# When Steps
# ===========================================================================


@when("I check if LiteFS is running")
def check_if_litefs_running(context: dict):
    """Check if LiteFS is running using is_litefs_running()."""
    detector = PrimaryDetector(mount_path=str(context["actual_mount_path"]))
    context["result"] = detector.is_litefs_running()
    context["error"] = None


@when("I attempt to check primary status")
def attempt_primary_status(context: dict):
    """Attempt to check primary status (may raise error)."""
    detector = PrimaryDetector(mount_path=str(context["actual_mount_path"]))
    try:
        context["result"] = detector.is_primary()
        context["error"] = None
    except LiteFSNotRunningError as e:
        context["result"] = None
        context["error"] = e


@when("I check if this node is primary")
def check_if_primary(context: dict):
    """Check if this node is primary."""
    detector = PrimaryDetector(mount_path=str(context["actual_mount_path"]))
    try:
        context["result"] = detector.is_primary()
        context["error"] = None
    except LiteFSNotRunningError as e:
        context["result"] = None
        context["error"] = e


@when("I check if this node is primary multiple times")
def check_primary_multiple_times(context: dict):
    """Check primary status multiple times to verify idempotency."""
    detector = PrimaryDetector(mount_path=str(context["actual_mount_path"]))
    results = []
    for _ in range(3):
        results.append(detector.is_primary())
    context["results"] = results
    context["error"] = None


@when("I get the primary URL")
def get_primary_url(context: dict):
    """Get the primary URL."""
    detector = PrimaryURLDetector(mount_path=str(context["actual_mount_path"]))
    context["result"] = detector.get_primary_url()
    context["error"] = None


@when("the settings are validated")
def settings_are_validated(context: dict):
    """Attempt to create settings with the configured mount path."""
    try:
        LiteFSSettings(
            mount_path=context["mount_path_to_validate"],
            data_path="/data/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1d",
        )
        context["error"] = None
        context["settings_created"] = True
    except LiteFSConfigError as e:
        context["error"] = e
        context["settings_created"] = False


@when("the settings are created")
def settings_are_created(context: dict):
    """Create settings with the configured mount path."""
    try:
        settings = LiteFSSettings(
            mount_path=context["mount_path_to_validate"],
            data_path="/data/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1d",
        )
        context["settings"] = settings
        context["error"] = None
        context["settings_created"] = True
    except LiteFSConfigError as e:
        context["error"] = e
        context["settings_created"] = False


@when('the ".primary" file is removed')
def primary_file_is_removed(context: dict):
    """Remove the .primary file."""
    primary_file = context["actual_mount_path"] / ".primary"
    if primary_file.exists():
        primary_file.unlink()


@when("I check if this node is primary again")
def check_primary_again(context: dict):
    """Check primary status again after modification."""
    cache_ttl = context.get("cache_ttl", 0)
    wrapped = PrimaryDetector(mount_path=str(context["actual_mount_path"]))

    if cache_ttl > 0:
        detector = context.get("cached_detector")
        if detector is None:
            detector = CachedPrimaryDetector(wrapped, ttl_seconds=cache_ttl)
            context["cached_detector"] = detector
    else:
        detector = wrapped

    context["second_result"] = detector.is_primary()


@when('the ".primary" file is removed within TTL')
def primary_file_removed_within_ttl(context: dict):
    """Remove the .primary file while still within TTL."""
    primary_file = context["actual_mount_path"] / ".primary"
    if primary_file.exists():
        primary_file.unlink()


# Special step for caching test - need to capture first result with cached detector
@when("I check if this node is primary", target_fixture="result_override")
def check_primary_cached(context: dict):
    """Check primary status with optional caching."""
    cache_ttl = context.get("cache_ttl", 0)
    wrapped = PrimaryDetector(mount_path=str(context["actual_mount_path"]))

    if cache_ttl > 0:
        detector = CachedPrimaryDetector(wrapped, ttl_seconds=cache_ttl)
        context["cached_detector"] = detector
    else:
        detector = wrapped

    context["result"] = detector.is_primary()
    context["error"] = None


# ===========================================================================
# Then Steps
# ===========================================================================


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
def litefs_not_running_error_raised(context: dict):
    """Assert LiteFSNotRunningError was raised."""
    assert context["error"] is not None, "Expected LiteFSNotRunningError but no error"
    assert isinstance(context["error"], LiteFSNotRunningError)


@then(parsers.parse('the error message should contain "{text}"'))
def error_message_contains(context: dict, text: str):
    """Assert error message contains expected text."""
    assert context["error"] is not None
    assert text in str(context["error"]), f"Expected '{text}' in '{context['error']}'"


@then("all results should be true")
def all_results_true(context: dict):
    """Assert all results are True."""
    assert all(r is True for r in context["results"])


@then("no side effects should occur")
def no_side_effects(context: dict):
    """Assert no side effects (file still exists)."""
    primary_file = context["actual_mount_path"] / ".primary"
    assert primary_file.exists()


@then(parsers.parse('the result should be "{expected}"'))
def result_should_be_string(context: dict, expected: str):
    """Assert result matches expected string."""
    assert context["result"] == expected


@then("the result should indicate this node is primary")
def result_indicates_primary(context: dict):
    """Assert result is empty string (indicating this node is primary)."""
    assert context["result"] == ""


@then("the result should be None")
def result_is_none(context: dict):
    """Assert result is None."""
    assert context["result"] is None


@then("no error should be raised")
def no_error_raised(context: dict):
    """Assert no error was raised."""
    assert context["error"] is None


@then("a LiteFSConfigError should be raised")
def config_error_raised(context: dict):
    """Assert LiteFSConfigError was raised."""
    assert context["error"] is not None, "Expected LiteFSConfigError but no error"
    assert isinstance(context["error"], LiteFSConfigError)


@then("validation should pass")
def validation_passes(context: dict):
    """Assert validation passed."""
    assert context["settings_created"] is True
    assert context["error"] is None


@then("the mount_path should be stored as-is")
def mount_path_stored_as_is(context: dict):
    """Assert mount_path is stored without modification."""
    assert context["settings"].mount_path == context["mount_path_to_validate"]


@then("the second result should be false")
def second_result_is_false(context: dict):
    """Assert second result is False."""
    assert context["second_result"] is False


@then("the second result should still be true")
def second_result_still_true(context: dict):
    """Assert second result is still True (due to caching)."""
    assert context["second_result"] is True
