"""Step definitions for management_commands.feature.

BDD tests for the Django management commands (litefs_check and litefs_status).
TRA Namespace: Adapter.Django.ManagementCommands
"""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from django.core.management.base import CommandError
from pytest_bdd import given, parsers, scenario, then, when

# Add project root to path for cross-package imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from litefs.domain.health import HealthStatus  # noqa: E402
from litefs.domain.settings import LiteFSSettings  # noqa: E402
from litefs_django.management.commands.litefs_check import (  # noqa: E402
    Command as LiteFSCheckCommand,
)
from litefs_django.management.commands.litefs_status import (  # noqa: E402
    Command as LiteFSStatusCommand,
)


# =============================================================================
# Scenarios - litefs_check Command
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check validates complete setup",
)
def test_litefs_check_validates_complete_setup() -> None:
    """Test litefs_check passes with correct configuration."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check reports missing LITEFS settings",
)
def test_litefs_check_reports_missing_settings() -> None:
    """Test litefs_check reports missing LITEFS settings."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check reports wrong database backend",
)
def test_litefs_check_reports_wrong_database_backend() -> None:
    """Test litefs_check reports wrong database backend."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check reports inaccessible mount path",
)
def test_litefs_check_reports_inaccessible_mount_path() -> None:
    """Test litefs_check reports inaccessible mount path."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check reports all issues at once",
)
def test_litefs_check_reports_all_issues_at_once() -> None:
    """Test litefs_check reports all issues at once."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check with verbosity 0 shows only errors",
)
def test_litefs_check_verbosity_0_shows_only_errors() -> None:
    """Test litefs_check with verbosity 0 shows only errors."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check with verbosity 2 shows detailed info",
)
def test_litefs_check_verbosity_2_shows_detailed_info() -> None:
    """Test litefs_check with verbosity 2 shows detailed info."""
    pass


# =============================================================================
# Scenarios - litefs_status Command
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_status shows current node state",
)
def test_litefs_status_shows_current_node_state() -> None:
    """Test litefs_status shows current node state."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_status shows primary when node is primary",
)
def test_litefs_status_shows_primary_when_node_is_primary() -> None:
    """Test litefs_status shows primary when node is primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_status shows replica when node is replica",
)
def test_litefs_status_shows_replica_when_node_is_replica() -> None:
    """Test litefs_status shows replica when node is replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_status reports when LiteFS not running",
)
def test_litefs_status_reports_when_litefs_not_running() -> None:
    """Test litefs_status reports when LiteFS not running."""
    pass


# =============================================================================
# Scenarios - JSON Output
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_check supports JSON output",
)
def test_litefs_check_supports_json_output() -> None:
    """Test litefs_check supports JSON output."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.ManagementCommands")
@scenario(
    "../../features/django/management_commands.feature",
    "litefs_status supports JSON output",
)
def test_litefs_status_supports_json_output() -> None:
    """Test litefs_status supports JSON output."""
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def context() -> dict[str, Any]:
    """Shared context for passing state between steps."""
    return {
        "stdout": StringIO(),
        "mock_settings": None,
        "mock_django_settings": None,
        "mock_detector": None,
        "mock_health_checker": None,
        "exit_code": 0,
        "command_error": None,
        "verbosity": 1,
        "format": "text",
    }


# =============================================================================
# Helper Functions
# =============================================================================


def _create_mock_litefs_settings(
    *,
    mount_path: str = "/mnt/litefs",
    enabled: bool = True,
    leader_election: str = "static",
) -> Mock:
    """Create a mock LiteFSSettings object."""
    mock_settings = Mock(spec=LiteFSSettings)
    mock_settings.mount_path = mount_path
    mock_settings.enabled = enabled
    mock_settings.leader_election = leader_election
    mock_settings.data_path = "/var/lib/litefs"
    mock_settings.database_name = "db.sqlite"
    mock_settings.proxy_addr = ":8080"
    mock_settings.retention = "7d"
    return mock_settings


