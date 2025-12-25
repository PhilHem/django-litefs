# Split-Brain Handling in litefs-py Domain Model

## Executive Summary

Split-brain occurs when network partitions prevent a cluster from maintaining consensus about who the leader is. In LiteFS with Raft, this results in multiple nodes believing they can accept writes—violating the fundamental "single primary" invariant.

**Recommendation**: Implement split-brain detection as a **domain-level concern** with:

1. **New Domain Value Objects**: `RaftNodeState`, `RaftClusterState`
2. **New Domain Event**: `SplitBrainDetectedEvent`
3. **New Application Service**: `SplitBrainDetector` use case
4. **Port Extension**: Add `get_cluster_state()` and `detect_split_brain()` methods to `RaftLeaderElectionPort`
5. **Behavioral Strategy**: Conservative detection + framework-level recovery (no auto-recovery in domain)

This keeps the domain pure, enables testability, and allows framework adapters (Django, FastAPI) to implement recovery strategies appropriate to their context.

---

## 1. Current Domain Model Gap Analysis

### Existing Layer: Configuration (Static)

| Component | Location | Scope |
|-----------|----------|-------|
| `LiteFSSettings` | `domain/settings.py` | Global configuration (mount paths, database name) |
| `RaftConfig` | `domain/settings.py` | Peer discovery (self_addr, peers list) |
| `RaftSettings` | `domain/raft.py` | Cluster topology (node_id, members, quorum size) |
| `QuorumPolicy` | `domain/raft.py` | Election timing (heartbeat interval, election timeout) |

### Existing Layer: Health (Node-Level)

| Component | Location | Scope |
|-----------|----------|-------|
| `HealthStatus` | `domain/health.py` | Single node health (healthy/unhealthy/degraded) |
| `PrimaryDetector` | `usecases/` | Is this node primary? (checks .primary file) |

### Gap: Runtime Cluster State (Missing)

**What's missing**: A domain model that captures *runtime observations* about the cluster:
- Which nodes believe they are the leader?
- Are multiple nodes claiming leadership?
- Has quorum been lost?
- Has a network partition been detected?

**Why it matters**: Split-brain is fundamentally a **runtime state problem**—a validly-configured cluster can disagree about leadership due to network issues. Configuration alone cannot detect or prevent this.

---

## 2. Proposed Domain Model

### New Value Objects

#### `RaftNodeState` - One node's self-view

```python
@dataclass(frozen=True)
class RaftNodeState:
    """One node's awareness of its role in the cluster.
    
    Represents what a single node believes about itself:
    - Is it the leader?
    - What election term is it in?
    - When was the last heartbeat from the leader?
    
    Invariants (enforced in __post_init__):
    - node_id: non-empty, non-whitespace
    - election_term: >= 0
    - If believes_is_leader=True: last_heartbeat_ts must be None
      (a leader doesn't receive heartbeats from itself)
    """
    node_id: str
    believes_is_leader: bool
    election_term: int = 0
    last_heartbeat_ts: float | None = None
```

#### `RaftClusterState` - Aggregated cluster view

```python
@dataclass(frozen=True)
class RaftClusterState:
    """Snapshot of all nodes' leadership beliefs at one moment.
    
    Aggregates observations from all nodes to determine:
    - How many nodes claim to be leader?
    - Has the cluster reached quorum?
    - Is a split-brain condition present?
    
    Computed properties:
    - leaders_detected: Tuple of node IDs claiming leadership
    - has_split_brain: True if len(leaders_detected) > 1
    - is_leaderless: True if len(leaders_detected) == 0
    
    Invariants:
    - cluster_members must be non-empty
    - quorum_size must be valid for cluster size
    - All leaders must be in cluster_members
    """
    cluster_members: dict[str, RaftNodeState]
    quorum_size: int
    is_partitioned: bool = False
```

**Key insight**: These are **immutable snapshots**, not mutable entities. They represent observations at a point in time, enabling clear history and event-driven logic.

### New Domain Event

#### `SplitBrainDetectedEvent` - Observable fact

```python
@dataclass(frozen=True)
class SplitBrainDetectedEvent:
    """Domain event: multiple leaders detected simultaneously.
    
    Signals a concrete, observable failure: at time T, nodes X and Y
    both claimed to be the leader. This violates the cluster invariant.
    
    Attributes:
    - detected_at: ISO 8601 timestamp
    - cluster_state: Snapshot of cluster at detection time
    - detected_by_node: Which node detected this?
    - conflicting_leaders: Tuple of claimant node IDs
    
    Invariants:
    - len(conflicting_leaders) >= 2
    - detected_by_node must be in cluster_members
    """
    detected_at: str
    cluster_state: RaftClusterState
    detected_by_node: str
    conflicting_leaders: tuple[str, ...]
```

