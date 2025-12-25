# Split-Brain Handling: Concrete Code Examples

## Phase 1: Ports (Add to adapters/ports.py)

```python
"""Split-brain detection and resolution ports.

These ports define the contracts for detecting network partitions
and safely fencing write access when split-brain is detected.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class HealthStatus:
    """Health status of a node."""
    is_healthy: bool
    last_check: float  # Unix timestamp
    reason: str | None = None  # Why unhealthy (e.g., "disk_full")


class ConflictResolutionStrategy(Enum):
    """Strategies for handling detected split-brain."""
    ROLLBACK_TO_CHECKPOINT = "rollback_to_checkpoint"
    FORCE_REPLICA = "force_replica"
    SHUTDOWN_SAFE = "shutdown_safe"


class SplitBrainDetectedError(LiteFSConfigError):
    """Raised when split-brain is detected and cannot be resolved."""
    pass


@runtime_checkable
class SplitBrainDetectorPort(Protocol):
    """Port interface for detecting split-brain scenarios.
    
    Split-brain occurs when a node loses quorum but still believes
    it's the leader (stale leadership). This port detects such
    conditions before they cause data corruption.
    """
    
    def has_quorum(self) -> bool:
        """Check if quorum is established.
        
        Returns:
            True if this node can reach >n/2 cluster members, False if partitioned.
        """
        ...
    
    def can_commit_writes(self) -> bool:
        """Check if this node can safely accept writes.
        
        Returns True only if:
        1. This node is the elected leader (Raft consensus) AND
        2. Quorum is established (can reach majority of cluster)
        
        Returns:
            True if safe to accept writes, False otherwise.
        """
        ...
    
    def last_heartbeat_from(self, node_id: str) -> float:
        """Get seconds since last heartbeat from a peer node.
        
        Args:
            node_id: The node to check.
        
        Returns:
            Seconds since last heartbeat (0.0 if just received).
            Returns float('inf') if never received from this node.
        """
        ...
    
    def detect_stale_leadership(self) -> bool:
        """Detect if this node thinks it's PRIMARY but lost quorum.
        
        This is the critical split-brain detector.
        
        Logic:
            stale = (
                is_leader_elected() AND  # Node thinks it's leader
                not has_quorum()         # But can't reach quorum
            )
        
        Returns:
            True if stale leadership is detected, False otherwise.
        """
        ...


@runtime_checkable
class ConflictResolutionPort(Protocol):
    """Port interface for split-brain conflict resolution.
    
    When split-brain is detected, this port provides strategies
    to safely transition the node to a non-writing state.
    """
    
    def fence_write_access(self) -> None:
        """Fence (immediately block) write access on this node.
        
        Called when split-brain is detected. Ensures writes are rejected
        at the file system level.
        
        Implementation: Revoke .primary file from LiteFS mount.
        Idempotent: calling multiple times is safe.
        """
        ...
    
    def apply_resolution_strategy(
        self, strategy: ConflictResolutionStrategy
    ) -> None:
        """Apply a conflict resolution strategy.
        
        Args:
            strategy: One of FORCE_REPLICA, ROLLBACK_TO_CHECKPOINT, SHUTDOWN_SAFE.
        
        Raises:
            SplitBrainDetectedError: If strategy application fails.
        """
        ...


@runtime_checkable
class HealthStatePort(Protocol):
    """Port interface for reporting node health status.
    
    Raft consensus depends on accurate health reporting. Nodes report
    their health status to peers so quorum calculation is correct.
    """
    
    def get_health_status(self) -> HealthStatus:
        """Get the current health status of this node.
        
        Returns:
            HealthStatus with degraded/healthy/unhealthy flags.
        """
        ...
    
    def update_health(self, status: HealthStatus) -> None:
        """Update the health status on this node.
        
        Called periodically to report health to peers via Raft.
        Allows leader to exclude unhealthy followers from quorum.
        
        Args:
            status: New health status.
        """
        ...
```

**Update adapters/__init__.py**:

```python
from litefs.adapters.ports import (
    # ... existing imports ...
    SplitBrainDetectorPort,
    ConflictResolutionPort,
    HealthStatePort,
    ConflictResolutionStrategy,
    HealthStatus,
    SplitBrainDetectedError,
)

__all__ = [
    # ... existing exports ...
    "SplitBrainDetectorPort",
    "ConflictResolutionPort",
    "HealthStatePort",
    "ConflictResolutionStrategy",
    "HealthStatus",
    "SplitBrainDetectedError",
]
```