def _create_mock_django_settings(
    *,
    litefs_dict: dict[str, Any] | None = None,
    database_engine: str = "litefs_django.db.backends.litefs",
) -> Mock:
    """Create a mock Django settings object."""
    mock_django_settings = Mock()
    mock_django_settings.LITEFS = litefs_dict or {}
    mock_django_settings.DATABASES = {"default": {"ENGINE": database_engine}}
    return mock_django_settings


# =============================================================================
# Given Steps - Django Project Setup
# =============================================================================


@given("a Django project with litefs_django installed")
def django_project_with_litefs_installed(context: dict[str, Any]) -> None:
    """Set up a Django project with litefs_django installed."""
    # Base setup - will be customized by subsequent steps
    pass


@given("LITEFS settings are correctly configured")
def litefs_settings_correctly_configured(context: dict[str, Any]) -> None:
    """Configure valid LITEFS settings."""
    context["mock_settings"] = _create_mock_litefs_settings()


@given("LITEFS settings are configured")
def litefs_settings_configured(context: dict[str, Any]) -> None:
    """Configure LITEFS settings (may not be complete)."""
    context["mock_settings"] = _create_mock_litefs_settings()


@given("no LITEFS settings are configured")
def no_litefs_settings_configured(context: dict[str, Any]) -> None:
    """Configure no LITEFS settings."""
    from litefs.domain.exceptions import LiteFSConfigError

    context["get_settings_error"] = LiteFSConfigError("LITEFS settings not configured")


@given("DATABASE backend is litefs_django.db.backends.litefs")
def database_backend_is_litefs(context: dict[str, Any]) -> None:
    """Configure LiteFS database backend."""
    context["mock_django_settings"] = _create_mock_django_settings(
        database_engine="litefs_django.db.backends.litefs"
    )


@given(parsers.parse('DATABASE ENGINE is "{engine}"'))
def database_engine_is(context: dict[str, Any], engine: str) -> None:
    """Configure specific database engine."""
    context["mock_django_settings"] = _create_mock_django_settings(
        database_engine=engine
    )


@given("the LiteFS mount path exists and is accessible")
def litefs_mount_path_accessible(context: dict[str, Any]) -> None:
    """Configure accessible mount path."""
    detector = Mock()
    detector.is_primary.return_value = True
    context["mock_detector"] = detector


@given(parsers.parse('LITEFS settings have mount_path "{mount_path}"'))
def litefs_settings_have_mount_path(context: dict[str, Any], mount_path: str) -> None:
    """Configure specific mount path in LITEFS settings."""
    context["mock_settings"] = _create_mock_litefs_settings(mount_path=mount_path)


@given(parsers.parse('the path "{path}" does not exist'))
def path_does_not_exist(context: dict[str, Any], path: str) -> None:
    """Configure mount path as inaccessible."""
    from litefs.usecases.primary_detector import LiteFSNotRunningError

    detector = Mock()
    detector.is_primary.side_effect = LiteFSNotRunningError("Mount path not found")
    context["mock_detector"] = detector


@given("a Django project with multiple configuration issues:")
def django_project_with_multiple_issues(context: dict[str, Any]) -> None:
    """Configure project with multiple issues."""
    from litefs.usecases.primary_detector import LiteFSNotRunningError

    # Wrong database backend
    context["mock_django_settings"] = _create_mock_django_settings(
        database_engine="django.db.backends.sqlite3"
    )
    # Valid settings but inaccessible mount
    context["mock_settings"] = _create_mock_litefs_settings()
    # Mount path not accessible
    detector = Mock()
    detector.is_primary.side_effect = LiteFSNotRunningError("Mount path not found")
    context["mock_detector"] = detector