---

## 3. Integration with Existing Domain Model

### Configuration vs. Runtime State

```
LiteFSSettings (CONFIGURATION - What nodes *should* exist)
  ├── leader_election: "static" | "raft"
  ├── raft_config: RaftConfig (peer discovery)
  │   └── peers: ["node-a:20202", "node-b:20202"]
  └── raft_settings: RaftSettings (immutable cluster metadata)
      └── cluster_members: ("node-a", "node-b", "node-c")

RaftClusterState (RUNTIME - What nodes *actually* believe)
  └── cluster_members:
      ├── "node-a" → RaftNodeState(believes_is_leader=True, term=5)
      ├── "node-b" → RaftNodeState(believes_is_leader=True, term=5)  ← CONFLICT
      └── "node-c" → RaftNodeState(believes_is_leader=False, term=4)
```

### Relationship to Existing Use Cases

```
FailoverCoordinator (existing)
  └── coordinate_transition()
      ├── Current logic:
      │   - leader_election.is_leader_elected() → bool
      │   - Update state: PRIMARY or REPLICA
      │
      └── Future logic (with split-brain awareness):
          - Also check: leader_election.detect_split_brain()
          - If split-brain → Emit SplitBrainDetectedEvent
          - Don't transition if conflicted

PrimaryDetector (existing)
  └── is_primary() → bool (checks .primary file)
      └── Could validate agreement:
          "I believe I'm leader AND .primary exists"
          OR: "I don't believe I'm leader AND .primary doesn't exist"
          Disagreement → SplitBrainDetectedEvent

HealthStatus (existing)
  └── Orthogonal concern (node is healthy vs. cluster consensus broken)
      A healthy node can still be in a split-brain condition
```

---

## 4. Port Extension: RaftLeaderElectionPort

Extend the existing port with cluster state queries:

```python
@runtime_checkable
class RaftLeaderElectionPort(LeaderElectionPort, Protocol):
    """Extended with cluster state and split-brain detection."""
    
    # Existing methods (unchanged)
    def is_leader_elected(self) -> bool: ...
    def elect_as_leader(self) -> None: ...
    def demote_from_leader(self) -> None: ...
    def get_cluster_members(self) -> list[str]: ...
    def is_quorum_reached(self) -> bool: ...
    
    # NEW METHODS
    def get_cluster_state(self) -> RaftClusterState:
        """Get current cluster state (all nodes' beliefs).
        
        Returns:
            RaftClusterState with RaftNodeState for each cluster member.
            
        Raises:
            RaftError: If cluster state cannot be determined.
        """
        ...
    
    def detect_split_brain(self) -> SplitBrainDetectedEvent | None:
        """Detect split-brain condition.
        
        Returns None if no split-brain (0 or 1 leader).
        Returns SplitBrainDetectedEvent if multiple leaders detected.
        
        Returns:
            SplitBrainDetectedEvent if split-brain, None otherwise.
        """
        ...
```

**Why extend instead of create new port?**
- Single responsibility: all Raft-related queries in one place
- Backwards compatible: implementations can return None for new methods initially
- Clear dependency: "If using Raft, you get split-brain detection"

---

## 5. New Application Service: SplitBrainDetector

```python
class SplitBrainDetector:
    """Use case: Detect split-brain conditions in Raft cluster.
    
    This is a DETECTION service, not a RECOVERY service.
    It observes and reports split-brain conditions;
    framework adapters decide what to do (abort writes, demote, alert ops).
    
    Dependency: RaftLeaderElectionPort (for querying cluster state)
    
    Thread safety: Reads only from port; stateless query interface.
    """
    
    def __init__(self, leader_election: RaftLeaderElectionPort) -> None:
        self.leader_election = leader_election
        self._last_split_brain: SplitBrainDetectedEvent | None = None
    
    def check(self) -> SplitBrainDetectedEvent | None:
        """Check current cluster for split-brain condition.
        
        Returns:
            SplitBrainDetectedEvent if split-brain detected, None otherwise.
        """
        event = self.leader_election.detect_split_brain()
        if event:
            self._last_split_brain = event
        return event
    
    def has_resolved(self) -> bool:
        """Check if previously-detected split-brain has resolved.
        
        Useful for implementing recovery workflows:
        "We detected split-brain at T1. Has it resolved by T2?"
        
        Returns:
            True if split-brain previously detected but now resolved.
        """
        if not self._last_split_brain:
            return False
        
        current_state = self.leader_election.get_cluster_state()
        return len(current_state.leaders_detected) <= 1
```

