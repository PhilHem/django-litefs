# Split-Brain Handling Architecture Analysis

This directory contains a complete architectural analysis of how graceful split-brain handling fits into the litefs-py hexagonal architecture.

## Quick Start

1. **Start here**: [SPLIT_BRAIN_ANALYSIS.md](SPLIT_BRAIN_ANALYSIS.md)
   - Comprehensive design rationale
   - Architecture overview
   - Port contracts and integration patterns
   - 15-minute read for high-level understanding

2. **Visual reference**: [SPLIT_BRAIN_ARCHITECTURE_DIAGRAM.txt](SPLIT_BRAIN_ARCHITECTURE_DIAGRAM.txt)
   - ASCII architecture diagrams
   - Layer structure (Domain → Application → Adapters → Infrastructure)
   - Call sequences and split-brain scenarios

3. **Quick reference**: [SPLIT_BRAIN_QUICK_REF.md](SPLIT_BRAIN_QUICK_REF.md)
   - Port and adapter summary tables
   - File structure after implementation
   - Implementation checklist
   - Key decisions

4. **Implementation guide**: [SPLIT_BRAIN_CODE_EXAMPLES.md](SPLIT_BRAIN_CODE_EXAMPLES.md)
   - Concrete code for all phases
   - Phase 1: Port definitions
   - Phase 2: Adapter implementations
   - Phase 3: Use case and middleware
   - Phase 4: Unit and integration tests

## Key Findings

**Problem**: Network partitions can cause split-brain, where multiple nodes think they're the leader, leading to data corruption.

**Solution**: Three new ports + two adapters + one use case to detect and fence split-brain conditions.

**Impact**: 
- 550 lines of code
- 6-10 hours of implementation (Phase 1-3)
- Zero breaking changes (opt-in feature)
- Very low risk (defensive pattern)

## Architecture at a Glance

```
Split-Brain Solution = 3 Ports + 2 Adapters + 1 Use Case

Port 1: SplitBrainDetectorPort
├─ Adapter: SplitBrainDetectorAdapter
└─ Queries existing RaftLeaderElectionPort

Port 2: ConflictResolutionPort
├─ Adapter: ConflictResolutionAdapter
└─ Fences write access at LiteFS mount level

Port 3: HealthStatePort
├─ Adapter: HealthStateAdapter (future)
└─ Reports node health to Raft consensus

Use Case: SplitBrainCoordinator
├─ Detects stale leadership
├─ Fences writes
├─ Demotes from Raft leader
└─ Transitions application state (REPLICA)
```

## Files to Create/Modify

**Phase 1-3 Minimal Implementation**:

| File | Action | LOC |
|------|--------|-----|
| `adapters/ports.py` | Add 3 ports | +150 |
| `adapters/split_brain_detector_adapter.py` | New | +80 |
| `adapters/conflict_resolution_adapter.py` | New | +120 |
| `usecases/split_brain_coordinator.py` | New | +120 |
| `domain/exceptions.py` | Add exception | +10 |
| `litefs_django/middleware.py` | New | +80 |

**Total: ~550 LOC**

## Integration with Existing Code

**No changes to**:
- Domain layer
- Existing ports or adapters
- FailoverCoordinator
- Database backend

**Integration points**:
- SplitBrainDetectorAdapter → queries RaftLeaderElectionPort
- SplitBrainCoordinator → uses FailoverCoordinator
- Django middleware → hooks into request cycle

**No breaking changes**: Feature is opt-in via configuration

## Testing Strategy

1. **Unit tests** (no external deps)
   - Mock RaftLeaderElectionPort
   - Test detection logic: stale = elected AND NOT quorum
   - Test adapter idempotence

2. **Property-based tests** (Hypothesis)
   - Random election + quorum states
   - Verify detection logic consistency

3. **Integration tests** (Docker Compose, optional)
   - 3-node cluster
   - Network partition simulation
   - Verify fencing prevents conflicts

## Deployment

**For existing apps**:
1. No action required
2. Feature is opt-in: `LITEFS["DETECT_SPLIT_BRAIN"] = True`
3. Middleware runs on every Nth request
4. Logs CRITICAL when split-brain detected

**Monitoring**:
- Metrics: `litefs_split_brain_detected`, `litefs_quorum_lost`, `litefs_node_fenced`
- Alerts: Page on split-brain detection (data at risk)

## How It Works

```
HTTP Request
  ↓
Django Middleware (every N requests)
  └─ coordinator.check_and_resolve_split_brain()
  ↓
1. Detect stale leadership
   ├─ raft_port.is_leader_elected() → True
   └─ raft_port.is_quorum_reached() → False
2. Fence write access
   └─ Move .primary file (LiteFS checks this)
3. Demote from leadership
   └─ Raft consensus: step down
4. Transition state
   └─ PRIMARY → REPLICA
  ↓
Application continues as read-only replica
```

## Clean Architecture Compliance

Verified against the Clean Architecture dependency rule:

```
Domain (zero external imports)
  ↑ uses (doesn't know about adapters)
Application (SplitBrainCoordinator)
  ↑ uses (only depends on ports)
Adapters (new ports + implementations)
  ↑ uses (can import py-leader, LiteFS, Django)
Infrastructure (py-leader, LiteFS, Django)
```

All dependencies point inward only. No dependency inversions.

## Next Steps

1. **Review** this analysis (15 minutes)
2. **Prioritize** implementation phases
3. **Start Phase 1**: Add 3 ports to `adapters/ports.py`
4. **Add Phase 2**: Create 2 adapters
5. **Complete Phase 3**: Use case + middleware
6. **Optional Phase 4**: Tests and observability

## References

- LiteFS Docs: https://fly.io/docs/litefs/
- py-leader (Raft): https://github.com/bakwc/PySyncObj
- Clean Architecture: *Clean Architecture* by Robert C. Martin

---

**Analysis Date**: 2025-12-25
**Project**: django-litefs (litefs-py core)
**Status**: Ready for implementation
