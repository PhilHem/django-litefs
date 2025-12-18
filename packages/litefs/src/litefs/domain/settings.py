"""LiteFS settings domain entity."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from litefs.domain.exceptions import LiteFSConfigError


@dataclass
class LiteFSSettings:
    """LiteFS configuration settings.

    Domain entity with zero external dependencies.
    """

    mount_path: str
    data_path: str
    database_name: str
    leader_election: Literal["static", "raft"]
    proxy_addr: str
    enabled: bool
    retention: str
    raft_self_addr: str | None = None
    raft_peers: list[str] | None = None

    def __post_init__(self) -> None:
        """Validate settings after initialization."""
        self._validate_paths()
        self._validate_leader_election()

    def _validate_paths(self) -> None:
        """Validate that paths are absolute and don't contain traversal."""
        for path_name, path_value in [
            ("mount_path", self.mount_path),
            ("data_path", self.data_path),
        ]:
            path = Path(path_value)
            # Check for path traversal first (even in relative paths)
            if ".." in path.parts:
                raise LiteFSConfigError(
                    f"{path_name} contains path traversal, got: {path_value}"
                )
            # Then check that path is absolute
            if not path.is_absolute():
                raise LiteFSConfigError(
                    f"{path_name} must be an absolute path, got: {path_value}"
                )

    def _validate_leader_election(self) -> None:
        """Validate leader_election value."""
        if self.leader_election not in ("static", "raft"):
            raise LiteFSConfigError(
                f"leader_election must be 'static' or 'raft', got: {self.leader_election}"
            )
