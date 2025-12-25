"""Port interfaces for the LiteFS core package.

Ports define the contracts that adapters must implement.
These are Protocol classes (structural subtyping) for flexible testing.
"""

from __future__ import annotations

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
