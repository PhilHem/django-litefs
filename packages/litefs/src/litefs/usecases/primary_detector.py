"""Primary detector use case for LiteFS."""

from pathlib import Path

from litefs.domain.exceptions import LiteFSConfigError


class LiteFSNotRunningError(LiteFSConfigError):
    """Raised when LiteFS is not running or mount path is invalid."""

    pass


class PrimaryDetector:
    """Detects if current node is the primary node."""

    def __init__(self, mount_path: str) -> None:
        """Initialize primary detector.

        Args:
            mount_path: Path to LiteFS mount point
        """
        self.mount_path = Path(mount_path)
        self.primary_file = self.mount_path / ".primary"

    def is_primary(self) -> bool:
        """Check if current node is primary.

        Returns:
            True if this node is primary, False if replica

        Raises:
            LiteFSNotRunningError: If mount path doesn't exist or LiteFS is not running
        """
        if not self.mount_path.exists():
            raise LiteFSNotRunningError(
                f"LiteFS mount path does not exist: {self.mount_path}"
            )

        return self.primary_file.exists()
