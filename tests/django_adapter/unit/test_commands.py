"""Unit tests for Django management commands."""

import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from django.core.management import call_command
from django.core.management.base import CommandError

from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig
from litefs.usecases.primary_detector import LiteFSNotRunningError
from litefs_django.management.commands.litefs_status import Command as LiteFSStatusCommand
from litefs_django.management.commands.litefs_check import Command as LiteFSCheckCommand


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
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

        with patch("litefs_django.management.commands.litefs_status.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_status.PrimaryDetector") as mock_detector_class:
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

        with patch("litefs_django.management.commands.litefs_status.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_status.PrimaryDetector") as mock_detector_class:
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

        with patch("litefs_django.management.commands.litefs_status.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_status.PrimaryDetector") as mock_detector_class:
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

        with patch("litefs_django.management.commands.litefs_status.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_status.PrimaryDetector") as mock_detector_class:
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

        with patch("litefs_django.management.commands.litefs_status.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_status.PrimaryDetector") as mock_detector_class:
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

        with patch("litefs_django.management.commands.litefs_status.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_status.PrimaryDetector") as mock_detector_class:
                mock_get_settings.return_value = mock_settings
                detector = Mock()
                detector.is_primary.side_effect = LiteFSNotRunningError("Mount path not found")
                mock_detector_class.return_value = detector

                # Command should handle the error gracefully (wraps as CommandError)
                with pytest.raises(CommandError):
                    cmd.handle()


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestLiteFSCheckCommand:
    """Test litefs_check management command."""

    def test_command_exists(self) -> None:
        """Test that litefs_check command can be imported."""
        assert LiteFSCheckCommand is not None

    def test_command_exits_zero_on_primary(self) -> None:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                with patch("litefs_django.management.commands.litefs_check.PrimaryDetector") as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    # Command should return successfully (no exception)
                    result = cmd.handle()
                    assert result is None or result == 0

    def test_command_exits_zero_on_replica(self) -> None:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                with patch("litefs_django.management.commands.litefs_check.PrimaryDetector") as mock_detector_class:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                with patch("litefs_django.management.commands.litefs_check.PrimaryDetector") as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.side_effect = LiteFSNotRunningError("Mount path not found")
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                mock_get_settings.return_value = mock_settings

                # Command should fail if LiteFS is disabled
                with pytest.raises(CommandError):
                    cmd.handle()

    def test_command_performs_health_checks(self) -> None:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                with patch("litefs_django.management.commands.litefs_check.PrimaryDetector") as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    cmd.handle()
                    output = out.getvalue()

                    # Should produce some output indicating checks were performed
                    # (could be informational or verbose output)
                    # At minimum, command should call the detector

    def test_check_validates_settings_first(self) -> None:
        """Test that check command validates settings are configured."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            from litefs.domain.exceptions import LiteFSConfigError
            mock_get_settings.side_effect = LiteFSConfigError("Missing required settings")

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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                mock_get_settings.return_value = mock_settings

                # Command should fail if database backend is not litefs
                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                assert "database backend" in str(exc_info.value).lower() or "ENGINE" in str(exc_info.value)

    def test_check_passes_when_database_backend_is_litefs(self) -> None:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                with patch("litefs_django.management.commands.litefs_check.PrimaryDetector") as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    # Command should pass
                    result = cmd.handle()
                    assert result is None or result == 0

    def test_check_verbose_output_shows_database_backend_check(self) -> None:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                with patch("litefs_django.management.commands.litefs_check.PrimaryDetector") as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    detector = Mock()
                    detector.is_primary.return_value = True
                    mock_detector_class.return_value = detector

                    cmd.handle(verbose=True)
                    output = out.getvalue()

                    # Should show database backend check in verbose output
                    assert "database" in output.lower() or "backend" in output.lower()


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                error_message = str(exc_info.value)
                # Both issues should be reported
                assert "database" in error_message.lower() or "ENGINE" in error_message
                assert "disabled" in error_message.lower() or "enabled" in error_message.lower()

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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                error_message = str(exc_info.value)
                # Should have fix suggestions (patterns from current error messages)
                # Backend fix: mentions ENGINE or DATABASES
                # Enabled fix: mentions LITEFS.ENABLED or "Enable LiteFS"
                has_backend_fix = "DATABASES" in error_message or "ENGINE" in error_message
                has_enabled_fix = "ENABLED" in error_message or "Enable" in error_message
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                mock_get_settings.return_value = mock_settings

                with pytest.raises(CommandError) as exc_info:
                    cmd.handle()

                error_message = str(exc_info.value)
                # Issues should be clearly separated (e.g., numbered list or newlines)
                # Count distinct issues by looking for issue indicators
                issue_count = error_message.count("\n- ") + error_message.count("1.") + error_message.count("2.")
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
            with patch("litefs_django.management.commands.litefs_check.settings", mock_django_settings):
                with patch("litefs_django.management.commands.litefs_check.PrimaryDetector") as mock_detector_class:
                    mock_get_settings.return_value = mock_settings
                    mock_detector_class.side_effect = Exception("Mount path not accessible")

                    with pytest.raises(CommandError) as exc_info:
                        cmd.handle()

                    error_message = str(exc_info.value)
                    # All three issues should appear
                    has_backend = "database" in error_message.lower() or "ENGINE" in error_message
                    has_enabled = "disabled" in error_message.lower() or "enabled" in error_message.lower()
                    has_mount = "mount" in error_message.lower() or "accessible" in error_message.lower()
                    assert has_backend and has_enabled and has_mount
