"""Installation checker use case for verifying LiteFS binary installation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable


class InstallationStatus(Enum):
    """Status of LiteFS binary installation check.

    Attributes:
        OK: Binary exists, is executable, and runs successfully.
        MISSING: Binary does not exist at the specified path.
        CORRUPT: Binary exists but fails to execute properly.
        UNUSABLE: Binary exists but lacks execute permissions.
    """

    OK = "ok"
    MISSING = "missing"
    CORRUPT = "corrupt"
    UNUSABLE = "unusable"


@dataclass(frozen=True)
class InstallationCheckResult:
    """Result of installation check.

    Immutable value object containing the result of checking LiteFS
    binary installation status.

    Attributes:
        status: The installation status (OK, MISSING, CORRUPT, UNUSABLE).
        binary_path: Path to the binary checked, or None if not provided.
        error_message: Error details for failed checks, None for success.
    """

    status: InstallationStatus
    binary_path: Path | None
    error_message: str | None

    @classmethod
    def create_success(cls, binary_path: Path) -> InstallationCheckResult:
        """Create a successful installation check result.

        Args:
            binary_path: Path to the successfully verified binary.

        Returns:
            InstallationCheckResult with OK status and no error message.
        """
        return cls(
            status=InstallationStatus.OK,
            binary_path=binary_path,
            error_message=None,
        )

    @classmethod
    def create_failure(
        cls,
        status: InstallationStatus,
        binary_path: Path | None,
        error_message: str,
    ) -> InstallationCheckResult:
        """Create a failed installation check result.

        Args:
            status: The failure status (MISSING, CORRUPT, or UNUSABLE).
            binary_path: Path to the binary, or None if not provided.
            error_message: Description of why the check failed.

        Returns:
            InstallationCheckResult with the specified failure status.
        """
        return cls(
            status=status,
            binary_path=binary_path,
            error_message=error_message,
        )


@runtime_checkable
class FileCheckerPort(Protocol):
    """Port interface for file system checks.

    Implementations verify file existence and permissions.

    Contract:
        - exists(path) returns True if file exists at path
        - is_executable(path) returns True if file is executable
    """

    def exists(self, path: Path) -> bool:
        """Check if file exists at path.

        Args:
            path: Path to check.

        Returns:
            True if file exists, False otherwise.
        """
        ...

    def is_executable(self, path: Path) -> bool:
        """Check if file is executable.

        Args:
            path: Path to check.

        Returns:
            True if file is executable, False otherwise.
        """
        ...


@runtime_checkable
class BinaryExecutorPort(Protocol):
    """Port interface for executing binary commands.

    Implementations run the binary to verify it works.

    Contract:
        - run_version_check(path) runs binary with --version
        - Returns (success: bool, output: str) tuple
    """

    def run_version_check(self, path: Path) -> tuple[bool, str]:
        """Run version check on binary.

        Args:
            path: Path to the binary to run.

        Returns:
            Tuple of (success, output) where:
            - success: True if binary ran successfully
            - output: Version string on success, error message on failure
        """
        ...


class InstallationChecker:
    """Use case for checking LiteFS binary installation.

    Verifies that a LiteFS binary is properly installed by checking:
    1. Binary exists at the specified path
    2. Binary has execute permissions
    3. Binary runs successfully (via --version check)

    This use case orchestrates file system checks and binary execution
    through injected ports, returning an InstallationCheckResult with
    the appropriate status.
    """

    def __init__(
        self,
        file_checker: FileCheckerPort,
        binary_executor: BinaryExecutorPort,
    ) -> None:
        """Initialize the installation checker use case.

        Args:
            file_checker: Port for checking file existence and permissions.
            binary_executor: Port for executing binary version check.
        """
        self._file_checker = file_checker
        self._binary_executor = binary_executor

    def __call__(self, binary_path: Path | None) -> InstallationCheckResult:
        """Execute installation check workflow.

        Checks the binary at the given path for existence, permissions,
        and functionality.

        Args:
            binary_path: Path to the LiteFS binary to check, or None.

        Returns:
            InstallationCheckResult with:
            - OK if binary is fully functional
            - MISSING if path is None or file doesn't exist
            - UNUSABLE if file exists but isn't executable
            - CORRUPT if file exists and is executable but fails to run
        """
        # Check if path was provided
        if binary_path is None:
            return InstallationCheckResult.create_failure(
                status=InstallationStatus.MISSING,
                binary_path=None,
                error_message="Binary path not provided",
            )

        # Check if file exists
        if not self._file_checker.exists(binary_path):
            return InstallationCheckResult.create_failure(
                status=InstallationStatus.MISSING,
                binary_path=binary_path,
                error_message=f"Binary does not exist at {binary_path}",
            )

        # Check if file is executable
        if not self._file_checker.is_executable(binary_path):
            return InstallationCheckResult.create_failure(
                status=InstallationStatus.UNUSABLE,
                binary_path=binary_path,
                error_message=f"Binary at {binary_path} is not executable",
            )

        # Check if binary runs successfully
        success, output = self._binary_executor.run_version_check(binary_path)
        if not success:
            return InstallationCheckResult.create_failure(
                status=InstallationStatus.CORRUPT,
                binary_path=binary_path,
                error_message=f"Binary failed to run: {output}",
            )

        return InstallationCheckResult.create_success(binary_path)
