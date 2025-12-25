"""Port interfaces for the LiteFS core package.

Ports define the contracts that adapters must implement.
These are Protocol classes (structural subtyping) for flexible testing.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class PrimaryDetectorPort(Protocol):
    """Port interface for primary node detection.

    Implementations check whether the current node is the primary (leader)
    in a LiteFS cluster. The primary node is the only one that can accept
    write operations.

    Contract:
        - is_primary() returns True if this node is primary, False if replica
        - May raise LiteFSNotRunningError if LiteFS is not available
    """

    def is_primary(self) -> bool:
        """Check if current node is primary.

        Returns:
            True if this node is primary (can accept writes),
            False if this node is a replica (read-only).

        Raises:
            LiteFSNotRunningError: If LiteFS is not running or mount path invalid.
        """
        ...


@runtime_checkable
class NodeIDResolverPort(Protocol):
    """Port interface for resolving the current node's ID/hostname.

    Implementations resolve how to identify the current node within a cluster.
    This enables testable abstraction of hostname resolution.

    Contract:
        - resolve_node_id() returns a non-empty string identifying this node
        - The returned string should be consistent across multiple calls
        - May raise KeyError if required configuration is missing
        - May raise ValueError if resolved ID is invalid (e.g., empty after stripping)
    """

    def resolve_node_id(self) -> str:
        """Resolve the current node's ID/hostname.

        Returns:
            A non-empty string uniquely identifying this node in the cluster.

        Raises:
            KeyError: If required environment variable or configuration is missing.
            ValueError: If the resolved ID is invalid (e.g., empty after stripping).
        """
        ...


class EnvironmentNodeIDResolver:
    """Default implementation: resolve node ID from LITEFS_NODE_ID environment variable.

    Reads the LITEFS_NODE_ID environment variable and returns it after stripping
    whitespace. This is the standard way to configure node identity in containerized
    deployments.
    """

    def resolve_node_id(self) -> str:
        """Resolve node ID from LITEFS_NODE_ID environment variable.

        Returns:
            The value of LITEFS_NODE_ID after stripping whitespace.

        Raises:
            KeyError: If LITEFS_NODE_ID environment variable is not set.
            ValueError: If LITEFS_NODE_ID is empty or whitespace-only after stripping.
        """
        node_id = os.environ["LITEFS_NODE_ID"]
        node_id_stripped = node_id.strip()

        if not node_id_stripped:
            raise ValueError("node ID cannot be empty or whitespace-only")

        return node_id_stripped
