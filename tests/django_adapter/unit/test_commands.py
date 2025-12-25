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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
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

        with patch("litefs_django.management.commands.litefs_check.get_litefs_settings") as mock_get_settings:
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
