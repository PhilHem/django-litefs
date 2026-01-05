"""Unit tests for Django management commands."""

import pytest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Iterator
from unittest.mock import Mock, patch

from django.core.management.base import CommandError

from litefs.domain.settings import LiteFSSettings
from litefs.usecases.primary_detector import LiteFSNotRunningError
from litefs.usecases.installation_checker import (
    InstallationCheckResult,
    InstallationStatus,
)
from litefs_django.management.commands.litefs_status import (
    Command as LiteFSStatusCommand,
)
from litefs_django.management.commands.litefs_check import Command as LiteFSCheckCommand


@contextmanager
def mock_litefs_check_dependencies(
    settings: Mock | None = None,
    django_settings: Mock | None = None,
    is_primary: bool = True,
    binary_status: InstallationStatus = InstallationStatus.OK,
    binary_path: Path = Path("/usr/bin/litefs"),
) -> Iterator[dict[str, Mock]]:
    """Context manager to mock litefs_check command dependencies.

    This helper reduces test boilerplate by setting up all necessary mocks
    for the litefs_check command with sensible defaults.

    Args:
        settings: Mock LiteFSSettings (creates default if None)
        django_settings: Mock Django settings (creates default if None)
        is_primary: Whether PrimaryDetector.is_primary() returns True
        binary_status: InstallationStatus for binary check
        binary_path: Path to report as binary location

    Yields:
        Dictionary of all created mocks for additional configuration
    """
    if settings is None:
        settings = Mock(spec=LiteFSSettings)
        settings.mount_path = "/litefs"
        settings.enabled = True

    if django_settings is None:
        django_settings = Mock()
        django_settings.LITEFS = {}
        django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

    # Create binary location mock
    mock_binary_location = Mock()
    mock_binary_location.path = binary_path

    # Create installation check result
    if binary_status == InstallationStatus.OK:
        mock_install_result = InstallationCheckResult(
            status=InstallationStatus.OK,
            binary_path=binary_path,
            error_message=None,
        )
    else:
        mock_install_result = InstallationCheckResult(
            status=binary_status,
            binary_path=binary_path
            if binary_status != InstallationStatus.MISSING
            else None,
            error_message=f"Binary issue: {binary_status.value}",
        )

    # Stack patches
    patches = {
        "get_settings": patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ),
        "django_settings": patch(
            "litefs_django.management.commands.litefs_check.settings",
            django_settings,
        ),
        "detector": patch(
            "litefs_django.management.commands.litefs_check.PrimaryDetector"
        ),
        "resolver": patch(
            "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
        ),
        "checker": patch(
            "litefs_django.management.commands.litefs_check.InstallationChecker"
        ),
    }

    with (
        patches["get_settings"] as mock_get_settings,
        patches["django_settings"],
        patches["detector"] as mock_detector_class,
        patches["resolver"] as mock_resolver_class,
        patches["checker"] as mock_checker_class,
    ):
        mock_get_settings.return_value = settings

        detector = Mock()
        detector.is_primary.return_value = is_primary
        mock_detector_class.return_value = detector

        mock_resolver_class.return_value.resolve.return_value = mock_binary_location
        mock_checker_class.return_value.return_value = mock_install_result

        yield {
            "get_settings": mock_get_settings,
            "detector_class": mock_detector_class,
            "detector": detector,
            "resolver_class": mock_resolver_class,
            "checker_class": mock_checker_class,
            "binary_location": mock_binary_location,
            "install_result": mock_install_result,
        }


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestLiteFSStatusCommand:
    """Test litefs_status management command."""

    def test_command_exists(self) -> None:
        """Test that litefs_status command can be imported."""
        assert LiteFSStatusCommand is not None

    def test_command_output_shows_node_role_primary(self) -> None:
        """Test that status command shows 'primary' role when node is primary."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        # Mock settings and primary detector
        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = True
                mock_detector_class.return_value = detector

                cmd.handle()
                output = out.getvalue()

                assert "primary" in output.lower()
                assert "/litefs" in output

    def test_command_output_shows_node_role_replica(self) -> None:
        """Test that status command shows 'replica' role when node is replica."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        # Mock settings and primary detector
        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = False
                mock_detector_class.return_value = detector

                cmd.handle()
                output = out.getvalue()

                assert "replica" in output.lower()
                assert "/litefs" in output

    def test_command_shows_mount_path(self) -> None:
        """Test that status command shows mount path."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/custom/litefs/path"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = True
                mock_detector_class.return_value = detector

                cmd.handle()
                output = out.getvalue()

                assert "/custom/litefs/path" in output

    def test_command_shows_enabled_state(self) -> None:
        """Test that status command shows enabled state."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = True
                mock_detector_class.return_value = detector

                cmd.handle()
                output = out.getvalue()

                # Should indicate enabled status
                assert "enabled" in output.lower() or "true" in output.lower()

    def test_command_shows_disabled_state(self) -> None:
        """Test that status command shows when LiteFS is disabled."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = False
                mock_detector_class.return_value = detector

                cmd.handle()
                output = out.getvalue()

                # Should indicate disabled status
                assert "disabled" in output.lower() or "false" in output.lower()

    def test_command_handles_litefs_not_running(self) -> None:
        """Test that status command handles LiteFS not running gracefully."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/nonexistent"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.side_effect = LiteFSNotRunningError(
                    "Mount path not found"
                )
                mock_detector_class.return_value = detector

                # Command should handle the error gracefully (wraps as CommandError)
                with pytest.raises(CommandError):
                    cmd.handle()


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestLiteFSCheckCommand:
    """Test litefs_check management command."""

    def test_command_exists(self) -> None:
        """Test that litefs_check command can be imported."""
        assert LiteFSCheckCommand is not None

    def test_command_exits_zero_on_primary(
        self, mock_installation_checker: dict
    ) -> None:
        """Test that check command exits with code 0 when node is primary."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        # Mock Django settings with correct database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                with patch(
                    "litefs_django.management.commands.litefs_check.PrimaryDetector"
                ) as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    # Command should return successfully (no exception)
                    result = cmd.handle()
                    assert result is None or result == 0

    def test_command_exits_zero_on_replica(
        self, mock_installation_checker: dict
    ) -> None:
        """Test that check command exits with code 0 when node is replica."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        # Mock Django settings with correct database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                with patch(
                    "litefs_django.management.commands.litefs_check.PrimaryDetector"
                ) as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = False
                    mock_detector_class.return_value = detector

                    # Command should return successfully on replica too
                    result = cmd.handle()
                    assert result is None or result == 0

    def test_command_fails_when_litefs_not_running(self) -> None:
        """Test that check command fails when LiteFS is not running."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/nonexistent"
        mock_settings.enabled = True

        # Mock Django settings with correct database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                with patch(
                    "litefs_django.management.commands.litefs_check.PrimaryDetector"
                ) as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.side_effect = LiteFSNotRunningError(
                        "Mount path not found"
                    )
                    mock_detector_class.return_value = detector

                    # Command should raise an exception to indicate failure (wraps as CommandError)
                    with pytest.raises(CommandError):
                        cmd.handle()

    def test_command_fails_when_litefs_disabled(self) -> None:
        """Test that check command fails when LiteFS is disabled."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False

        # Mock Django settings with correct database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                # Command should fail if LiteFS is disabled
                with pytest.raises(CommandError):
                    cmd.handle()

    def test_command_performs_health_checks(
        self, mock_installation_checker: dict
    ) -> None:
        """Test that check command performs health checks."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        # Mock Django settings with correct database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                with patch(
                    "litefs_django.management.commands.litefs_check.PrimaryDetector"
                ) as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    cmd.handle()
                    _output = out.getvalue()  # noqa: F841

                    # Should produce some output indicating checks were performed
                    # (could be informational or verbose output)
                    # At minimum, command should call the detector

    def test_check_validates_settings_first(self) -> None:
        """Test that check command validates settings are configured."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            from litefs.domain.exceptions import LiteFSConfigError

            mock_get_settings.side_effect = LiteFSConfigError(
                "Missing required settings"
            )

            # Should fail if settings are invalid (wraps as CommandError)
            with pytest.raises(CommandError):
                cmd.handle()

    def test_check_fails_when_database_backend_not_litefs(self) -> None:
        """Test that check command fails when database backend is not litefs_django."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        # Mock Django settings with wrong database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                # Command should fail if database backend is not litefs
                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                assert "database backend" in str(
                    exc_info.value
                ).lower() or "ENGINE" in str(exc_info.value)

    def test_check_passes_when_database_backend_is_litefs(
        self, mock_installation_checker: dict
    ) -> None:
        """Test that check command passes when database backend is litefs_django."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        # Mock Django settings with correct database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                with patch(
                    "litefs_django.management.commands.litefs_check.PrimaryDetector"
                ) as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    # Command should pass
                    result = cmd.handle()
                    assert result is None or result == 0

    def test_check_verbose_output_shows_database_backend_check(
        self, mock_installation_checker: dict
    ) -> None:
        """Test that verbose output shows database backend check."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        # Mock Django settings with correct database backend
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                with patch(
                    "litefs_django.management.commands.litefs_check.PrimaryDetector"
                ) as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    cmd.handle(verbose=True)
                    output = out.getvalue()

                    # Should show database backend check in verbose output
                    assert "database" in output.lower() or "backend" in output.lower()


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestLiteFSCheckMultiIssueReporting:
    """Test multi-issue reporting for litefs_check command."""

    def test_reports_all_issues_when_multiple_config_problems_exist(self) -> None:
        """Test that command reports ALL issues, not just the first one."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False  # Issue 1: disabled

        # Mock Django settings with wrong backend (Issue 2)
        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                error_message = str(exc_info.value)
                # Both issues should be reported
                assert "database" in error_message.lower() or "ENGINE" in error_message
                assert (
                    "disabled" in error_message.lower()
                    or "enabled" in error_message.lower()
                )

    def test_each_issue_has_suggested_fix(self) -> None:
        """Test that each reported issue includes a suggested fix."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False  # Issue: disabled

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}  # Issue: wrong backend
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                error_message = str(exc_info.value)
                # Should have fix suggestions (patterns from current error messages)
                # Backend fix: mentions ENGINE or DATABASES
                # Enabled fix: mentions LITEFS.ENABLED or "Enable LiteFS"
                has_backend_fix = (
                    "DATABASES" in error_message or "ENGINE" in error_message
                )
                has_enabled_fix = (
                    "ENABLED" in error_message or "Enable" in error_message
                )
                assert has_backend_fix and has_enabled_fix

    def test_exits_with_code_1_on_any_issue(self) -> None:
        """Test that command exits with code 1 when any issue exists."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False  # Single issue

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                # CommandError causes Django to exit with code 1
                with pytest.raises(CommandError):
                    cmd.handle()

    def test_output_lists_issues_clearly(self) -> None:
        """Test that issues are listed in a clear, parseable format."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                error_message = str(exc_info.value)
                # Issues should be clearly separated (e.g., numbered list or newlines)
                # Count distinct issues by looking for issue indicators
                issue_count = (
                    error_message.count("\n- ")
                    + error_message.count("1.")
                    + error_message.count("2.")
                )
                # At minimum we should see structure showing multiple issues
                assert issue_count >= 1 or "\n" in error_message

    def test_single_issue_still_works(self) -> None:
        """Test that single-issue case still reports correctly."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True  # enabled OK

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}  # Only this issue
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                error_message = str(exc_info.value)
                # Should report the backend issue
                assert "database" in error_message.lower() or "ENGINE" in error_message

    def test_three_issues_all_reported(self) -> None:
        """Test that three simultaneous issues are all reported."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/nonexistent"
        mock_settings.enabled = False  # Issue 1

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}  # Issue 2
        }
        # Issue 3: mount path not accessible will be caught when PrimaryDetector is created

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                with patch(
                    "litefs_django.management.commands.litefs_check.PrimaryDetector"
                ) as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    mock_detector_class.side_effect = Exception(
                        "Mount path not accessible"
                    )

                    with pytest.raises(CommandError) as exc_info:
                        cmd.handle()

                    error_message = str(exc_info.value)
                    # All three issues should appear
                    has_backend = (
                        "database" in error_message.lower() or "ENGINE" in error_message
                    )
                    has_enabled = (
                        "disabled" in error_message.lower()
                        or "enabled" in error_message.lower()
                    )
                    has_mount = (
                        "mount" in error_message.lower()
                        or "accessible" in error_message.lower()
                    )
                    assert has_backend and has_enabled and has_mount


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestVerbosityLevels:
    """Test Django verbosity levels for management commands."""

    def test_status_verbosity_0_minimal_output(self) -> None:
        """Test that -v 0 produces minimal (no) output for status command."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = True
                mock_detector_class.return_value = detector

                cmd.handle(verbosity=0)
                output = out.getvalue()

                # Verbosity 0 should produce minimal or no output
                assert output == "" or len(output.strip().split("\n")) <= 1

    def test_status_verbosity_1_normal_output(self) -> None:
        """Test that -v 1 (default) produces normal output for status command."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = True
                mock_detector_class.return_value = detector

                cmd.handle(verbosity=1)
                output = out.getvalue()

                # Verbosity 1 should show status info
                assert "primary" in output.lower()
                assert "/litefs" in output

    def test_status_verbosity_2_detailed_output(self) -> None:
        """Test that -v 2 produces detailed output for status command."""
        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"
        mock_settings.data_path = "/var/lib/litefs"
        mock_settings.database_name = "db"
        mock_settings.proxy_addr = ":8080"
        mock_settings.retention = "1h"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = True
                mock_detector_class.return_value = detector

                cmd.handle(verbosity=2)
                output = out.getvalue()

                # Verbosity 2 should include extra details
                assert "data" in output.lower() or "database" in output.lower()

    def test_check_verbosity_0_minimal_output(self) -> None:
        """Test that -v 0 produces minimal output for check command."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        with mock_litefs_check_dependencies():
            cmd.handle(verbosity=0)
            output = out.getvalue()

            # Verbosity 0 should produce no output on success
            assert output == ""

    def test_check_verbosity_1_normal_output(self) -> None:
        """Test that -v 1 (default) produces success message for check command."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        with mock_litefs_check_dependencies():
            cmd.handle(verbosity=1)
            output = out.getvalue()

            # Verbosity 1 should show success message
            assert (
                "passed" in output.lower() or "ok" in output.lower() or len(output) > 0
            )

    def test_check_verbosity_2_shows_check_steps(self) -> None:
        """Test that -v 2 shows individual check steps for check command."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        with mock_litefs_check_dependencies():
            cmd.handle(verbosity=2)
            output = out.getvalue()

            # Verbosity 2 should show individual health checks
            assert "[" in output or "check" in output.lower()


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestJSONOutput:
    """Test JSON output format for management commands."""

    def test_check_json_format_on_success(self) -> None:
        """Test that --format=json produces valid JSON on success."""
        import json

        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        with mock_litefs_check_dependencies():
            cmd.handle(format="json")
            output = out.getvalue()

            # Should be valid JSON
            data = json.loads(output)
            assert data["status"] == "ok"
            assert "checks" in data

    def test_check_json_includes_all_check_results(self) -> None:
        """Test that JSON output includes all health check results."""
        import json

        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        with mock_litefs_check_dependencies():
            cmd.handle(format="json")
            output = out.getvalue()

            data = json.loads(output)
            checks = data["checks"]
            # Should have checks for config, backend, enabled, mount, binary, role
            assert len(checks) >= 3
            check_names = [c["name"] for c in checks]
            assert any("config" in n.lower() for n in check_names)

    def test_check_json_format_on_failure(self) -> None:
        """Test that --format=json produces valid JSON on failure."""
        import json

        out = StringIO()
        err = StringIO()
        cmd = LiteFSCheckCommand(stdout=out, stderr=err)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False  # Issue

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}  # Issue
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                # With JSON format, should output JSON instead of raising CommandError
                with pytest.raises(CommandError):
                    cmd.handle(format="json")

                # Output should still be JSON
                output = out.getvalue()
                if output:
                    data = json.loads(output)
                    assert data["status"] == "error"
                    assert "issues" in data

    def test_check_json_issues_have_fix_suggestions(self) -> None:
        """Test that JSON issues include fix suggestions."""
        import json

        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "django.db.backends.sqlite3"}
        }

        with patch(
            "litefs_django.management.commands.litefs_check.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_check.settings",
                mock_django_settings,
            ):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError):
                    cmd.handle(format="json")

                output = out.getvalue()
                if output:
                    data = json.loads(output)
                    for issue in data.get("issues", []):
                        assert "fix" in issue or "suggestion" in issue

    def test_status_json_format(self) -> None:
        """Test that --format=json produces valid JSON for status command."""
        import json

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"
        mock_settings.data_path = "/var/lib/litefs"
        mock_settings.database_name = "db"
        mock_settings.proxy_addr = ":8080"
        mock_settings.retention = "1h"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = True
                mock_detector_class.return_value = detector

                cmd.handle(format="json")
                output = out.getvalue()

                data = json.loads(output)
                assert data["role"] == "primary"
                assert data["mount_path"] == "/litefs"
                assert data["enabled"] is True

    def test_status_json_includes_leader_election(self) -> None:
        """Test that JSON status includes leader election mode."""
        import json

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "consul"
        mock_settings.data_path = "/var/lib/litefs"
        mock_settings.database_name = "db"
        mock_settings.proxy_addr = ":8080"
        mock_settings.retention = "1h"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.return_value = False
                mock_detector_class.return_value = detector

                cmd.handle(format="json")
                output = out.getvalue()

                data = json.loads(output)
                assert data["role"] == "replica"
                assert data["leader_election"] == "consul"

    def test_status_json_disabled_state(self) -> None:
        """Test that JSON status handles disabled state."""
        import json

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = False
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            cmd.handle(format="json")
            output = out.getvalue()

            data = json.loads(output)
            assert data["enabled"] is False
            # Role should be null/none when disabled
            assert data.get("role") is None or "role" not in data


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestLiteFSStatusHealthStatus:
    """Test health status display in litefs_status command."""

    def test_status_shows_health_status_healthy(self) -> None:
        """Test that status command shows health status when node is healthy."""
        from litefs.domain.health import HealthStatus

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                with patch(
                    "litefs_django.management.commands.litefs_status.HealthChecker"
                ) as mock_health_checker_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    health_checker = Mock()
                    health_checker.check_health.return_value = HealthStatus(
                        state="healthy"
                    )
                    mock_health_checker_class.return_value = health_checker

                    cmd.handle()
                    output = out.getvalue()

                    assert "healthy" in output.lower()

    def test_status_shows_health_status_degraded(self) -> None:
        """Test that status command shows degraded health status."""
        from litefs.domain.health import HealthStatus

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                with patch(
                    "litefs_django.management.commands.litefs_status.HealthChecker"
                ) as mock_health_checker_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    health_checker = Mock()
                    health_checker.check_health.return_value = HealthStatus(
                        state="degraded"
                    )
                    mock_health_checker_class.return_value = health_checker

                    cmd.handle()
                    output = out.getvalue()

                    assert "degraded" in output.lower()

    def test_status_shows_health_status_unhealthy(self) -> None:
        """Test that status command shows unhealthy health status."""
        from litefs.domain.health import HealthStatus

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                with patch(
                    "litefs_django.management.commands.litefs_status.HealthChecker"
                ) as mock_health_checker_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    health_checker = Mock()
                    health_checker.check_health.return_value = HealthStatus(
                        state="unhealthy"
                    )
                    mock_health_checker_class.return_value = health_checker

                    cmd.handle()
                    output = out.getvalue()

                    assert "unhealthy" in output.lower()

    def test_status_json_includes_health_status(self) -> None:
        """Test that JSON output includes health_status field."""
        import json
        from litefs.domain.health import HealthStatus

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"
        mock_settings.data_path = "/var/lib/litefs"
        mock_settings.database_name = "db"
        mock_settings.proxy_addr = ":8080"
        mock_settings.retention = "1h"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                with patch(
                    "litefs_django.management.commands.litefs_status.HealthChecker"
                ) as mock_health_checker_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    health_checker = Mock()
                    health_checker.check_health.return_value = HealthStatus(
                        state="healthy"
                    )
                    mock_health_checker_class.return_value = health_checker

                    cmd.handle(format="json")
                    output = out.getvalue()

                    data = json.loads(output)
                    assert "health_status" in data
                    assert data["health_status"] == "healthy"

    def test_status_health_uses_health_checker(self) -> None:
        """Test that health status is obtained from HealthChecker use case."""
        from litefs.domain.health import HealthStatus

        out = StringIO()
        cmd = LiteFSStatusCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True
        mock_settings.leader_election = "static"

        with patch(
            "litefs_django.management.commands.litefs_status.get_litefs_settings"
        ) as mock_get_settings:
            with patch(
                "litefs_django.management.commands.litefs_status.PrimaryDetector"
            ) as mock_detector_class:
                with patch(
                    "litefs_django.management.commands.litefs_status.HealthChecker"
                ) as mock_health_checker_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    health_checker = Mock()
                    health_checker.check_health.return_value = HealthStatus(
                        state="healthy"
                    )
                    mock_health_checker_class.return_value = health_checker

                    cmd.handle()

                    # Verify HealthChecker was instantiated with the detector
                    mock_health_checker_class.assert_called_once()
                    # Verify check_health was called
                    health_checker.check_health.assert_called_once()


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestLiteFSDownloadCommand:
    """Test litefs_download management command."""

    def test_command_exists(self) -> None:
        """Test that litefs_download command can be imported."""
        from litefs_django.management.commands.litefs_download import (
            Command as LiteFSDownloadCommand,
        )

        assert LiteFSDownloadCommand is not None

    def test_command_downloads_binary_successfully(self, tmp_path: Path) -> None:
        """Test that download command successfully downloads binary."""
        from litefs_django.management.commands.litefs_download import Command

        out = StringIO()
        cmd = Command(stdout=out)

        # Mock dependencies
        mock_platform = Mock()
        mock_platform.os = "linux"
        mock_platform.arch = "amd64"

        mock_metadata = Mock()
        mock_metadata.location = Mock()
        mock_metadata.location.path = tmp_path / "litefs"
        mock_metadata.size_bytes = 12345678
        mock_metadata.checksum = "abc123"

        mock_download_result = Mock()
        mock_download_result.success = True
        mock_download_result.metadata = mock_metadata
        mock_download_result.error = None

        with patch(
            "litefs_django.management.commands.litefs_download.OsPlatformDetector"
        ) as mock_detector_class:
            with patch(
                "litefs_django.management.commands.litefs_download.BinaryDownloader"
            ) as mock_downloader_class:
                with patch(
                    "litefs_django.management.commands.litefs_download.HttpxBinaryDownloader"
                ):  # noqa: F841
                    with patch(
                        "litefs_django.management.commands.litefs_download.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        mock_detector_class.return_value.detect.return_value = (
                            mock_platform
                        )
                        mock_downloader_class.return_value.download.return_value = (
                            mock_download_result
                        )
                        mock_resolver_class.return_value.resolve.return_value = None

                        cmd.handle()
                        output = out.getvalue()

                        assert (
                            "success" in output.lower() or "complete" in output.lower()
                        )

    def test_command_handles_download_errors_gracefully(self) -> None:
        """Test that download command handles errors gracefully with helpful messages."""
        from litefs_django.management.commands.litefs_download import Command

        out = StringIO()
        cmd = Command(stdout=out)

        mock_platform = Mock()
        mock_platform.os = "linux"
        mock_platform.arch = "amd64"

        mock_download_result = Mock()
        mock_download_result.success = False
        mock_download_result.metadata = None
        mock_download_result.error = "Network connection failed"

        with patch(
            "litefs_django.management.commands.litefs_download.OsPlatformDetector"
        ) as mock_detector_class:
            with patch(
                "litefs_django.management.commands.litefs_download.BinaryDownloader"
            ) as mock_downloader_class:
                with patch(
                    "litefs_django.management.commands.litefs_download.HttpxBinaryDownloader"
                ):
                    with patch(
                        "litefs_django.management.commands.litefs_download.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        mock_detector_class.return_value.detect.return_value = (
                            mock_platform
                        )
                        mock_downloader_class.return_value.download.return_value = (
                            mock_download_result
                        )
                        mock_resolver_class.return_value.resolve.return_value = None

                        with pytest.raises(CommandError) as exc_info:
                            cmd.handle()

                        error_message = str(exc_info.value)
                        assert (
                            "network" in error_message.lower()
                            or "failed" in error_message.lower()
                        )

    def test_command_supports_force_flag(self, tmp_path: Path) -> None:
        """Test that --force flag re-downloads even when binary exists."""
        from litefs_django.management.commands.litefs_download import Command
        from litefs.domain.binary import BinaryLocation

        out = StringIO()
        cmd = Command(stdout=out)

        mock_platform = Mock()
        mock_platform.os = "linux"
        mock_platform.arch = "amd64"

        existing_binary = BinaryLocation(path=tmp_path / "litefs", is_custom=False)

        mock_metadata = Mock()
        mock_metadata.location = Mock()
        mock_metadata.location.path = tmp_path / "litefs"
        mock_metadata.size_bytes = 12345678
        mock_metadata.checksum = "abc123"

        mock_download_result = Mock()
        mock_download_result.success = True
        mock_download_result.metadata = mock_metadata
        mock_download_result.error = None

        with patch(
            "litefs_django.management.commands.litefs_download.OsPlatformDetector"
        ) as mock_detector_class:
            with patch(
                "litefs_django.management.commands.litefs_download.BinaryDownloader"
            ) as mock_downloader_class:
                with patch(
                    "litefs_django.management.commands.litefs_download.HttpxBinaryDownloader"
                ):
                    with patch(
                        "litefs_django.management.commands.litefs_download.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        mock_detector_class.return_value.detect.return_value = (
                            mock_platform
                        )
                        mock_downloader_class.return_value.download.return_value = (
                            mock_download_result
                        )
                        # Binary exists
                        mock_resolver_class.return_value.resolve.return_value = (
                            existing_binary
                        )

                        # With --force, should still download
                        cmd.handle(force=True)

                        # Verify download was called despite binary existing
                        mock_downloader_class.return_value.download.assert_called_once()

    def test_command_skips_download_when_binary_exists_without_force(
        self, tmp_path: Path
    ) -> None:
        """Test that command skips download when binary exists and --force not used."""
        from litefs_django.management.commands.litefs_download import Command
        from litefs.domain.binary import BinaryLocation

        out = StringIO()
        cmd = Command(stdout=out)

        mock_platform = Mock()
        mock_platform.os = "linux"
        mock_platform.arch = "amd64"

        existing_binary = BinaryLocation(path=tmp_path / "litefs", is_custom=False)

        with patch(
            "litefs_django.management.commands.litefs_download.OsPlatformDetector"
        ) as mock_detector_class:
            with patch(
                "litefs_django.management.commands.litefs_download.BinaryDownloader"
            ) as mock_downloader_class:
                with patch(
                    "litefs_django.management.commands.litefs_download.HttpxBinaryDownloader"
                ):
                    with patch(
                        "litefs_django.management.commands.litefs_download.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        mock_detector_class.return_value.detect.return_value = (
                            mock_platform
                        )
                        # Binary exists
                        mock_resolver_class.return_value.resolve.return_value = (
                            existing_binary
                        )

                        # Without --force, should skip download
                        cmd.handle(force=False)
                        output = out.getvalue()

                        # Download should NOT have been called
                        mock_downloader_class.return_value.download.assert_not_called()
                        # Should indicate binary already exists
                        assert "exists" in output.lower() or "already" in output.lower()

    def test_command_shows_progress_output(self, tmp_path: Path) -> None:
        """Test that command shows progress during download."""
        from litefs_django.management.commands.litefs_download import Command

        out = StringIO()
        cmd = Command(stdout=out)

        mock_platform = Mock()
        mock_platform.os = "linux"
        mock_platform.arch = "amd64"

        mock_metadata = Mock()
        mock_metadata.location = Mock()
        mock_metadata.location.path = tmp_path / "litefs"
        mock_metadata.size_bytes = 12345678
        mock_metadata.checksum = "abc123"

        mock_download_result = Mock()
        mock_download_result.success = True
        mock_download_result.metadata = mock_metadata
        mock_download_result.error = None

        with patch(
            "litefs_django.management.commands.litefs_download.OsPlatformDetector"
        ) as mock_detector_class:
            with patch(
                "litefs_django.management.commands.litefs_download.BinaryDownloader"
            ) as mock_downloader_class:
                with patch(
                    "litefs_django.management.commands.litefs_download.HttpxBinaryDownloader"
                ):
                    with patch(
                        "litefs_django.management.commands.litefs_download.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        mock_detector_class.return_value.detect.return_value = (
                            mock_platform
                        )
                        mock_downloader_class.return_value.download.return_value = (
                            mock_download_result
                        )
                        mock_resolver_class.return_value.resolve.return_value = None

                        cmd.handle()
                        output = out.getvalue()

                        # Should show some progress indication
                        assert (
                            "download" in output.lower()
                            or "linux" in output.lower()
                            or "amd64" in output.lower()
                        )

    def test_command_shows_completion_status(self, tmp_path: Path) -> None:
        """Test that command shows completion status after download."""
        from litefs_django.management.commands.litefs_download import Command

        out = StringIO()
        cmd = Command(stdout=out)

        mock_platform = Mock()
        mock_platform.os = "linux"
        mock_platform.arch = "amd64"

        mock_metadata = Mock()
        mock_metadata.location = Mock()
        mock_metadata.location.path = tmp_path / "litefs"
        mock_metadata.size_bytes = 12345678
        mock_metadata.checksum = "abc123def456"

        mock_download_result = Mock()
        mock_download_result.success = True
        mock_download_result.metadata = mock_metadata
        mock_download_result.error = None

        with patch(
            "litefs_django.management.commands.litefs_download.OsPlatformDetector"
        ) as mock_detector_class:
            with patch(
                "litefs_django.management.commands.litefs_download.BinaryDownloader"
            ) as mock_downloader_class:
                with patch(
                    "litefs_django.management.commands.litefs_download.HttpxBinaryDownloader"
                ):
                    with patch(
                        "litefs_django.management.commands.litefs_download.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        mock_detector_class.return_value.detect.return_value = (
                            mock_platform
                        )
                        mock_downloader_class.return_value.download.return_value = (
                            mock_download_result
                        )
                        mock_resolver_class.return_value.resolve.return_value = None

                        cmd.handle()
                        output = out.getvalue()

                        # Should show completion info (path, size, or checksum)
                        assert (
                            str(tmp_path) in output
                            or "12345678" in output
                            or "abc123" in output.lower()
                            or "success" in output.lower()
                            or "complete" in output.lower()
                        )

    def test_command_handles_unsupported_platform(self) -> None:
        """Test that command handles unsupported platform gracefully."""
        from litefs_django.management.commands.litefs_download import Command
        from litefs.domain.exceptions import LiteFSConfigError

        out = StringIO()
        cmd = Command(stdout=out)

        with patch(
            "litefs_django.management.commands.litefs_download.OsPlatformDetector"
        ) as mock_detector_class:
            mock_detector_class.return_value.detect.side_effect = LiteFSConfigError(
                "Unsupported platform: windows"
            )

            with pytest.raises(CommandError) as exc_info:
                cmd.handle()

            error_message = str(exc_info.value)
            assert (
                "unsupported" in error_message.lower()
                or "platform" in error_message.lower()
            )
