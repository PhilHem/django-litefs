"""Domain events for LiteFS state transitions.

Events are immutable value objects representing state changes in the cluster.
They follow the frozen dataclass pattern used throughout the domain layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailoverEventType(Enum):
    """Types of failover events that can be emitted.

    Attributes:
        PROMOTED_TO_PRIMARY: Node transitioned from REPLICA to PRIMARY.
        DEMOTED_TO_REPLICA: Node transitioned from PRIMARY to REPLICA.
        HEALTH_DEMOTION: Node demoted due to health check failure.
        QUORUM_LOSS_DEMOTION: Node demoted due to quorum loss.
        GRACEFUL_HANDOFF: Node performed graceful leadership handoff.
    """

    PROMOTED_TO_PRIMARY = "promoted_to_primary"
    DEMOTED_TO_REPLICA = "demoted_to_replica"
    HEALTH_DEMOTION = "health_demotion"
    QUORUM_LOSS_DEMOTION = "quorum_loss_demotion"
    GRACEFUL_HANDOFF = "graceful_handoff"


@dataclass(frozen=True)
class FailoverEvent:
    """Immutable event representing a failover state transition.

    Value object emitted when FailoverCoordinator changes state.
    Contains event type and optional reason for the transition.

    Attributes:
        event_type: The type of failover event that occurred.
        reason: Optional human-readable reason for the event.
    """

    event_type: FailoverEventType
    reason: str | None = None
