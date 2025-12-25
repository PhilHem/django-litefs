"""Mount path validation use case."""

from __future__ import annotations

from pathlib import Path

from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.primary_detector import LiteFSNotRunningError


class MountValidator:
    """Validates LiteFS mount paths."""

    def validate(self, mount_path: Path) -> None:
        """Validate mount path exists and is absolute.

        Args:
            mount_path: Path to validate

        Raises:
            LiteFSConfigError: If path is not absolute
            LiteFSNotRunningError: If path doesn't exist (LiteFS not running)
        """
        # Check if path is absolute
        if not mount_path.is_absolute():
            raise LiteFSConfigError(
                f"mount_path must be an absolute path, got: {mount_path}"
            )

        # Check if path exists (raises LiteFSNotRunningError for runtime state)
        if not mount_path.exists():
            raise LiteFSNotRunningError(
                f"LiteFS mount path does not exist: {mount_path}. "
                "LiteFS may not be running or mounted."
            )

