"""SplitBrainDetector use case for detecting split-brain scenarios.

A split-brain occurs when network partition causes the cluster consensus
to break down, resulting in multiple nodes believing they are the leader
simultaneously. This use case detects such scenarios by examining the
current state of all nodes in the cluster.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litefs.adapters.ports import SplitBrainDetectorPort
from litefs.domain.split_brain import RaftNodeState

if TYPE_CHECKING:
    from litefs.adapters.metrics_port import MetricsPort


@dataclass(frozen=True)
class SplitBrainStatus:
    """Result of split-brain detection.

    Value object containing the detection result and list of nodes
    claiming leadership. Immutable and hashable.

    Attributes:
        is_split_brain: Boolean indicating whether a split-brain was detected.
                       True if 2+ nodes claim leadership, False if 0 or 1 leaders.
        leader_nodes: List of RaftNodeState objects for all nodes claiming leadership.
                     May be empty if no leaders detected, contain one item in healthy
                     state, or multiple items if split-brain is detected.
    """

    is_split_brain: bool
    leader_nodes: list[RaftNodeState]


class SplitBrainDetector:
    """Detects split-brain scenarios in a Raft cluster.

    This use case queries the cluster state from a port implementation
    and determines whether a split-brain condition exists (multiple nodes
    claiming leadership). The detector uses the cluster topology to make
    this determination without requiring consensus protocol knowledge.

    A healthy cluster has exactly one leader. A split-brain has 2+ leaders.
    A cluster with no leaders is not healthy but is not a split-brain per se.

    Dependencies:
        - SplitBrainDetectorPort: Provides current cluster state (node IDs and leadership)

    Thread safety:
        Reads from SplitBrainDetectorPort. The port is responsible for
        synchronization of cluster state access.
    """

    def __init__(
        self,
        port: SplitBrainDetectorPort,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize the split-brain detector.

        Args:
            port: Implementation of SplitBrainDetectorPort for cluster state access.
            metrics: Optional port for emitting split-brain detection metrics.
        """
        self.port = port
        self._metrics = metrics

    def detect_split_brain(self) -> SplitBrainStatus:
        """Detect if a split-brain condition exists in the cluster.

        Queries the current cluster state and examines node leadership status.
        A split-brain is detected when 2 or more nodes claim to be the leader.

        Returns:
            SplitBrainStatus containing:
            - is_split_brain: True if 2+ leaders detected, False otherwise
            - leader_nodes: List of all nodes claiming leadership

        Raises:
            May propagate exceptions from port if cluster state cannot be determined.
        """
        # Get cluster state from port
        cluster_state = self.port.get_cluster_state()

        # Get all nodes claiming leadership
        leader_nodes = cluster_state.get_leader_nodes()

        # Split-brain is detected when more than one node claims leadership
        is_split_brain = len(leader_nodes) > 1

        # Emit split-brain metric
        if self._metrics is not None:
            self._metrics.set_split_brain_detected(is_split_brain)

        return SplitBrainStatus(
            is_split_brain=is_split_brain, leader_nodes=leader_nodes
        )