---

## Phase 2: Minimal Adapters

### SplitBrainDetectorAdapter

**File**: `adapters/split_brain_detector_adapter.py`

```python
"""Adapter for detecting split-brain via Raft quorum status."""

from __future__ import annotations
import logging
from litefs.adapters.ports import SplitBrainDetectorPort, RaftLeaderElectionPort

logger = logging.getLogger(__name__)


class SplitBrainDetectorAdapter:
    """Detects split-brain by querying Raft quorum status.
    
    Implementation:
    - has_quorum() delegates to RaftLeaderElectionPort.is_quorum_reached()
    - detect_stale_leadership() combines leadership + quorum status
    - last_heartbeat_from() queries py-leader internals (future enhancement)
    """
    
    def __init__(
        self,
        raft_port: RaftLeaderElectionPort,
        heartbeat_timeout_factor: float = 1.5,
    ):
        """Initialize detector with Raft port.
        
        Args:
            raft_port: RaftLeaderElectionPort implementation (e.g., from py-leader).
            heartbeat_timeout_factor: Multiplier for heartbeat timeout detection.
        """
        self.raft_port = raft_port
        self.heartbeat_timeout_factor = heartbeat_timeout_factor
    
    def has_quorum(self) -> bool:
        """Check if quorum is established.
        
        Delegates to the Raft port.
        """
        return self.raft_port.is_quorum_reached()
    
    def can_commit_writes(self) -> bool:
        """Check if safe to accept writes.
        
        True only if this node is both elected leader AND has quorum.
        """
        return (
            self.raft_port.is_leader_elected()
            and self.raft_port.is_quorum_reached()
        )
    
    def last_heartbeat_from(self, node_id: str) -> float:
        """Get seconds since last heartbeat from a peer.
        
        Future implementation: Query py-leader's peer tracker.
        For now: Approximate via quorum status.
        """
        # TODO: Query py-leader internals for actual heartbeat timestamps
        # For MVP: Return 0.0 if quorum, else election_timeout
        if self.has_quorum():
            return 0.0  # All peers responding
        else:
            return self.raft_port.get_election_timeout()
    
    def detect_stale_leadership(self) -> bool:
        """Detect if elected but no quorum (split-brain).
        
        Logic:
            stale = is_leader_elected AND NOT is_quorum_reached
        
        This is the critical split-brain condition.
        """
        is_elected = self.raft_port.is_leader_elected()
        has_qorum = self.raft_port.is_quorum_reached()
        
        is_stale = is_elected and not has_qorum
        
        if is_stale:
            logger.warning(
                "Split-brain detected: elected leader but lost quorum. "
                "Will fence write access."
            )
        
        return is_stale
```

### ConflictResolutionAdapter

**File**: `adapters/conflict_resolution_adapter.py`

```python
"""Adapter for resolving split-brain via write fencing."""

from __future__ import annotations
import logging
from pathlib import Path
from litefs.adapters.ports import ConflictResolutionPort, ConflictResolutionStrategy
from litefs.domain.exceptions import SplitBrainDetectedError

logger = logging.getLogger(__name__)


class ConflictResolutionAdapter:
    """Resolves split-brain by fencing write access.
    
    Implementation:
    - fence_write_access() moves .primary file to prevent LiteFS writes
    - apply_resolution_strategy() executes the chosen recovery strategy
    """
    
    def __init__(self, litefs_mount: str = "/litefs"):
        """Initialize resolver with LiteFS mount path.
        
        Args:
            litefs_mount: Path to LiteFS mount point.
        """
        self.mount_path = Path(litefs_mount)
        self.primary_file = self.mount_path / ".primary"
        self.blocked_file = self.mount_path / ".primary.blocked"
    
    def fence_write_access(self) -> None:
        """Fence write access by removing .primary file.
        
        LiteFS reads .primary to determine if this node can write.
        Moving the file blocks writes at the file system level.
        
        Idempotent: safe to call multiple times.
        """
        if not self.mount_path.exists():
            logger.error(f"LiteFS mount not found: {self.mount_path}")
            return
        
        if self.primary_file.exists():
            try:
                # Move .primary to .primary.blocked as a fence marker
                self.primary_file.rename(self.blocked_file)
                logger.critical(
                    f"Write access fenced: moved {self.primary_file} "
                    f"to {self.blocked_file}"
                )
            except OSError as e:
                logger.error(
                    f"Failed to fence write access: {e}. "
                    "Manual intervention may be needed."
                )
        else:
            # Already blocked or missing; no action needed
            logger.info(".primary file already missing; node is fenced.")
    
    def apply_resolution_strategy(
        self, strategy: ConflictResolutionStrategy
    ) -> None:
        """Apply a conflict resolution strategy.
        
        Args:
            strategy: FORCE_REPLICA, ROLLBACK_TO_CHECKPOINT, or SHUTDOWN_SAFE.
        
        Raises:
            SplitBrainDetectedError: If strategy fails unrecoverably.
        """
        if strategy == ConflictResolutionStrategy.FORCE_REPLICA:
            # Already fenced; no additional action for FORCE_REPLICA
            logger.info("Applying FORCE_REPLICA strategy: write access fenced")
            return
        
        elif strategy == ConflictResolutionStrategy.ROLLBACK_TO_CHECKPOINT:
            # Future: Implement checkpoint recovery
            logger.warning(
                "ROLLBACK_TO_CHECKPOINT strategy not yet implemented. "
                "Using FORCE_REPLICA instead."
            )
            return
        
        elif strategy == ConflictResolutionStrategy.SHUTDOWN_SAFE:
            # Future: Implement graceful shutdown
            logger.critical(
                "SHUTDOWN_SAFE strategy not yet implemented. "
                "Node will continue in REPLICA mode (fenced)."
            )
            return
        
        else:
            raise SplitBrainDetectedError(f"Unknown strategy: {strategy}")
```