**Usage pattern** (domain layer):

```python
detector = SplitBrainDetector(raft_port)
event = detector.check()

if event:
    # Framework adapter will handle recovery
    emit(event)
    log.warning(f"Split-brain: leaders={event.conflicting_leaders}")
```

**Recovery moved to adapters** (framework layer):

```python
# litefs_django/management/commands/recover_split_brain.py

def handle(self):
    detector = SplitBrainDetector(raft_port)
    event = detector.check()
    
    if event:
        # Django-specific recovery: demote all but majority
        demote_minority_leaders(event.conflicting_leaders)
        self.stdout.write("Split-brain recovery initiated")
```

---

## 6. Minimal Implementation Path

### Step 1: Add Domain Value Objects

**File**: `/Users/philipphematty/Projects/django-litefs/packages/litefs/src/litefs/domain/raft_state.py` (NEW)

```python
"""Raft runtime state domain value objects."""

from dataclasses import dataclass
from litefs.domain.exceptions import LiteFSConfigError

@dataclass(frozen=True)
class RaftNodeState:
    """Single node's view of its leadership role."""
    node_id: str
    believes_is_leader: bool
    election_term: int = 0
    last_heartbeat_ts: float | None = None
    
    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.strip():
            raise LiteFSConfigError("node_id cannot be empty")
        if self.election_term < 0:
            raise LiteFSConfigError("election_term must be non-negative")
        if self.believes_is_leader and self.last_heartbeat_ts is not None:
            raise LiteFSConfigError(
                "Leader node cannot have last_heartbeat_ts"
            )

@dataclass(frozen=True)
class RaftClusterState:
    """Aggregate cluster state snapshot."""
    cluster_members: dict[str, RaftNodeState]
    quorum_size: int
    is_partitioned: bool = False
    
    @property
    def leaders_detected(self) -> tuple[str, ...]:
        """Node IDs claiming leadership."""
        return tuple(
            node_id for node_id, state in self.cluster_members.items()
            if state.believes_is_leader
        )
    
    @property
    def has_split_brain(self) -> bool:
        """True if multiple leaders detected."""
        return len(self.leaders_detected) > 1
    
    @property
    def is_leaderless(self) -> bool:
        """True if no leader detected."""
        return len(self.leaders_detected) == 0
    
    def __post_init__(self) -> None:
        if not self.cluster_members:
            raise LiteFSConfigError("cluster_members cannot be empty")
        if self.quorum_size <= 0 or self.quorum_size > len(self.cluster_members):
            raise LiteFSConfigError("Invalid quorum_size")
```

**Effort**: ~50 lines of code, 20 minutes

### Step 2: Add Domain Event

**File**: `/Users/philipphematty/Projects/django-litefs/packages/litefs/src/litefs/domain/events.py` (NEW)

```python
"""Domain events for cluster state changes."""

from dataclasses import dataclass
from litefs.domain.raft_state import RaftClusterState
from litefs.domain.exceptions import LiteFSConfigError

@dataclass(frozen=True)
class SplitBrainDetectedEvent:
    """Multiple nodes claim leadership simultaneously."""
    detected_at: str  # ISO 8601
    cluster_state: RaftClusterState
    detected_by_node: str
    
    @property
    def conflicting_leaders(self) -> tuple[str, ...]:
        """Node IDs claiming leadership."""
        return self.cluster_state.leaders_detected
    
    def __post_init__(self) -> None:
        if len(self.conflicting_leaders) < 2:
            raise LiteFSConfigError(
                "SplitBrainDetectedEvent requires >=2 conflicting leaders"
            )
        if self.detected_by_node not in self.cluster_state.cluster_members:
            raise LiteFSConfigError(
                f"detected_by_node '{self.detected_by_node}' not in cluster"
            )
```

**Effort**: ~30 lines of code, 15 minutes

### Step 3: Extend RaftLeaderElectionPort

**File**: Update `/Users/philipphematty/Projects/django-litefs/packages/litefs/src/litefs/adapters/ports.py`

Add methods to `RaftLeaderElectionPort`:

```python
def get_cluster_state(self) -> RaftClusterState:
    """Get current cluster state including all node beliefs.
    
    Returns a snapshot of what each node believes about leadership,
    enabling split-brain detection.
    
    Returns:
        RaftClusterState with all nodes' leadership beliefs.
        
    Raises:
        RaftError: If cluster state cannot be determined.
    """
    ...

def detect_split_brain(self) -> SplitBrainDetectedEvent | None:
    """Detect if split-brain condition exists.
    
    Returns None if no split-brain (0 or 1 leader).
    Returns SplitBrainDetectedEvent if multiple leaders detected.
    
    Returns:
        SplitBrainDetectedEvent if split-brain detected, None otherwise.
    """
    ...
```