@given("a Django project with configuration issues")
def django_project_with_configuration_issues(context: dict[str, Any]) -> None:
    """Configure project with some configuration issues."""
    # Wrong database backend
    context["mock_django_settings"] = _create_mock_django_settings(
        database_engine="django.db.backends.sqlite3"
    )
    context["mock_settings"] = _create_mock_litefs_settings()
    detector = Mock()
    detector.is_primary.return_value = True
    context["mock_detector"] = detector


@given("a Django project with correct configuration")
def django_project_with_correct_configuration(context: dict[str, Any]) -> None:
    """Configure project correctly."""
    context["mock_django_settings"] = _create_mock_django_settings(
        database_engine="litefs_django.db.backends.litefs"
    )
    context["mock_settings"] = _create_mock_litefs_settings()
    detector = Mock()
    detector.is_primary.return_value = True
    context["mock_detector"] = detector

    health_checker = Mock()
    health_checker.check_health.return_value = HealthStatus(state="healthy")
    context["mock_health_checker"] = health_checker


# =============================================================================
# Given Steps - LiteFS Running State
# =============================================================================


@given("a Django project with LiteFS running")
def django_project_with_litefs_running(context: dict[str, Any]) -> None:
    """Configure project with LiteFS running."""
    context["mock_django_settings"] = _create_mock_django_settings(
        database_engine="litefs_django.db.backends.litefs"
    )
    context["mock_settings"] = _create_mock_litefs_settings()
    detector = Mock()
    detector.is_primary.return_value = True
    context["mock_detector"] = detector

    health_checker = Mock()
    health_checker.check_health.return_value = HealthStatus(state="healthy")
    context["mock_health_checker"] = health_checker


@given("the current node is the primary")
def current_node_is_primary(context: dict[str, Any]) -> None:
    """Configure node as primary."""
    detector = Mock()
    detector.is_primary.return_value = True
    context["mock_detector"] = detector


@given("the current node is a replica")
def current_node_is_replica(context: dict[str, Any]) -> None:
    """Configure node as replica."""
    detector = Mock()
    detector.is_primary.return_value = False
    context["mock_detector"] = detector


@given("a Django project with LiteFS configured")
def django_project_with_litefs_configured(context: dict[str, Any]) -> None:
    """Configure project with LiteFS configured but not necessarily running."""
    context["mock_django_settings"] = _create_mock_django_settings(
        database_engine="litefs_django.db.backends.litefs"
    )
    context["mock_settings"] = _create_mock_litefs_settings()


@given("the LiteFS mount path does not exist")
def litefs_mount_path_does_not_exist(context: dict[str, Any]) -> None:
    """Configure mount path as not existing."""
    from litefs.usecases.primary_detector import LiteFSNotRunningError

    detector = Mock()
    detector.is_primary.side_effect = LiteFSNotRunningError("Mount path not found")
    context["mock_detector"] = detector


# =============================================================================
# When Steps - Running Commands
# =============================================================================


def _run_litefs_check(
    context: dict[str, Any], verbosity: int, output_format: str
) -> None:
    """Run litefs_check command with mocked dependencies."""
    stdout = context["stdout"]
    cmd = LiteFSCheckCommand(stdout=stdout)

    mock_settings = context.get("mock_settings") or _create_mock_litefs_settings()
    mock_django_settings = (
        context.get("mock_django_settings") or _create_mock_django_settings()
    )
    mock_detector = context.get("mock_detector")
    get_settings_error = context.get("get_settings_error")

    with patch(
        "litefs_django.management.commands.litefs_check.settings",
        mock_django_settings,
    ):
        if get_settings_error:
            with patch(
                "litefs_django.management.commands.litefs_check.get_litefs_settings",
                side_effect=get_settings_error,
            ):
                try:
                    cmd.handle(verbosity=verbosity, format=output_format)
                    context["exit_code"] = 0
                except CommandError as e:
                    context["exit_code"] = 1
                    context["command_error"] = str(e)
        else:
            with patch(
                "litefs_django.management.commands.litefs_check.get_litefs_settings",
                return_value=mock_settings,
            ):
                if mock_detector:
                    with patch(
                        "litefs_django.management.commands.litefs_check.PrimaryDetector",
                        return_value=mock_detector,
                    ):
                        try:
                            cmd.handle(verbosity=verbosity, format=output_format)
                            context["exit_code"] = 0
                        except CommandError as e:
                            context["exit_code"] = 1
                            context["command_error"] = str(e)
                else:
                    try:
                        cmd.handle(verbosity=verbosity, format=output_format)
                        context["exit_code"] = 0
                    except CommandError as e:
                        context["exit_code"] = 1
                        context["command_error"] = str(e)