---

## Phase 3: Use Case Orchestration

**File**: `usecases/split_brain_coordinator.py`

```python
"""SplitBrainCoordinator: Orchestrate detection and resolution."""

from __future__ import annotations
from enum import Enum
import logging

from litefs.adapters.ports import (
    SplitBrainDetectorPort,
    ConflictResolutionPort,
    ConflictResolutionStrategy,
)
from litefs.usecases.failover_coordinator import FailoverCoordinator

logger = logging.getLogger(__name__)


class SplitBrainState(Enum):
    """State of split-brain detection."""
    HEALTHY = "healthy"
    SPLIT_BRAIN_DETECTED = "split_brain_detected"
    RESOLVED = "resolved"
    FAILED = "failed"


class SplitBrainCoordinator:
    """Orchestrates split-brain detection and resolution.
    
    Monitors quorum status and triggers conflict resolution when
    a split-brain condition is detected.
    
    Polling-based: called by application's health check or periodic task.
    
    State machine:
        HEALTHY -> (detect_stale_leadership) -> SPLIT_BRAIN_DETECTED
        SPLIT_BRAIN_DETECTED -> (apply_resolution) -> RESOLVED
        RESOLVED -> (retry_quorum) -> HEALTHY
    """
    
    def __init__(
        self,
        detector: SplitBrainDetectorPort,
        resolver: ConflictResolutionPort,
        failover: FailoverCoordinator,
    ):
        """Initialize split-brain coordinator.
        
        Args:
            detector: Port for detecting split-brain.
            resolver: Port for applying resolution strategies.
            failover: Existing FailoverCoordinator for state transitions.
        """
        self.detector = detector
        self.resolver = resolver
        self.failover = failover
        self._state = SplitBrainState.HEALTHY
    
    @property
    def state(self) -> SplitBrainState:
        """Get current split-brain state."""
        return self._state
    
    def check_and_resolve_split_brain(self) -> SplitBrainState:
        """Check for split-brain and resolve if detected.
        
        This is the main entry point, called by health check middleware
        or background worker.
        
        Returns:
            Current SplitBrainState after check and resolution.
        
        Logic:
            1. If stale leadership detected:
               a. Fence writes immediately
               b. Apply resolution strategy
               c. Demote from leadership (Raft)
               d. Transition to REPLICA state
            2. Otherwise, return HEALTHY
        """
        try:
            if self.detector.detect_stale_leadership():
                self._state = SplitBrainState.SPLIT_BRAIN_DETECTED
                self._resolve_split_brain()
                self._state = SplitBrainState.RESOLVED
            else:
                self._state = SplitBrainState.HEALTHY
        except Exception as e:
            logger.exception(f"Error during split-brain check: {e}")
            self._state = SplitBrainState.FAILED
        
        return self._state
    
    def _resolve_split_brain(self) -> None:
        """Internal: Apply resolution steps in sequence.
        
        Order matters:
            1. Fence immediately (prevent further damage)
            2. Apply strategy (recovery)
            3. Demote from leader (Raft consensus)
            4. Transition state (application state)
        """
        logger.critical("Resolving split-brain condition...")
        
        # Step 1: Fence write access at file system level
        self.resolver.fence_write_access()
        
        # Step 2: Apply resolution strategy
        self.resolver.apply_resolution_strategy(
            ConflictResolutionStrategy.FORCE_REPLICA
        )
        
        # Step 3: Demote from leadership in Raft consensus
        try:
            self.failover.leader_election.demote_from_leader()
            logger.info("Demoted from leader in Raft consensus")
        except Exception as e:
            logger.error(f"Failed to demote from leader: {e}")
            # Continue anyway; fencing is already applied
        
        # Step 4: Transition application state
        try:
            self.failover.coordinate_transition()
            logger.info(
                f"Transitioned to state: {self.failover.state}"
            )
        except Exception as e:
            logger.error(f"Failed to transition state: {e}")
            # Continue anyway; fencing is already applied


# Enum for return type
class SplitBrainEvent:
    """Event emitted when split-brain is detected.
    
    Used for observability (metrics, alerts).
    """
    
    def __init__(
        self,
        detected: bool,
        state: SplitBrainState,
        node_id: str | None = None,
        timestamp: float | None = None,
    ):
        self.detected = detected
        self.state = state
        self.node_id = node_id
        self.timestamp = timestamp
```

