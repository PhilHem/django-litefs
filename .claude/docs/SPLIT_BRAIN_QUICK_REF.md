# Split-Brain Handling: Quick Reference

## Port Summary

| Port | Location | Key Methods | Responsibility |
|------|----------|-------------|-----------------|
| **SplitBrainDetectorPort** | `adapters/ports.py` | `has_quorum()`, `detect_stale_leadership()`, `last_heartbeat_from()` | Detect partition conditions |
| **ConflictResolutionPort** | `adapters/ports.py` | `fence_write_access()`, `apply_resolution_strategy()` | Block writes, apply recovery |
| **HealthStatePort** | `adapters/ports.py` | `get_health_status()`, `update_health()` | Report node health to cluster |

## Adapter Summary

| Adapter | Location | Ports Implemented | Ports Depends On |
|---------|----------|------------------|-----------------|
| **SplitBrainDetectorAdapter** | `adapters/split_brain_detector_adapter.py` | `SplitBrainDetectorPort` | `RaftLeaderElectionPort`, `NodeIDResolverPort` |
| **ConflictResolutionAdapter** | `adapters/conflict_resolution_adapter.py` | `ConflictResolutionPort` | None (direct LiteFS mount access) |

## Use Case Summary

| Use Case | Location | Dependencies | Responsibility |
|----------|----------|--------------|-----------------|
| **SplitBrainCoordinator** | `usecases/split_brain_coordinator.py` | `SplitBrainDetectorPort`, `ConflictResolutionPort`, `FailoverCoordinator` | Orchestrate detection → resolution → failover |

## Data Flow

```
1. Application calls SplitBrainCoordinator.check_and_resolve_split_brain()
   ↓
2. Coordinator queries SplitBrainDetectorPort.detect_stale_leadership()
   ↓
3. Detector queries RaftLeaderElectionPort.is_quorum_reached()
   ↓
4. If stale: Coordinator calls ConflictResolutionPort.fence_write_access()
   ↓
5. Coordinator calls FailoverCoordinator.leader_election.demote_from_leader()
   ↓
6. Failover Coordinator transitions node to REPLICA state
```

## File Structure (After Implementation)

```
packages/litefs/src/litefs/
├── domain/
│   └── exceptions.py (add: SplitBrainDetectedError)
│
├── adapters/
│   ├── ports.py (add: SplitBrainDetectorPort, ConflictResolutionPort, HealthStatePort)
│   ├── __init__.py (export new ports)
│   ├── split_brain_detector_adapter.py (new)
│   └── conflict_resolution_adapter.py (new)
│
├── usecases/
│   └── split_brain_coordinator.py (new)
```

## Minimal Implementation Checklist

- [ ] Phase 1: Add 3 ports to `adapters/ports.py`
- [ ] Phase 1: Export ports in `adapters/__init__.py`
- [ ] Phase 1: Add `SplitBrainDetectedError` to `domain/exceptions.py`
- [ ] Phase 2: Create `SplitBrainDetectorAdapter` (queries existing `RaftLeaderElectionPort`)
- [ ] Phase 2: Create `ConflictResolutionAdapter` (basic file-based fencing)
- [ ] Phase 3: Create `SplitBrainCoordinator` use case
- [ ] Phase 3: Integrate into health check (Django middleware or background task)
- [ ] Phase 4 (Optional): Add unit tests + integration tests

## Integration Points

### With RaftLeaderElectionPort

```python
# Adapter depends on existing port
raft_port = RaftLeaderElectionAdapter(py_leader_impl)

detector = SplitBrainDetectorAdapter(raft_port)
# detector.has_quorum() → raft_port.is_quorum_reached()
```

### With FailoverCoordinator

```python
# Use case orchestrates with existing use case
failover = FailoverCoordinator(raft_port)

coordinator = SplitBrainCoordinator(
    detector=detector,
    resolver=resolver,
    failover=failover
)
# coordinator.check_and_resolve_split_brain()
# → if stale: failover.coordinate_transition()
```

## No Breaking Changes

Existing code continues to work unchanged:

```python
# Old code (still works)
failover = FailoverCoordinator(raft_adapter)
failover.coordinate_transition()

# New code (optional)
coordinator = SplitBrainCoordinator(detector, resolver, failover)
coordinator.check_and_resolve_split_brain()
```

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Port or Concrete Class? | **Port** | Allows multiple implementations, testable |
| Sync or Async? | **Sync** | Matches existing architecture, called from sync middleware |
| When to call? | **Health check** | Every request or periodic task, not in data path |
| Where to fence? | **LiteFS mount** | Move/delete `.primary` file prevents LiteFS writes |
| Error handling? | **Log + continue** | Fencing is defensive; errors don't cascade |

## Testing Each Layer

### Unit (no external deps)

```python
# MockRaftLeaderElectionPort
detector = SplitBrainDetectorAdapter(mock_raft)
assert detector.detect_stale_leadership() == True  # when elected + no quorum
```

### Property-Based (Hypothesis)

```python
# Test consistency across random state sequences
@given(elected=st.booleans(), quorum=st.booleans())
def test_stale_leadership_logic(elected, quorum):
    # Verify logic: stale = elected AND NOT quorum
```

### Integration (Docker, 3 nodes)

```bash
# Simulate partition, verify fencing prevents conflicts
docker-compose up
iptables -I FORWARD -d node2 -j DROP  # Partition node1
assert not node1.can_write  # Fenced
assert node2.can_write      # Quorum intact
```