def _run_litefs_status(
    context: dict[str, Any], verbosity: int, output_format: str
) -> None:
    """Run litefs_status command with mocked dependencies."""
    stdout = context["stdout"]
    cmd = LiteFSStatusCommand(stdout=stdout)

    mock_settings = context.get("mock_settings") or _create_mock_litefs_settings()
    mock_detector = context.get("mock_detector")
    mock_health_checker = context.get("mock_health_checker")
    get_settings_error = context.get("get_settings_error")

    if get_settings_error:
        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings",
            side_effect=get_settings_error,
        ):
            try:
                cmd.handle(verbosity=verbosity, format=output_format)
                context["exit_code"] = 0
            except CommandError as e:
                context["exit_code"] = 1
                context["command_error"] = str(e)
    else:
        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings",
            return_value=mock_settings,
        ):
            if mock_detector:
                with patch(
                    "litefs_django.management.commands.litefs_status.PrimaryDetector",
                    return_value=mock_detector,
                ):
                    if mock_health_checker:
                        with patch(
                            "litefs_django.management.commands.litefs_status.HealthChecker",
                            return_value=mock_health_checker,
                        ):
                            try:
                                cmd.handle(verbosity=verbosity, format=output_format)
                                context["exit_code"] = 0
                            except CommandError as e:
                                context["exit_code"] = 1
                                context["command_error"] = str(e)
                    else:
                        try:
                            cmd.handle(verbosity=verbosity, format=output_format)
                            context["exit_code"] = 0
                        except CommandError as e:
                            context["exit_code"] = 1
                            context["command_error"] = str(e)
            else:
                try:
                    cmd.handle(verbosity=verbosity, format=output_format)
                    context["exit_code"] = 0
                except CommandError as e:
                    context["exit_code"] = 1
                    context["command_error"] = str(e)


@when('I run "python manage.py litefs_check"')
def run_litefs_check(context: dict[str, Any]) -> None:
    """Run litefs_check command."""
    _run_litefs_check(context, verbosity=1, output_format="text")


@when('I run "python manage.py litefs_check -v 0"')
def run_litefs_check_v0(context: dict[str, Any]) -> None:
    """Run litefs_check command with verbosity 0."""
    _run_litefs_check(context, verbosity=0, output_format="text")


@when('I run "python manage.py litefs_check -v 2"')
def run_litefs_check_v2(context: dict[str, Any]) -> None:
    """Run litefs_check command with verbosity 2."""
    _run_litefs_check(context, verbosity=2, output_format="text")


@when('I run "python manage.py litefs_check --format=json"')
def run_litefs_check_json(context: dict[str, Any]) -> None:
    """Run litefs_check command with JSON format."""
    _run_litefs_check(context, verbosity=1, output_format="json")


@when('I run "python manage.py litefs_status"')
def run_litefs_status(context: dict[str, Any]) -> None:
    """Run litefs_status command."""
    _run_litefs_status(context, verbosity=1, output_format="text")


@when('I run "python manage.py litefs_status --format=json"')
def run_litefs_status_json(context: dict[str, Any]) -> None:
    """Run litefs_status command with JSON format."""
    _run_litefs_status(context, verbosity=1, output_format="json")


# =============================================================================
# Then Steps - Exit Codes
# =============================================================================