**Effort**: ~10 lines of code, 10 minutes

### Step 4: Create SplitBrainDetector Use Case

**File**: `/Users/philipphematty/Projects/django-litefs/packages/litefs/src/litefs/usecases/split_brain_detector.py` (NEW)

```python
"""Split-brain detection use case."""

from litefs.adapters.ports import RaftLeaderElectionPort
from litefs.domain.events import SplitBrainDetectedEvent

class SplitBrainDetector:
    """Use case: Detect split-brain in Raft cluster.
    
    Polls cluster state and identifies when multiple nodes claim
    leadership (split-brain condition). This is detection only;
    recovery strategies are implemented by framework adapters.
    """
    
    def __init__(self, leader_election: RaftLeaderElectionPort) -> None:
        self.leader_election = leader_election
        self._last_split_brain: SplitBrainDetectedEvent | None = None
    
    def check(self) -> SplitBrainDetectedEvent | None:
        """Check for split-brain condition.
        
        Returns:
            SplitBrainDetectedEvent if detected, None otherwise.
        """
        event = self.leader_election.detect_split_brain()
        if event:
            self._last_split_brain = event
        return event
    
    def has_resolved(self) -> bool:
        """Check if previous split-brain has resolved.
        
        Returns:
            True if split-brain previously detected but now resolved.
        """
        if not self._last_split_brain:
            return False
        
        current_state = self.leader_election.get_cluster_state()
        return len(current_state.leaders_detected) <= 1
```

**Effort**: ~40 lines of code, 20 minutes

### Step 5: Write Unit Tests

**File**: `tests/core/unit/usecases/test_split_brain_detector.py` (NEW)

```python
import pytest
from unittest.mock import Mock
from litefs.domain.raft_state import RaftNodeState, RaftClusterState
from litefs.domain.events import SplitBrainDetectedEvent
from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs.adapters.ports import RaftLeaderElectionPort

@pytest.mark.unit
class TestSplitBrainDetector:
    
    def test_detects_multiple_leaders(self):
        """Detector identifies multiple leaders."""
        # Arrange
        node_a = RaftNodeState("node-a", believes_is_leader=True)
        node_b = RaftNodeState("node-b", believes_is_leader=True)
        
        cluster_state = RaftClusterState(
            cluster_members={"node-a": node_a, "node-b": node_b},
            quorum_size=1,
        )
        
        event = SplitBrainDetectedEvent(
            detected_at="2025-01-01T00:00:00Z",
            cluster_state=cluster_state,
            detected_by_node="node-a",
        )
        
        mock_port = Mock(spec=RaftLeaderElectionPort)
        mock_port.detect_split_brain.return_value = event
        
        detector = SplitBrainDetector(mock_port)
        
        # Act
        result = detector.check()
        
        # Assert
        assert result is not None
        assert result.cluster_state.has_split_brain
        assert len(result.conflicting_leaders) == 2
    
    def test_returns_none_for_healthy_cluster(self):
        """No event for single leader."""
        mock_port = Mock(spec=RaftLeaderElectionPort)
        mock_port.detect_split_brain.return_value = None
        
        detector = SplitBrainDetector(mock_port)
        
        assert detector.check() is None
    
    def test_tracks_resolution(self):
        """Detects when split-brain resolves."""
        # First check: split-brain detected
        event = SplitBrainDetectedEvent(
            detected_at="2025-01-01T00:00:00Z",
            cluster_state=RaftClusterState(
                cluster_members={
                    "node-a": RaftNodeState("node-a", True),
                    "node-b": RaftNodeState("node-b", True),
                },
                quorum_size=1,
            ),
            detected_by_node="node-a",
        )
        
        mock_port = Mock(spec=RaftLeaderElectionPort)
        mock_port.detect_split_brain.return_value = event
        
        detector = SplitBrainDetector(mock_port)
        detector.check()
        
        # Second check: split-brain resolved
        resolved_state = RaftClusterState(
            cluster_members={
                "node-a": RaftNodeState("node-a", True),
                "node-b": RaftNodeState("node-b", False),
            },
            quorum_size=1,
        )
        mock_port.get_cluster_state.return_value = resolved_state
        
        assert detector.has_resolved()
```

**Effort**: ~80 lines of code, 30 minutes