---

## Phase 3b: Integration with Django (Middleware)

**File**: `litefs_django/middleware.py` (new or add to existing)

```python
"""Django middleware for split-brain detection."""

from __future__ import annotations
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class LiteFSSplitBrainHealthCheckMiddleware:
    """Middleware that periodically checks for split-brain.
    
    Calls SplitBrainCoordinator.check_and_resolve_split_brain()
    every N requests to detect and fence split-brain conditions.
    
    Configuration:
        LITEFS = {
            "DETECT_SPLIT_BRAIN": True,
            "SPLIT_BRAIN_CHECK_INTERVAL": 100,  # Check every 100 requests
        }
    """
    
    def __init__(self, get_response):
        """Initialize middleware.
        
        Args:
            get_response: Django WSGI application.
        """
        self.get_response = get_response
        self.coordinator = None
        self.check_interval = 100
        self.request_count = 0
        
        # Initialize if split-brain detection is enabled
        litefs_config = settings.LITEFS
        if litefs_config.get("DETECT_SPLIT_BRAIN", False):
            self._initialize_coordinator()
            self.check_interval = litefs_config.get(
                "SPLIT_BRAIN_CHECK_INTERVAL", 100
            )
    
    def _initialize_coordinator(self) -> None:
        """Lazy-initialize SplitBrainCoordinator (avoids circular imports)."""
        try:
            from litefs.adapters.split_brain_detector_adapter import (
                SplitBrainDetectorAdapter,
            )
            from litefs.adapters.conflict_resolution_adapter import (
                ConflictResolutionAdapter,
            )
            from litefs.usecases.split_brain_coordinator import (
                SplitBrainCoordinator,
            )
            from litefs_django.apps import get_failover_coordinator
            
            litefs_config = settings.LITEFS
            raft_adapter = litefs_config.get("raft_adapter")
            
            if raft_adapter:
                detector = SplitBrainDetectorAdapter(raft_adapter)
                resolver = ConflictResolutionAdapter(
                    litefs_mount=litefs_config.get("MOUNT_PATH", "/litefs")
                )
                failover = get_failover_coordinator()
                
                self.coordinator = SplitBrainCoordinator(
                    detector=detector,
                    resolver=resolver,
                    failover=failover,
                )
                logger.info("SplitBrainCoordinator initialized")
        except Exception as e:
            logger.exception(
                f"Failed to initialize SplitBrainCoordinator: {e}"
            )
            self.coordinator = None
    
    def __call__(self, request):
        """Process request and periodically check for split-brain."""
        # Check for split-brain every N requests
        if self.coordinator:
            self.request_count += 1
            if self.request_count >= self.check_interval:
                self.request_count = 0
                state = self.coordinator.check_and_resolve_split_brain()
                if state.name != "HEALTHY":
                    logger.warning(f"Split-brain state: {state}")
        
        # Continue with normal request processing
        response = self.get_response(request)
        return response
```

---

## Testing Examples

### Unit Test: SplitBrainDetectorAdapter

**File**: `tests/core/unit/adapters/test_split_brain_detector_adapter.py`

