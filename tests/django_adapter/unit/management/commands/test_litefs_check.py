"""Tests for litefs_check management command binary verification."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch
import json

import pytest
from django.core.management.base import CommandError

from litefs.domain.settings import LiteFSSettings
from litefs.usecases.installation_checker import (
    InstallationCheckResult,
    InstallationStatus,
)
from litefs_django.management.commands.litefs_check import (
    Command as LiteFSCheckCommand,
)


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django")
class TestLiteFSCheckBinaryVerification:
    """Tests for binary verification in litefs_check command."""

    def test_binary_check_passes_when_binary_exists_and_runs(self) -> None:
        """Binary check passes when binary is found and executes successfully."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        binary_path = Path("/usr/local/bin/litefs")
        mock_install_result = InstallationCheckResult.create_success(binary_path)

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = (
                                Mock(path=binary_path)
                            )
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            cmd.handle(verbosity=2)
                            output = out.getvalue()

                            assert "binary" in output.lower()
                            mock_checker_class.return_value.assert_called_once()

    def test_binary_check_fails_when_binary_missing(self) -> None:
        """Binary check fails with clear error when binary is not found."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        mock_install_result = InstallationCheckResult.create_failure(
            status=InstallationStatus.MISSING,
            binary_path=None,
            error_message="Binary path not provided",
        )

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = None
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            with pytest.raises(CommandError) as exc_info:
                                cmd.handle()

                            assert "binary" in str(exc_info.value).lower()

    def test_binary_check_fails_when_binary_corrupt(self) -> None:
        """Binary check fails when binary exists but cannot execute."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        binary_path = Path("/usr/local/bin/litefs")
        mock_install_result = InstallationCheckResult.create_failure(
            status=InstallationStatus.CORRUPT,
            binary_path=binary_path,
            error_message="Binary failed to run: segfault",
        )

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = (
                                Mock(path=binary_path)
                            )
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            with pytest.raises(CommandError) as exc_info:
                                cmd.handle()

                            error_msg = str(exc_info.value).lower()
                            assert "binary" in error_msg or "corrupt" in error_msg

    def test_binary_check_json_output_includes_binary_status(self) -> None:
        """JSON output includes binary installation status."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        binary_path = Path("/usr/local/bin/litefs")
        mock_install_result = InstallationCheckResult.create_success(binary_path)

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = (
                                Mock(path=binary_path)
                            )
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            cmd.handle(format="json")
                            output = out.getvalue()

                            data = json.loads(output)
                            checks = {c["name"]: c for c in data["checks"]}
                            assert "binary" in checks
                            assert checks["binary"]["passed"] is True

    def test_binary_check_json_output_includes_binary_path(self) -> None:
        """JSON output includes binary path when available."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        binary_path = Path("/usr/local/bin/litefs")
        mock_install_result = InstallationCheckResult.create_success(binary_path)

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = (
                                Mock(path=binary_path)
                            )
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            cmd.handle(format="json")
                            output = out.getvalue()

                            data = json.loads(output)
                            checks = {c["name"]: c for c in data["checks"]}
                            assert (
                                "/usr/local/bin/litefs" in checks["binary"]["message"]
                            )

    def test_binary_check_verbose_output_shows_binary_info(self) -> None:
        """Verbose output shows binary check details."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        binary_path = Path("/usr/local/bin/litefs")
        mock_install_result = InstallationCheckResult.create_success(binary_path)

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = (
                                Mock(path=binary_path)
                            )
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            cmd.handle(verbosity=2)
                            output = out.getvalue()

                            stdout_lower = output.lower()
                            assert "binary" in stdout_lower
                            # Should show check progress
                            assert "[" in output and "/" in output and "]" in output

    def test_binary_check_handles_unusable_binary(self) -> None:
        """Binary check reports unusable binary (no execute permission)."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        binary_path = Path("/usr/local/bin/litefs")
        mock_install_result = InstallationCheckResult.create_failure(
            status=InstallationStatus.UNUSABLE,
            binary_path=binary_path,
            error_message="Binary at /usr/local/bin/litefs is not executable",
        )

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = (
                                Mock(path=binary_path)
                            )
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            with pytest.raises(CommandError) as exc_info:
                                cmd.handle()

                            error_msg = str(exc_info.value).lower()
                            assert "binary" in error_msg or "executable" in error_msg

    def test_binary_check_json_failure_includes_binary_issue(self) -> None:
        """JSON output for failed binary check includes issue details."""
        out = StringIO()
        cmd = LiteFSCheckCommand(stdout=out)

        mock_settings = Mock(spec=LiteFSSettings)
        mock_settings.mount_path = "/litefs"
        mock_settings.enabled = True

        mock_django_settings = Mock()
        mock_django_settings.LITEFS = {}
        mock_django_settings.DATABASES = {
            "default": {"ENGINE": "litefs_django.db.backends.litefs"}
        }

        mock_install_result = InstallationCheckResult.create_failure(
            status=InstallationStatus.MISSING,
            binary_path=None,
            error_message="Binary path not provided",
        )

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
                    with patch(
                        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
                    ) as mock_resolver_class:
                        with patch(
                            "litefs_django.management.commands.litefs_check.InstallationChecker"
                        ) as mock_checker_class:
                            mock_get_settings.return_value = mock_settings
                            detector = Mock()
                            detector.is_primary.return_value = True
                            mock_detector_class.return_value = detector

                            mock_resolver_class.return_value.resolve.return_value = None
                            mock_checker_class.return_value.return_value = (
                                mock_install_result
                            )

                            with pytest.raises(CommandError):
                                cmd.handle(format="json")

                            output = out.getvalue()
                            data = json.loads(output)
                            assert data["status"] == "error"
                            # Check that binary failure is in issues
                            binary_issues = [
                                i
                                for i in data["issues"]
                                if "binary" in i["description"].lower()
                            ]
                            assert len(binary_issues) > 0