### Step 6: Update Exports

**File**: Update `/Users/philipphematty/Projects/django-litefs/packages/litefs/src/litefs/domain/__init__.py`

```python
from litefs.domain.raft_state import RaftNodeState, RaftClusterState
from litefs.domain.events import SplitBrainDetectedEvent

__all__ = [
    # Existing exports
    "LiteFSSettings",
    "StaticLeaderConfig",
    "LiteFSConfigError",
    "HealthStatus",
    # New exports
    "RaftNodeState",
    "RaftClusterState",
    "SplitBrainDetectedEvent",
]
```

**Effort**: ~5 lines, 5 minutes

---

## 7. Total Implementation Effort

| Component | Lines | Time |
|-----------|-------|------|
| raft_state.py (value objects) | 50 | 20 min |
| events.py (domain event) | 30 | 15 min |
| ports.py (extend port) | 10 | 10 min |
| split_brain_detector.py (use case) | 40 | 20 min |
| test_split_brain_detector.py (tests) | 80 | 30 min |
| __init__.py (exports) | 5 | 5 min |
| **TOTAL** | **215** | **2 hours** |

---

## 8. Upgrade Paths (Trigger-Based)

### Path A: Persistent Event Log (When: Need to audit incidents)

**Trigger**: "We want to track all split-brain events for analysis and SLA tracking"

**Implementation**:
1. Define port: `SplitBrainEventRepository`
2. Django adapter: Implement with Django ORM logging
3. Inject into `SplitBrainDetector`

**Effort**: 1-2 hours

### Path B: Automatic Recovery (When: Observed split-brain requiring action)

**Trigger**: "Production hit split-brain, need to automatically demote conflicting leaders"

**Implementation**:
1. Define port: `SplitBrainRecoveryStrategy`
2. Extend `SplitBrainDetector` to support optional recovery
3. Django adapter: Implement strategy using `raft_port.demote_from_leader()`

**Effort**: 2-3 hours

### Path C: Observability Integration (When: Need real-time alerting)

**Trigger**: "Want Prometheus/Grafana dashboards for split-brain incidents"

**Implementation**:
1. Emit metrics in event handler
2. Django management command: Poll detector, emit metrics
3. FastAPI: Health endpoint that includes split-brain status

**Effort**: 2-4 hours

---

## 9. Key Architectural Principles

### Clean Architecture Preserved

- Domain value objects: **Zero external dependencies**
- Ports: Defined in adapters layer, implemented by infrastructure
- Use cases: Know about ports, not implementations
- Framework adapters: Implement ports, handle recovery

### Hexagonal Architecture Preserved

```
┌──────────────────────────────────────────┐
│ Framework (Django/FastAPI)               │
│ ├─ Recovery handlers                     │
│ ├─ Observability hooks                   │
│ └─ Management commands                   │
├──────────────────────────────────────────┤
│ Application (Use Cases)                  │
│ ├─ SplitBrainDetector (NEW)              │
│ ├─ FailoverCoordinator (existing)        │
│ └─ PrimaryDetector (existing)            │
├──────────────────────────────────────────┤
│ Domain (Value Objects & Events)          │
│ ├─ RaftNodeState (NEW)                   │
│ ├─ RaftClusterState (NEW)                │
│ ├─ SplitBrainDetectedEvent (NEW)         │
│ ├─ LiteFSSettings (existing)             │
│ └─ HealthStatus (existing)               │
├──────────────────────────────────────────┤
│ Adapters (Ports)                         │
│ ├─ RaftLeaderElectionPort (extended)    │
│ └─ SplitBrainEventRepository (optional)  │
└──────────────────────────────────────────┘
```

### Concurrency at the Edge

- Domain layer: **Synchronous, stateless queries**
- Edge layer: **Async polling, event handling, recovery orchestration**

---

## 10. Next Steps

1. **Review** this analysis with the team
2. **Implement** Steps 1-6 above (minimal 2-hour task)
3. **Test** with unit tests (included in Step 5)
4. **Document** in CLAUDE.md (reference this analysis)
5. **Create tasks**:
   - TASK-RAFT-004: Implement `get_cluster_state()` in py-leader adapter
   - TASK-RAFT-005: Integrate `SplitBrainDetector` into FailoverCoordinator
6. **Defer** recovery/observability until trigger observed in production

---

## References

- Clean Architecture: Robert C. Martin
- Domain-Driven Design: Eric Evans
- Raft Consensus: Ongaro & Ousterhout, https://raft.github.io/
- LiteFS Docs: https://fly.io/docs/litefs/
