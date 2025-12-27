"""Primary URL detector use case for LiteFS."""

from pathlib import Path


class PrimaryURLDetector:
    """Detects primary node URL from .primary file.

    The .primary file is managed by LiteFS and contains:
    - Empty content: this node is the primary
    - URL content: the primary node's URL (e.g., "primary.local:8080")
    - File missing: no primary elected yet
    """

    def __init__(self, mount_path: str) -> None:
        """Initialize primary URL detector.

        Args:
            mount_path: Path to LiteFS mount point
        """
        self.mount_path = Path(mount_path)
        self.primary_file = self.mount_path / ".primary"

    def get_primary_url(self) -> str | None:
        """Get the primary node URL.

        Returns:
            None: if .primary file doesn't exist (no primary elected)
            "": if .primary file is empty (this node is primary)
            str: the primary URL if file has content
        """
        if not self.primary_file.exists():
            return None

        content = self.primary_file.read_text()
        return content.strip()
