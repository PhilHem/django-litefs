"""LiteFS settings domain entity."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from litefs.domain.exceptions import LiteFSConfigError


@dataclass(frozen=True)
class RaftConfig:
    """Raft leader election configuration.

    Value object specifying the configuration for Raft-based leader election.
    In Raft mode, nodes coordinate automatically to elect a primary.

    Attributes:
        self_addr: Network address of this node (e.g., '127.0.0.1:20202').
                  Must be non-empty and non-whitespace.
        peers: List of peer node addresses for cluster communication.
               Must be a non-empty list of non-empty strings.
    """

    self_addr: str
    peers: list[str]

    def __post_init__(self) -> None:
        """Validate Raft configuration."""
        self._validate_self_addr()
        self._validate_peers()

    def _validate_self_addr(self) -> None:
        """Validate self_addr is non-empty and contains no whitespace-only values."""
        if not self.self_addr:
            raise LiteFSConfigError("self_addr cannot be empty")

        if not self.self_addr.strip():
            raise LiteFSConfigError("self_addr cannot be whitespace-only")

    def _validate_peers(self) -> None:
        """Validate peers list is non-empty."""
        if not self.peers:
            raise LiteFSConfigError("peers list cannot be empty")


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


@dataclass(frozen=True)
class ForwardingSettings:
    """Write forwarding configuration for replica nodes.

    Value object for configuring how replica nodes forward write requests
    to the primary node in a LiteFS cluster.

    Attributes:
        enabled: Whether write forwarding is enabled. Defaults to False.
        primary_url: URL of the primary node for forwarding writes.
                    Required when enabled=True. Defaults to None.
        timeout_seconds: Timeout for forwarded requests in seconds.
                        Defaults to 30.0.
        retry_count: Number of retry attempts for failed forwards.
                    Defaults to 1.
        excluded_paths: URL paths to exclude from forwarding (e.g., health checks).
                       Uses tuple for immutability. Defaults to empty tuple.
        scheme: HTTP scheme to use for forwarding (e.g., "http", "https").
                Defaults to "http".
    """

    enabled: bool = False
    primary_url: str | None = None
    timeout_seconds: float = 30.0
    retry_count: int = 1
    excluded_paths: tuple[str, ...] = ()
    scheme: str = "http"


@dataclass(frozen=True)
class ProxySettings:
    """HTTP proxy configuration for handling read-your-writes consistency.

    Value object for LiteFS proxy settings. The proxy sits between clients and
    the application, tracking transaction IDs via cookies to ensure reads
    always see writes that occurred on previous requests.

    Attributes:
        addr: Proxy listen address (e.g., ':8080'). Must be non-empty.
        target: Application address (e.g., 'localhost:8081'). Must be non-empty.
        db: Database name for TXID tracking (e.g., 'db.sqlite3'). Must be non-empty.
        passthrough: List of URL patterns to bypass proxy (e.g., ['/static/*', '*.css']).
                    Defaults to empty list.
        primary_redirect_timeout: Duration to hold writes during failover (e.g., '5s', '10s').
                                Defaults to '5s'.
    """

    addr: str
    target: str
    db: str
    passthrough: list[str] = field(default_factory=list)
    primary_redirect_timeout: str = "5s"

    def __post_init__(self) -> None:
        """Validate proxy settings."""
        self._validate_addr()
        self._validate_target()
        self._validate_db()

    def _validate_addr(self) -> None:
        """Validate addr is non-empty and non-whitespace."""
        if not self.addr:
            raise LiteFSConfigError("addr cannot be empty")

        if not self.addr.strip():
            raise LiteFSConfigError("addr cannot be whitespace-only")

    def _validate_target(self) -> None:
        """Validate target is non-empty and non-whitespace."""
        if not self.target:
            raise LiteFSConfigError("target cannot be empty")

        if not self.target.strip():
            raise LiteFSConfigError("target cannot be whitespace-only")

    def _validate_db(self) -> None:
        """Validate db is non-empty and non-whitespace."""
        if not self.db:
            raise LiteFSConfigError("db cannot be empty")

        if not self.db.strip():
            raise LiteFSConfigError("db cannot be whitespace-only")


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
    proxy: ProxySettings | None = None

    def __post_init__(self) -> None:
        """Validate settings after initialization."""
        self._validate_database_name()
        self._validate_paths()
        self._validate_leader_election()
        self._validate_raft_config()

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

    def _validate_raft_config(self) -> None:
        """Validate Raft configuration when leader_election is 'raft'.

        When leader_election="raft", both raft_self_addr and raft_peers must be
        present and non-empty. When leader_election="static", these fields are ignored.
        """
        if self.leader_election != "raft":
            return

        # Check raft_self_addr is present
        if self.raft_self_addr is None:
            raise LiteFSConfigError(
                "raft_self_addr is required when leader_election='raft'"
            )

        # Check raft_self_addr is not empty or whitespace-only
        if not self.raft_self_addr or not self.raft_self_addr.strip():
            raise LiteFSConfigError(
                "raft_self_addr cannot be empty or whitespace-only when leader_election='raft'"
            )

        # Check raft_peers is present
        if self.raft_peers is None:
            raise LiteFSConfigError(
                "raft_peers is required when leader_election='raft'"
            )

        # Check raft_peers is not empty
        if not self.raft_peers:
            raise LiteFSConfigError(
                "raft_peers cannot be empty when leader_election='raft'"
            )
