"""Internal PySyncObj wrapper for leader election."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from pysyncobj import SyncObj, SyncObjConf

if TYPE_CHECKING:
    from collections.abc import Callable

# PySyncObj state constants
_STATE_FOLLOWER = 0
_STATE_CANDIDATE = 1
_STATE_LEADER = 2


class LeaderElectionNode(SyncObj):
    """Minimal SyncObj for leader election only - no replicated state.

    This class wraps PySyncObj's SyncObj to provide a simple leader election
    mechanism. It does not use any replicated state - only the Raft consensus
    for leader election.

    Attributes:
        is_leader: Thread-safe property indicating if this node is the leader.
    """

    def __init__(
        self,
        self_address: str,
        partners: list[str],
        *,
        election_timeout_ms: int = 5000,
        heartbeat_interval_ms: int = 1000,
        on_leader_change: Callable[[bool], None] | None = None,
    ) -> None:
        """Initialize the leader election node.

        Args:
            self_address: This node's address in "host:port" format.
            partners: List of partner node addresses in "host:port" format.
            election_timeout_ms: Election timeout in milliseconds.
            heartbeat_interval_ms: Heartbeat interval in milliseconds.
            on_leader_change: Optional callback called when leadership changes.
                Receives True when becoming leader, False when losing leadership.
        """
        self._is_leader = False
        self._lock = threading.Lock()
        self._on_leader_change = on_leader_change

        conf = SyncObjConf(
            appendEntriesPeriod=heartbeat_interval_ms / 1000.0,
            raftMinTimeout=election_timeout_ms / 1000.0,
            raftMaxTimeout=(election_timeout_ms * 1.5) / 1000.0,
            onStateChanged=self._handle_state_change,
            autoTick=True,
            dynamicMembershipChange=False,  # Static membership for simplicity
        )

        super().__init__(self_address, partners, conf=conf)

    @property
    def is_leader(self) -> bool:
        """Check if this node is currently the leader.

        Thread-safe property.
        """
        with self._lock:
            return self._is_leader

    def _handle_state_change(self, old_state: int, new_state: int) -> None:
        """Handle Raft state transitions.

        Called by PySyncObj when the node's role changes.
        """
        was_leader = old_state == _STATE_LEADER
        is_now_leader = new_state == _STATE_LEADER

        if was_leader != is_now_leader:
            with self._lock:
                self._is_leader = is_now_leader

            if self._on_leader_change is not None:
                self._on_leader_change(is_now_leader)

    def get_responding_nodes_count(self) -> int:
        """Get the number of nodes currently responding in the cluster.

        Returns:
            Number of nodes that are responding (including self if leader).
        """
        status = self.getStatus()
        if status is None:
            return 1  # At minimum, self is responding

        # Count nodes that are responding
        responding = 1  # Self
        for key, value in status.items():
            if key.startswith("partner_node_status_") and value == 2:
                # Status 2 means node is connected
                responding += 1

        return responding