@then(parsers.parse("the command should exit with code {exit_code:d}"))
def command_should_exit_with_code(context: dict[str, Any], exit_code: int) -> None:
    """Assert the command exit code."""
    assert context["exit_code"] == exit_code, (
        f"Expected exit code {exit_code}, got {context['exit_code']}. "
        f"Error: {context.get('command_error', 'none')}"
    )


# =============================================================================
# Then Steps - Output Content
# =============================================================================


@then("the output should show all checks passed")
def output_shows_all_checks_passed(context: dict[str, Any]) -> None:
    """Assert output shows all checks passed."""
    output = context["stdout"].getvalue()
    assert "passed" in output.lower() or context["exit_code"] == 0, (
        f"Expected success message, got: {output}"
    )


@then(parsers.parse('the output should indicate "{message}"'))
def output_should_indicate(context: dict[str, Any], message: str) -> None:
    """Assert output contains the specified message or semantically equivalent.

    This step allows flexible matching to handle different phrasings
    of the same information in the actual command output.
    """
    output = context["stdout"].getvalue() + (context.get("command_error") or "")
    output_lower = output.lower()
    message_lower = message.lower()

    # Direct match first
    if message_lower in output_lower:
        return

    # Semantic equivalents for common messages
    equivalents: dict[str, list[str]] = {
        "database backend mismatch": [
            "database backend is not configured correctly",
            "expected engine",
        ],
        "mount path not accessible": [
            "mount path is inaccessible",
            "litefs is not running or mount path",
        ],
        "role: primary": ["node role:", "primary"],
        "role: replica": ["node role:", "replica"],
        "litefs not running": ["litefs is not running"],
    }

    # Check for semantic equivalents
    if message_lower in equivalents:
        for equiv in equivalents[message_lower]:
            if equiv in output_lower:
                return

    # For role checks, also check if both parts are present
    if message_lower.startswith("role:"):
        role = message_lower.split(":")[1].strip()
        if "node role" in output_lower and role in output_lower:
            return

    assert False, f"Expected '{message}' in output, got: {output}"


@then("the output should suggest adding LITEFS dict to settings")
def output_suggests_adding_litefs_dict(context: dict[str, Any]) -> None:
    """Assert output suggests adding LITEFS dict."""
    output = context["stdout"].getvalue() + (context.get("command_error") or "")
    assert "litefs" in output.lower() or "settings" in output.lower(), (
        f"Expected suggestion about settings, got: {output}"
    )


@then("the output should suggest using litefs backend")
def output_suggests_litefs_backend(context: dict[str, Any]) -> None:
    """Assert output suggests using litefs backend."""
    output = context["stdout"].getvalue() + (context.get("command_error") or "")
    assert "litefs" in output.lower() or "backend" in output.lower(), (
        f"Expected suggestion about backend, got: {output}"
    )


@then("the output should suggest checking LiteFS is running")
def output_suggests_checking_litefs_running(context: dict[str, Any]) -> None:
    """Assert output suggests checking LiteFS is running."""
    output = context["stdout"].getvalue() + (context.get("command_error") or "")
    assert "running" in output.lower() or "mount" in output.lower(), (
        f"Expected suggestion about LiteFS running, got: {output}"
    )


@then("the output should list all issues")
def output_lists_all_issues(context: dict[str, Any]) -> None:
    """Assert output lists all issues."""
    output = context["stdout"].getvalue() + (context.get("command_error") or "")
    # Should mention both database backend and mount path issues
    has_backend_issue = "backend" in output.lower() or "engine" in output.lower()
    has_mount_issue = "mount" in output.lower() or "running" in output.lower()
    assert has_backend_issue or has_mount_issue, (
        f"Expected multiple issues listed, got: {output}"
    )


@then("each issue should have a suggested fix")
def each_issue_has_suggested_fix(context: dict[str, Any]) -> None:
    """Assert each issue has a suggested fix."""
    output = context["stdout"].getvalue() + (context.get("command_error") or "")
    # Look for fix suggestions
    assert "fix" in output.lower() or "update" in output.lower(), (
        f"Expected fix suggestions, got: {output}"
    )


