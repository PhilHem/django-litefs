"""Unit tests for InstallationChecker use case."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from litefs.usecases.installation_checker import (
    InstallationChecker,
    InstallationCheckResult,
    InstallationStatus,
)


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.InstallationChecker")
class TestInstallationChecker:
    """Test InstallationChecker use case."""

    def test_ok_when_binary_exists_executable_and_runs(self) -> None:
        """Test OK status when binary exists, is executable, and runs successfully."""
        # Arrange
        binary_path = Path("/usr/local/bin/litefs")

        file_checker = Mock()
        file_checker.exists.return_value = True
        file_checker.is_executable.return_value = True

        binary_executor = Mock()
        binary_executor.run_version_check.return_value = (True, "litefs v0.8.0")

        checker = InstallationChecker(
            file_checker=file_checker,
            binary_executor=binary_executor,
        )

        # Act
        result = checker(binary_path)

        # Assert
        assert isinstance(result, InstallationCheckResult)
        assert result.status == InstallationStatus.OK
        assert result.error_message is None
        assert result.binary_path == binary_path

    def test_missing_when_binary_path_is_none(self) -> None:
        """Test MISSING status when binary path is None."""
        # Arrange
        file_checker = Mock()
        binary_executor = Mock()

        checker = InstallationChecker(
            file_checker=file_checker,
            binary_executor=binary_executor,
        )

        # Act
        result = checker(None)

        # Assert
        assert result.status == InstallationStatus.MISSING
        assert result.error_message == "Binary path not provided"
        assert result.binary_path is None

    def test_missing_when_binary_does_not_exist(self) -> None:
        """Test MISSING status when binary file does not exist."""
        # Arrange
        binary_path = Path("/nonexistent/litefs")

        file_checker = Mock()
        file_checker.exists.return_value = False

        binary_executor = Mock()

        checker = InstallationChecker(
            file_checker=file_checker,
            binary_executor=binary_executor,
        )

        # Act
        result = checker(binary_path)

        # Assert
        assert result.status == InstallationStatus.MISSING
        assert "does not exist" in str(result.error_message)
        assert result.binary_path == binary_path

    def test_unusable_when_binary_not_executable(self) -> None:
        """Test UNUSABLE status when binary is not executable."""
        # Arrange
        binary_path = Path("/usr/local/bin/litefs")

        file_checker = Mock()
        file_checker.exists.return_value = True
        file_checker.is_executable.return_value = False

        binary_executor = Mock()

        checker = InstallationChecker(
            file_checker=file_checker,
            binary_executor=binary_executor,
        )

        # Act
        result = checker(binary_path)

        # Assert
        assert result.status == InstallationStatus.UNUSABLE
        assert "not executable" in str(result.error_message)
        assert result.binary_path == binary_path

    def test_corrupt_when_binary_fails_to_run(self) -> None:
        """Test CORRUPT status when binary fails version check."""
        # Arrange
        binary_path = Path("/usr/local/bin/litefs")

        file_checker = Mock()
        file_checker.exists.return_value = True
        file_checker.is_executable.return_value = True

        binary_executor = Mock()
        binary_executor.run_version_check.return_value = (
            False,
            "Exec format error",
        )

        checker = InstallationChecker(
            file_checker=file_checker,
            binary_executor=binary_executor,
        )

        # Act
        result = checker(binary_path)

        # Assert
        assert result.status == InstallationStatus.CORRUPT
        assert "Exec format error" in str(result.error_message)
        assert result.binary_path == binary_path

    def test_includes_error_details_on_failure(self) -> None:
        """Test that error details are included in result for all failure types."""
        # Arrange
        binary_path = Path("/usr/local/bin/litefs")

        file_checker = Mock()
        file_checker.exists.return_value = True
        file_checker.is_executable.return_value = True

        binary_executor = Mock()
        binary_executor.run_version_check.return_value = (
            False,
            "signal: killed",
        )

        checker = InstallationChecker(
            file_checker=file_checker,
            binary_executor=binary_executor,
        )

        # Act
        result = checker(binary_path)

        # Assert
        assert result.status == InstallationStatus.CORRUPT
        assert result.error_message is not None
        assert "signal: killed" in result.error_message

    def test_uses_injected_ports_not_hardcoded(self) -> None:
        """Test that use case uses injected ports via dependency injection."""
        # Arrange
        binary_path = Path("/custom/path/litefs")

        file_checker = Mock()
        file_checker.exists.return_value = True
        file_checker.is_executable.return_value = True

        binary_executor = Mock()
        binary_executor.run_version_check.return_value = (True, "v1.0.0")

        checker = InstallationChecker(
            file_checker=file_checker,
            binary_executor=binary_executor,
        )

        # Act
        result = checker(binary_path)

        # Assert - verify mocks were called
        file_checker.exists.assert_called_once_with(binary_path)
        file_checker.is_executable.assert_called_once_with(binary_path)
        binary_executor.run_version_check.assert_called_once_with(binary_path)
        assert result.status == InstallationStatus.OK


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.InstallationChecker")
class TestInstallationCheckResult:
    """Test InstallationCheckResult factory methods."""

    def test_create_success_returns_ok_result(self) -> None:
        """Test create_success factory returns OK result."""
        binary_path = Path("/usr/local/bin/litefs")
        result = InstallationCheckResult.create_success(binary_path)

        assert result.status == InstallationStatus.OK
        assert result.binary_path == binary_path
        assert result.error_message is None

    def test_create_failure_returns_result_with_error(self) -> None:
        """Test create_failure factory returns result with error details."""
        binary_path = Path("/usr/local/bin/litefs")
        result = InstallationCheckResult.create_failure(
            status=InstallationStatus.CORRUPT,
            binary_path=binary_path,
            error_message="Binary is corrupted",
        )

        assert result.status == InstallationStatus.CORRUPT
        assert result.binary_path == binary_path
        assert result.error_message == "Binary is corrupted"

    def test_create_missing_with_none_path(self) -> None:
        """Test create_failure works with None path for MISSING status."""
        result = InstallationCheckResult.create_failure(
            status=InstallationStatus.MISSING,
            binary_path=None,
            error_message="Binary path not provided",
        )

        assert result.status == InstallationStatus.MISSING
        assert result.binary_path is None
        assert result.error_message == "Binary path not provided"