```python
"""Unit tests for SplitBrainDetectorAdapter."""

import pytest
from litefs.adapters.split_brain_detector_adapter import (
    SplitBrainDetectorAdapter,
)


class MockRaftLeaderElectionPort:
    """Mock Raft port for testing."""
    
    def __init__(self, is_elected: bool = False, is_quorum: bool = True):
        self.is_elected = is_elected
        self.is_quorum = is_quorum
    
    def is_leader_elected(self) -> bool:
        return self.is_elected
    
    def is_quorum_reached(self) -> bool:
        return self.is_quorum
    
    def get_election_timeout(self) -> float:
        return 0.3
    
    def get_cluster_members(self) -> list[str]:
        return ["node1", "node2", "node3"]


@pytest.mark.unit
class TestSplitBrainDetectorAdapter:
    """Test SplitBrainDetectorAdapter detection logic."""
    
    def test_detect_stale_leadership_when_elected_but_no_quorum(self):
        """Test stale leadership detection when elected but lost quorum."""
        raft = MockRaftLeaderElectionPort(is_elected=True, is_quorum=False)
        detector = SplitBrainDetectorAdapter(raft)
        
        assert detector.detect_stale_leadership() is True
    
    def test_no_stale_leadership_when_has_quorum(self):
        """Test no stale leadership when quorum is maintained."""
        raft = MockRaftLeaderElectionPort(is_elected=True, is_quorum=True)
        detector = SplitBrainDetectorAdapter(raft)
        
        assert detector.detect_stale_leadership() is False
    
    def test_no_stale_leadership_when_not_elected(self):
        """Test no stale leadership when not elected leader."""
        raft = MockRaftLeaderElectionPort(is_elected=False, is_quorum=False)
        detector = SplitBrainDetectorAdapter(raft)
        
        assert detector.detect_stale_leadership() is False
    
    def test_can_commit_writes_only_when_elected_and_has_quorum(self):
        """Test write safety requires both election and quorum."""
        raft = MockRaftLeaderElectionPort(is_elected=True, is_quorum=True)
        detector = SplitBrainDetectorAdapter(raft)
        
        assert detector.can_commit_writes() is True
        
        # Lost quorum
        raft.is_quorum = False
        assert detector.can_commit_writes() is False
        
        # Not elected
        raft.is_elected = False
        raft.is_quorum = True
        assert detector.can_commit_writes() is False


@pytest.mark.unit
class TestSplitBrainCoordinator:
    """Test SplitBrainCoordinator orchestration."""
    
    def test_detects_and_resolves_split_brain(self):
        """Test full split-brain detection and resolution."""
        from litefs.usecases.split_brain_coordinator import (
            SplitBrainCoordinator,
            SplitBrainState,
        )
        from litefs.adapters.conflict_resolution_adapter import (
            ConflictResolutionAdapter,
        )
        from litefs.usecases.failover_coordinator import (
            FailoverCoordinator,
        )
        
        # Setup: stale leadership condition
        raft = MockRaftLeaderElectionPort(is_elected=True, is_quorum=False)
        detector = SplitBrainDetectorAdapter(raft)
        resolver = ConflictResolutionAdapter()
        failover = FailoverCoordinator(leader_election=raft)
        
        coordinator = SplitBrainCoordinator(
            detector=detector,
            resolver=resolver,
            failover=failover,
        )
        
        # Check and resolve
        state = coordinator.check_and_resolve_split_brain()
        
        # Verify resolution
        assert state == SplitBrainState.RESOLVED
        assert failover.state.value == "replica"  # Transitioned to REPLICA
```

---

## Summary: Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `packages/litefs/src/litefs/adapters/ports.py` | Modify | Add 3 new ports |
| `packages/litefs/src/litefs/adapters/__init__.py` | Modify | Export new ports |
| `packages/litefs/src/litefs/domain/exceptions.py` | Modify | Add `SplitBrainDetectedError` |
| `packages/litefs/src/litefs/adapters/split_brain_detector_adapter.py` | Create | Implement `SplitBrainDetectorPort` |
| `packages/litefs/src/litefs/adapters/conflict_resolution_adapter.py` | Create | Implement `ConflictResolutionPort` |
| `packages/litefs/src/litefs/usecases/split_brain_coordinator.py` | Create | Orchestrate detection + resolution |
| `packages/litefs-django/src/litefs_django/middleware.py` | Create/Modify | Health check middleware |
| `tests/core/unit/adapters/test_split_brain_detector_adapter.py` | Create | Unit tests |
| `tests/core/unit/usecases/test_split_brain_coordinator.py` | Create | Use case tests |

Total: ~600 LOC (Phase 1-3), ~200 more for tests and integration

