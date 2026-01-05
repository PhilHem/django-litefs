"""Primary marker writer use case for static leader election."""

from pathlib import Path


class PrimaryMarkerWriter:
    """Writes and manages the .primary marker file for LiteFS.

    In static leader election mode, the designated primary node must
    write a .primary file to the LiteFS mount path. LiteFS reads this
    file to determine which node can accept writes.

    This is a stateless use case with filesystem I/O operations.
    """

    def __init__(self, mount_path: str) -> None:
        """Initialize the marker writer.

        Args:
            mount_path: Path to LiteFS mount point.
        """
        self._mount_path = Path(mount_path)
        self._primary_file = self._mount_path / ".primary"

    @property
    def mount_path(self) -> Path:
        """Return the LiteFS mount path."""
        return self._mount_path

    @property
    def primary_file(self) -> Path:
        """Return the path to the .primary marker file."""
        return self._primary_file

    def write_marker(self, node_id: str) -> None:
        """Write the primary marker file with the node ID.

        Args:
            node_id: The node ID to write (typically hostname).

        Raises:
            OSError: If file write fails.
        """
        self._primary_file.write_text(node_id)

    def remove_marker(self) -> None:
        """Remove the primary marker file.

        Idempotent: safe to call even if file doesn't exist.

        Raises:
            OSError: If file removal fails (other than FileNotFoundError).
        """
        try:
            self._primary_file.unlink()
        except FileNotFoundError:
            pass  # Already removed, this is fine

    def marker_exists(self) -> bool:
        """Check if the primary marker file exists.

        Returns:
            True if .primary file exists, False otherwise.
        """
        return self._primary_file.exists()

    def read_marker(self) -> str | None:
        """Read current marker content.

        Returns:
            The node ID from the marker file, or None if file doesn't exist.
        """
        if not self.marker_exists():
            return None
        return self._primary_file.read_text().strip()
