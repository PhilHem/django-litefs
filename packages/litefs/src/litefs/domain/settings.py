"""LiteFS settings domain entity."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from litefs.domain.exceptions import LiteFSConfigError


@dataclass(frozen=True)
class StaticLeaderConfig:
    """Static leader election configuration.

    Value object specifying the designated primary node for static leader election.
    In static mode, one node is manually designated as primary and holds the write lease.

    Attributes:
        primary_hostname: Hostname of the designated primary node.
                         Must be a valid hostname (non-empty, no whitespace).
    """

    primary_hostname: str

    def __post_init__(self) -> None:
        """Validate static leader configuration."""
        self._validate_hostname()

    def _validate_hostname(self) -> None:
        """Validate primary_hostname is non-empty and contains no whitespace."""
        if not self.primary_hostname:
            raise LiteFSConfigError("primary_hostname cannot be empty")

        # Check for control characters and null bytes first (before strip checks)
        if any(ord(c) < 32 or c == "\x7f" for c in self.primary_hostname):
            raise LiteFSConfigError(
                f"primary_hostname contains control characters, got: {self.primary_hostname!r}"
            )

        if not self.primary_hostname.strip():
            raise LiteFSConfigError("primary_hostname cannot be whitespace-only")

        if self.primary_hostname != self.primary_hostname.strip():
            raise LiteFSConfigError(
                f"primary_hostname cannot have leading/trailing whitespace, got: {self.primary_hostname!r}"
            )


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
    static_leader_config: StaticLeaderConfig | None = None

    def __post_init__(self) -> None:
        """Validate settings after initialization."""
        self._validate_database_name()
        self._validate_paths()
        self._validate_leader_election()

    def _validate_database_name(self) -> None:
        """Validate that database_name is not empty or whitespace-only."""
        if not self.database_name or not self.database_name.strip():
            raise LiteFSConfigError("database_name cannot be empty or whitespace-only")

    def _validate_paths(self) -> None:
        """Validate that paths are absolute and don't contain traversal."""
        for path_name, path_value in [
            ("mount_path", self.mount_path),
            ("data_path", self.data_path),
        ]:
            # Check for null bytes first (security issue)
            if "\x00" in path_value:
                raise LiteFSConfigError(
                    f"{path_name} contains null byte, got: {path_value!r}"
                )
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