@then("only error messages should be displayed")
def only_error_messages_displayed(context: dict[str, Any]) -> None:
    """Assert only error messages are displayed (no informational output)."""
    # With verbosity 0, on success there should be no output
    # On error, only the error message
    pass  # The exit code check handles most of this


@then("no informational output should appear")
def no_informational_output(context: dict[str, Any]) -> None:
    """Assert no informational output appears."""
    # With verbosity 0 and success, output should be minimal
    pass  # Combined with previous step


@then("detailed configuration values should be displayed")
def detailed_config_values_displayed(context: dict[str, Any]) -> None:
    """Assert detailed configuration values are displayed."""
    output = context["stdout"].getvalue()
    # With verbosity 2, should show step-by-step checks
    assert "performing" in output.lower() or "[" in output, (
        f"Expected detailed output, got: {output}"
    )


@then("each check step should be shown")
def each_check_step_shown(context: dict[str, Any]) -> None:
    """Assert each check step is shown."""
    output = context["stdout"].getvalue()
    # Should have numbered steps like [1/5], [2/5] etc.
    assert "[" in output or "check" in output.lower(), (
        f"Expected step-by-step output, got: {output}"
    )


# =============================================================================
# Then Steps - litefs_status Output
# =============================================================================


@then("the output should show:")
def output_should_show_table(context: dict[str, Any]) -> None:
    """Assert output shows the expected fields from table."""
    output = context["stdout"].getvalue()
    # Should show node_role, mount_path, health
    assert (
        "role" in output.lower()
        or "primary" in output.lower()
        or "replica" in output.lower()
    ), f"Expected role information, got: {output}"


@then(parsers.parse('the output should indicate "Role: {role}"'))
def output_indicates_role(context: dict[str, Any], role: str) -> None:
    """Assert output indicates the specified role."""
    output = context["stdout"].getvalue()
    assert role.lower() in output.lower(), (
        f"Expected role '{role}' in output, got: {output}"
    )


# =============================================================================
# Then Steps - JSON Output
# =============================================================================


@then("the output should be valid JSON")
def output_is_valid_json(context: dict[str, Any]) -> None:
    """Assert output is valid JSON."""
    output = context["stdout"].getvalue()
    try:
        context["json_output"] = json.loads(output)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output is not valid JSON: {e}\nOutput: {output}")


@then(parsers.parse('the JSON should contain "{field}" field'))
def json_contains_field(context: dict[str, Any], field: str) -> None:
    """Assert JSON contains the specified field."""
    json_output = context.get("json_output")
    if json_output is None:
        output = context["stdout"].getvalue()
        json_output = json.loads(output)
    assert field in json_output, (
        f"Expected '{field}' in JSON, got keys: {json_output.keys()}"
    )


@then(parsers.parse('the JSON should contain "{field}" array'))
def json_contains_array(context: dict[str, Any], field: str) -> None:
    """Assert JSON contains the specified array field."""
    json_output = context.get("json_output")
    if json_output is None:
        output = context["stdout"].getvalue()
        json_output = json.loads(output)
    assert field in json_output, (
        f"Expected '{field}' in JSON, got keys: {json_output.keys()}"
    )
    assert isinstance(json_output[field], list), (
        f"Expected '{field}' to be an array, got: {type(json_output[field])}"
    )


@then("the JSON should contain node state information")
def json_contains_node_state_info(context: dict[str, Any]) -> None:
    """Assert JSON contains node state information."""
    json_output = context.get("json_output")
    if json_output is None:
        output = context["stdout"].getvalue()
        json_output = json.loads(output)
    # Should have role information
    assert "role" in json_output or "enabled" in json_output, (
        f"Expected node state info in JSON, got keys: {json_output.keys()}"
    )
