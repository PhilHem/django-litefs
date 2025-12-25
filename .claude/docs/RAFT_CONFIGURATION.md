# Raft Leader Election Configuration

> Comprehensive guide to configuring Raft-based leader election in litefs-py. Raft is an automatic, distributed consensus algorithm for electing a primary node without external services.

## Table of Contents

1. [Overview](#overview)
2. [Raft Settings Value Objects](#raft-settings-value-objects)
3. [Configuration Parameters](#configuration-parameters)
4. [Factory: `create_raft_leader_election`](#factory-create_raft_leader_election)
5. [3-Node Cluster Example](#3-node-cluster-example)
6. [5-Node Cluster Example](#5-node-cluster-example)
7. [Network Architecture](#network-architecture)
8. [Failover Behavior](#failover-behavior)
9. [Quorum Requirements](#quorum-requirements)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Raft is a distributed consensus algorithm that elects a leader through quorum-based voting. Unlike static leader election (where one node is manually designated), Raft automatically:

- **Elects a leader** when nodes form a quorum
- **Handles failures** by re-electing when the leader becomes unavailable
- **Requires no external services** (no Consul, Etcd, or Fly.io needed)
- **Provides split-brain protection** by requiring quorum for any leadership claim

### When to Use Raft

| Scenario | Recommendation |
|----------|-----------------|
| **Single primary, automatic failover** | Use Raft |
| **Fixed topology (3-5 nodes)** | Use Raft |
| **Complex quorum policies** | Use Raft |
| **Single node, no failover needed** | Use static leader election |
| **Dynamic cluster scaling (adding/removing nodes)** | Raft (manual node addition supported) |

### Architecture in litefs-py

```
┌────────────────────────────────────┐
│  Application (Django/FastAPI)      │
├────────────────────────────────────┤
│  FailoverCoordinator               │
│  (orchestrates transitions)        │
├────────────────────────────────────┤
│  RaftLeaderElectionPort (interface)│
├────────────────────────────────────┤
│  RaftLeaderElection (py-leader)    │
│  (implements Raft consensus)       │
├────────────────────────────────────┤
│  LiteFS                            │
│  (SQLite replication)              │
└────────────────────────────────────┘
```

The `FailoverCoordinator` monitors Raft consensus and transitions the application between PRIMARY (writable) and REPLICA (read-only) states based on leader election outcomes.

---

## Raft Settings Value Objects

Raft configuration is built from two immutable domain value objects defined in `packages/litefs/src/litefs/domain/raft.py`.

### RaftSettings

Encapsulates cluster membership and quorum calculation.

**Attributes:**
- `node_id` (str): Unique identifier for this node in the cluster
  - Must be non-empty, non-whitespace
  - Must be a member of `cluster_members`
- `cluster_members` (tuple[str, ...] | list[str]): All node IDs in the cluster
  - Must be non-empty
  - Must not contain empty or whitespace-only strings
- `quorum_size` (int, calculated): Automatically set to floor(n/2) + 1
  - Ensures majority consensus for any leadership decision

**Invariants:**
- `node_id` must be in `cluster_members`
- `cluster_members` must not be empty
- `quorum_size` is always > n/2 (strict majority)

**Example:**

```python
from litefs.domain.raft import RaftSettings

settings = RaftSettings(
    node_id="node1",
    cluster_members=["node1", "node2", "node3"],
)
# quorum_size is automatically calculated: floor(3/2) + 1 = 2
assert settings.quorum_size == 2
```

### QuorumPolicy

Encapsulates timing parameters for Raft consensus (election timeout and heartbeat interval).

**Attributes:**
- `election_timeout_ms` (int): Milliseconds a follower waits before starting an election
  - Typical range: 300-500ms
  - Must be positive (> 0)
  - Must be greater than `heartbeat_interval_ms`
- `heartbeat_interval_ms` (int): Milliseconds between leader heartbeats
  - Typical range: 50-150ms
  - Must be positive (> 0)
  - Must be less than `election_timeout_ms`

**Invariants:**
- Both timeouts must be positive integers (> 0)
- `heartbeat_interval_ms < election_timeout_ms` (Raft requirement)
- Recommended ratio: 5-10x (e.g., 100ms heartbeat, 500ms election)

**Why This Matters:**

- **Heartbeat interval** is how often the leader sends "I'm alive" messages to all followers
- **Election timeout** is how long followers wait before assuming the leader is dead and starting an election
- If heartbeat is too close to election timeout, network delays can trigger spurious elections
- If heartbeat interval is too long, leader failures take longer to detect

**Example:**

```python
from litefs.domain.raft import QuorumPolicy

# Conservative: slower detection, fewer spurious elections (good for unstable networks)
policy = QuorumPolicy(
    election_timeout_ms=500,
    heartbeat_interval_ms=100,
)

# Aggressive: faster failover, but may cause spurious elections (good for stable networks)
policy = QuorumPolicy(
    election_timeout_ms=300,
    heartbeat_interval_ms=50,
)
```

---

## Configuration Parameters

Raft configuration is specified in `LiteFSSettings` (the main domain entity) and propagates through the framework adapters.

### Core Parameters (litefs-py)

These parameters configure Raft leader election in the `LiteFSSettings` domain entity.

```python
from litefs import LiteFSSettings

settings = LiteFSSettings(
    # Standard parameters
    mount_path="/litefs",
    data_path="/var/lib/litefs",
    database_name="db.sqlite3",
    leader_election="raft",           # Enable Raft (vs. "static")
    proxy_addr="0.0.0.0:8080",
    enabled=True,
    retention="24h",

    # Raft-specific parameters
    raft_self_addr="node1:20202",     # This node's address
    raft_peers=[
        "node2:20202",                # List of peer node addresses
        "node3:20202",
    ],
)
```

**Field Details:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `leader_election` | str | Yes | Must be `"raft"` to enable Raft |
| `raft_self_addr` | str | Yes (for Raft) | Network address of this node (e.g., `"node1:20202"`) |
| `raft_peers` | list[str] | Yes (for Raft) | List of peer addresses; must not be empty |

**Validation Rules:**

- If `leader_election="raft"`:
  - `raft_self_addr` must be non-empty and non-whitespace
  - `raft_peers` must be non-empty (at least one peer)
  - Both fields are required; `LiteFSSettings` will raise `LiteFSConfigError` if missing

---

## Factory: `create_raft_leader_election`

The factory function `create_raft_leader_election` creates a Raft leader election instance from settings.

**Location:** `packages/litefs/src/litefs/factories.py`

**Signature:**

```python
def create_raft_leader_election(
    settings: LiteFSSettings,
    node_id: str,
    election_timeout: float = 5.0,
    heartbeat_interval: float = 1.0,
) -> RaftLeaderElectionPort:
    """Create a RaftLeaderElection instance from LiteFSSettings.

    Args:
        settings: LiteFSSettings configured for Raft leader election.
        node_id: Unique identifier for this node in the cluster.
        election_timeout: Timeout in seconds (default 5.0).
        heartbeat_interval: Interval in seconds (default 1.0).

    Returns:
        A RaftLeaderElectionPort implementation.

    Raises:
        PyLeaderNotInstalledError: If py-leader is not installed.
        ValueError: If settings or timeouts are invalid.
    """
```

**Parameters:**

- `settings`: LiteFSSettings with `leader_election="raft"` and valid `raft_self_addr`, `raft_peers`
- `node_id`: Unique identifier for this node (e.g., hostname, pod name)
  - Must match the node's identity in your cluster
  - Used by the Raft algorithm for consensus
- `election_timeout`: Timeout in seconds (corresponds to `QuorumPolicy.election_timeout_ms` / 1000)
  - Default: 5.0 seconds (5000ms)
  - Must be > `heartbeat_interval`
- `heartbeat_interval`: Interval in seconds (corresponds to `QuorumPolicy.heartbeat_interval_ms` / 1000)
  - Default: 1.0 seconds (1000ms)
  - Must be > 0 and < `election_timeout`

**Returns:**

A `RaftLeaderElectionPort` (the interface) with implementation from `py-leader`:
- `is_leader_elected()`: Returns True if this node is the elected leader
- `elect_as_leader()`: Elect this node as leader
- `demote_from_leader()`: Demote from leadership
- `is_quorum_reached()`: Check if quorum is established
- `get_cluster_members()`: List all node IDs
- `get_election_timeout()`: Get election timeout in seconds

**Raises:**

- `PyLeaderNotInstalledError`: If `py-leader` is not installed (install with `pip install litefs-py[raft]`)
- `ValueError`: If:
  - `settings.leader_election != "raft"`
  - `settings.raft_self_addr` is None or empty
  - `settings.raft_peers` is None or empty
  - `election_timeout <= heartbeat_interval`
  - Either timeout is <= 0
  - `node_id` is not in the cluster members

**Installation Requirement:**

Raft functionality requires the `py-leader` package (optional dependency):

```bash
# Install with Raft support
pip install litefs-py[raft]

# Or install py-leader separately
pip install py-leader
```

---

## 3-Node Cluster Example

A 3-node cluster is the minimum for robust Raft consensus. Quorum requirement: 2 nodes.

### Configuration

**Node 1 (node1):**

```python
from litefs import LiteFSSettings
from litefs.factories import create_raft_leader_election
from litefs.usecases.failover_coordinator import FailoverCoordinator

settings = LiteFSSettings(
    mount_path="/litefs",
    data_path="/var/lib/litefs",
    database_name="db.sqlite3",
    leader_election="raft",
    proxy_addr="0.0.0.0:8080",
    enabled=True,
    retention="24h",
    raft_self_addr="node1:20202",      # This node's address
    raft_peers=["node2:20202", "node3:20202"],
)

# Create leader election with moderate timeouts
election = create_raft_leader_election(
    settings=settings,
    node_id="node1",
    election_timeout=5.0,              # 5 seconds
    heartbeat_interval=1.0,            # 1 second
)

coordinator = FailoverCoordinator(election)
```

**Node 2 (node2):**

```python
settings = LiteFSSettings(
    mount_path="/litefs",
    data_path="/var/lib/litefs",
    database_name="db.sqlite3",
    leader_election="raft",
    proxy_addr="0.0.0.0:8080",
    enabled=True,
    retention="24h",
    raft_self_addr="node2:20202",
    raft_peers=["node1:20202", "node3:20202"],
)

election = create_raft_leader_election(
    settings=settings,
    node_id="node2",
    election_timeout=5.0,
    heartbeat_interval=1.0,
)

coordinator = FailoverCoordinator(election)
```

**Node 3 (node3):**

```python
settings = LiteFSSettings(
    mount_path="/litefs",
    data_path="/var/lib/litefs",
    database_name="db.sqlite3",
    leader_election="raft",
    proxy_addr="0.0.0.0:8080",
    enabled=True,
    retention="24h",
    raft_self_addr="node3:20202",
    raft_peers=["node1:20202", "node2:20202"],
)

election = create_raft_leader_election(
    settings=settings,
    node_id="node3",
    election_timeout=5.0,
    heartbeat_interval=1.0,
)

coordinator = FailoverCoordinator(election)
```

### Django Settings Example

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "litefs_django",
]

DATABASES = {
    "default": {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "default",
    }
}

LITEFS = {
    "MOUNT_PATH": "/litefs",
    "DATA_PATH": "/var/lib/litefs",
    "DATABASE_NAME": "db.sqlite3",
    "LEADER_ELECTION": "raft",
    "RAFT_SELF_ADDR": "node1:20202",        # Set per node
    "RAFT_PEERS": ["node2:20202", "node3:20202"],
    "PROXY_ADDR": "0.0.0.0:8080",
    "ENABLED": True,
    "RETENTION": "24h",
}
```

### Docker Compose Setup

```yaml
version: '3.9'

services:
  node1:
    image: myapp:latest
    hostname: node1
    environment:
      LITEFS_SELF_ADDR: "node1:20202"
      LITEFS_PEERS: "node2:20202,node3:20202"
    ports:
      - "8001:8000"
    networks:
      - litefs-cluster

  node2:
    image: myapp:latest
    hostname: node2
    environment:
      LITEFS_SELF_ADDR: "node2:20202"
      LITEFS_PEERS: "node1:20202,node3:20202"
    ports:
      - "8002:8000"
    networks:
      - litefs-cluster

  node3:
    image: myapp:latest
    hostname: node3
    environment:
      LITEFS_SELF_ADDR: "node3:20202"
      LITEFS_PEERS: "node1:20202,node2:20202"
    ports:
      - "8003:8000"
    networks:
      - litefs-cluster

networks:
  litefs-cluster:
    driver: bridge
```

### Cluster Behavior

| Scenario | Quorum | Result |
|----------|--------|--------|
| All 3 nodes up | 2/3 ✓ | Leader elected; normal operation |
| 1 node down | 2/3 ✓ | Remaining 2 form quorum; leader may change |
| 2 nodes down | 1/3 ✗ | Quorum lost; writes blocked; read-only mode |

---

## 5-Node Cluster Example

A 5-node cluster provides higher availability. Quorum requirement: 3 nodes.

### Configuration

**Environment-based setup (recommended for Kubernetes/Docker):**

```bash
# Set on each pod/container:
LITEFS_SELF_ADDR="node1:20202"
LITEFS_PEERS="node2:20202,node3:20202,node4:20202,node5:20202"
LITEFS_NODE_ID="node1"  # Resolved from hostname or explicit env var
LITEFS_ELECTION_TIMEOUT="5.0"
LITEFS_HEARTBEAT_INTERVAL="1.0"
```

**Python configuration:**

```python
from litefs import LiteFSSettings
from litefs.factories import create_raft_leader_election
from litefs.adapters.ports import EnvironmentNodeIDResolver

settings = LiteFSSettings(
    mount_path="/litefs",
    data_path="/var/lib/litefs",
    database_name="db.sqlite3",
    leader_election="raft",
    proxy_addr="0.0.0.0:8080",
    enabled=True,
    retention="24h",
    raft_self_addr="node1:20202",
    raft_peers=[
        "node2:20202",
        "node3:20202",
        "node4:20202",
        "node5:20202",
    ],
)

# Resolve node_id from environment (LITEFS_NODE_ID)
resolver = EnvironmentNodeIDResolver()
node_id = resolver.resolve_node_id()

# Create election with tuned timeouts for larger cluster
election = create_raft_leader_election(
    settings=settings,
    node_id=node_id,
    election_timeout=10.0,             # Longer timeout for slower convergence
    heartbeat_interval=2.0,
)

coordinator = FailoverCoordinator(election)
```

### Availability Matrix

| Nodes Down | Available | Quorum | Status |
|-----------|-----------|--------|--------|
| 0 | 5/5 | ✓ | Normal; leader elected |
| 1 | 4/5 | ✓ | Leader continues; can tolerate 1 more failure |
| 2 | 3/5 | ✓ | Quorum still reachable |
| 3 | 2/5 | ✗ | Quorum lost; read-only mode |

**Advantage over 3-node:** Can tolerate losing 2 nodes and still maintain quorum (compared to 3-node which can only lose 1).

---

## Network Architecture

Raft requires network connectivity between all cluster nodes for consensus. This section covers network topology, port requirements, and cross-network scenarios.

### Port Mapping

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 20202 | HTTP (Raft) | Node ↔ Node | Raft consensus (py-leader) |
| 8080 | HTTP (LiteFS) | Client → Primary | LiteFS replication proxy |
| 8000 | HTTP (App) | Client → All | Application (Django/FastAPI) |

### Same-Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Private Network (Docker, VPC)            │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐│
│  │    Node 1       │  │     Node 2       │  │   Node 3     ││
│  │  (Primary)      │  │   (Follower)     │  │ (Follower)   ││
│  │                 │  │                  │  │              ││
│  │ Port 20202 ◄────┼──┼─ Port 20202 ◄────┼──┼─ Port 20202  ││
│  │ (Raft)          │  │  (Raft)          │  │  (Raft)      ││
│  └────────┬────────┘  └────────┬─────────┘  └────────┬─────┘│
│           │                    │                     │       │
│           └────────────────────┼─────────────────────┘       │
│                                │                             │
│                   (Heartbeats, Vote Requests)                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↑
                    Load Balancer (nginx)
```

**Configuration:**

- All nodes can reach each other on port 20202
- Use DNS names or static IPs (recommended: use hostnames in Docker/Kubernetes)
- Example: `raft_peers=["node1:20202", "node2:20202", "node3:20202"]`

### Cross-Network Topology (VPN Required)

For nodes in different networks (cloud regions, on-premises + cloud, multiple data centers):

```
┌──────────────────────┐         ┌──────────────────────┐
│   Region A           │         │   Region B           │
│  ┌────────────────┐  │         │  ┌────────────────┐  │
│  │  Node 1        │  │         │  │  Node 2        │  │
│  │ :20202         │  │         │  │ :20202         │  │
│  └────────┬───────┘  │         │  └────────┬───────┘  │
└───────────┼──────────┘         └───────────┼──────────┘
            │                               │
            │      VPN Tunnel (Tailscale)   │
            │<──────────────────────────────>│
            │                               │
            └───────────────────────────────┘
         (Raft heartbeats over VPN)
```

**Setup Steps:**

1. Install [Tailscale](https://tailscale.com/) on all nodes
2. Authorize nodes to join the same Tailscale network
3. Use Tailscale IPs in `raft_self_addr` and `raft_peers`:
   ```python
   settings = LiteFSSettings(
       raft_self_addr="100.65.12.34:20202",  # Tailscale IP
       raft_peers=["100.65.45.67:20202", "100.65.89.01:20202"],
       # ...
   )
   ```
4. Raft consensus works over the VPN as if nodes were on the same network

**Alternative Tools:**

- Tailscale (recommended): Easy, automatic, secure
- WireGuard: Manual but powerful
- SSH tunneling: Last resort, performance overhead

### Kubernetes StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: litefs-cluster
spec:
  serviceName: litefs-cluster
  replicas: 3
  selector:
    matchLabels:
      app: litefs
  template:
    metadata:
      labels:
        app: litefs
    spec:
      containers:
      - name: app
        image: myapp:latest
        env:
        - name: LITEFS_NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: LITEFS_SELF_ADDR
          value: "$(LITEFS_NODE_ID).litefs-cluster.default:20202"
        - name: LITEFS_PEERS
          value: "litefs-cluster-0.litefs-cluster:20202,litefs-cluster-1.litefs-cluster:20202,litefs-cluster-2.litefs-cluster:20202"
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 20202
          name: raft
---
apiVersion: v1
kind: Service
metadata:
  name: litefs-cluster
spec:
  clusterIP: None
  selector:
    app: litefs
  ports:
  - name: http
    port: 8000
  - name: raft
    port: 20202
```

---

## Failover Behavior

The `FailoverCoordinator` orchestrates state transitions based on Raft consensus. This section documents how failover works.

### Steady State (Leader Elected)

```
┌──────────────────────────────────────────┐
│   FailoverCoordinator                    │
│                                          │
│  1. Check leader_election.is_leader()   │
│  2. Update node state (PRIMARY/REPLICA) │
│  3. Quorum check (if available)         │
│  4. Transition if needed                │
└──────────────────────────────────────────┘
         │                    │
         ▼                    ▼
    Node State          Election Status
    (PRIMARY/REPLICA)   (Leader/Follower)
```

### Failover Scenario: Primary Node Dies

```
Time  │  Node 1 (Primary)  │  Node 2 (Follower)  │  Node 3 (Follower)
──────┼────────────────────┼─────────────────────┼────────────────────
t=0   │  Leader elected    │  Following Node 1   │  Following Node 1
      │  Sends heartbeats  │                     │
──────┼────────────────────┼─────────────────────┼────────────────────
t=5s  │  DIES (no response)│  No heartbeat       │  No heartbeat
      │  (network failure) │  Election triggered │  Election triggered
──────┼────────────────────┼─────────────────────┼────────────────────
t=6-8s│  (dead)            │  Becomes leader     │  Acknowledges Node 2
      │                    │  (votes granted)    │  (quorum: 2/3)
──────┼────────────────────┼─────────────────────┼────────────────────
t=8s+ │  (dead)            │  PRIMARY state      │  REPLICA state
      │                    │  LiteFS writes      │  LiteFS reads
──────┴────────────────────┴─────────────────────┴────────────────────
```

### FailoverCoordinator Methods

The coordinator provides methods for application-level failover integration:

```python
from litefs.usecases.failover_coordinator import FailoverCoordinator

coordinator = FailoverCoordinator(election)

# Check state
if coordinator.state == NodeState.PRIMARY:
    # Can write to database
    pass
else:
    # Read-only mode
    pass

# Periodically coordinate transitions (call in polling loop)
coordinator.coordinate_transition()

# Check if node can maintain leadership
if coordinator.can_maintain_leadership():
    # Safe to keep writing
    pass
else:
    # Perform graceful handoff
    coordinator.perform_graceful_handoff()

# Health management
coordinator.mark_unhealthy()  # On disk error, connection loss, etc.
coordinator.mark_healthy()    # When recovered

# Check health
if not coordinator.is_healthy():
    # Node is degraded; demote if needed
    coordinator.perform_graceful_handoff()
```

### Transition Rules

**REPLICA → PRIMARY:**

1. Check: `is_leader_elected() == True` (Raft elected this node)
2. Check: `is_healthy() == True` (node is not degraded)
3. Check: `is_quorum_reached()` (quorum available, if using Raft)
4. If all checks pass: Transition to PRIMARY state

**PRIMARY → REPLICA:**

1. Check: `is_leader_elected() == False` (Raft demoted this node)
2. OR: `is_healthy() == False` (node became unhealthy)
3. If either check fails: Transition to REPLICA state

---

## Quorum Requirements

Quorum is essential to Raft's correctness. A quorum is a strict majority of nodes.

### Quorum Calculation

```
n = cluster size
quorum_size = floor(n / 2) + 1

Examples:
- 3 nodes:  floor(3/2) + 1 = 2 (need 2/3)
- 5 nodes:  floor(5/2) + 1 = 3 (need 3/5)
- 7 nodes:  floor(7/2) + 1 = 4 (need 4/7)
```

### Why Quorum Matters

Quorum prevents split-brain scenarios where multiple nodes claim leadership.

**Example: 3-node cluster, network partition:**

```
Scenario: Partition between Node 1 vs. Nodes 2+3

                    Network Partition
                      │       │
                      │       │
   ┌──────────────┐  │  │  ┌──────────────┐
   │    Node 1    │  │  │  │    Node 2    │
   │ (partitioned)│  │  │  │ (partition)  │
   │              │  │  │  │              │
   │ Has 1 vote   │  │  │  │ Has 2 votes  │
   │ Needs 2      │  │  │  │ Needs 2      │
   │ → REPLICA    │  │  │  │ → PRIMARY    │
   └──────────────┘  │  │  ├──────────────┤
                     │  │  │    Node 3    │
                     │  │  │ (partition)  │
                     │  │  │              │
                     │  │  │ Votes for 2  │
                     │  │  │ → REPLICA    │
                     │  │  └──────────────┘
```

Even though the network is split, quorum ensures **only one leader** (the 2-node partition). Node 1 cannot declare itself leader with only 1 vote (needs 2).

### Quorum Loss Protection

```python
coordinator = FailoverCoordinator(election)

# Check if can continue as leader
if not coordinator.can_maintain_leadership():
    # Quorum lost; demote to prevent writes
    coordinator.perform_graceful_handoff()
```

When quorum is lost:
- `is_quorum_reached()` returns False
- `can_maintain_leadership()` returns False
- Application should demote to read-only mode
- LiteFS blocks writes (primary lease expires without quorum)

---

## Troubleshooting

Common issues and solutions for Raft configuration.

### Issue: "py-leader is not installed"

**Error:**
```
PyLeaderNotInstalledError: py-leader is not installed. Install with: pip install litefs-py[raft]
```

**Solution:**

Install the optional Raft dependency:

```bash
# Option 1: Install litefs-py with raft extra
pip install litefs-py[raft]

# Option 2: Install py-leader directly
pip install py-leader
```

Verify installation:

```python
try:
    from py_leader import RaftLeaderElection
    print("py-leader is installed")
except ImportError:
    print("py-leader is not installed")
```

### Issue: Nodes Can't Reach Each Other

**Symptoms:**
- Quorum never established
- Election repeatedly times out
- No leader elected

**Diagnosis:**

1. Check network connectivity:
   ```bash
   ping node2:20202
   nc -zv node2 20202
   telnet node2 20202
   ```

2. Check firewall rules:
   ```bash
   # On each node, port 20202 must be open
   sudo ufw allow 20202
   # Or in cloud security groups:
   # Allow ingress on 20202 from other node IPs
   ```

3. Check address resolution:
   ```bash
   # In raft_peers, use resolvable names or IPs
   nslookup node2
   nslookup node3
   ```

**Solution:**

- For Docker: Use service names (e.g., `node2:20202`)
- For Kubernetes: Use headless service DNS (e.g., `pod-0.service-name:20202`)
- For cross-network: Use Tailscale IPs or VPN tunnel
- For on-premises: Use static IPs or DNS entries

### Issue: Spurious Elections / Frequent Leader Changes

**Symptoms:**
- Leader elected, then demoted, then re-elected in short bursts
- High log churn
- Timeouts in election logs

**Causes:**

- Heartbeat interval too close to election timeout
- Network latency exceeding heartbeat interval
- High CPU/disk load on nodes

**Solution:**

Increase election timeout and heartbeat interval:

```python
# Current (problematic):
election = create_raft_leader_election(
    settings=settings,
    node_id=node_id,
    election_timeout=1.0,          # Too short
    heartbeat_interval=0.5,         # Too close to election
)

# Fixed:
election = create_raft_leader_election(
    settings=settings,
    node_id=node_id,
    election_timeout=5.0,           # Longer grace period
    heartbeat_interval=1.0,         # 5x ratio
)
```

**Ratio guideline:** `election_timeout >= 5 * heartbeat_interval`

### Issue: Quorum Never Reached

**Symptoms:**
- `is_quorum_reached()` always returns False
- `can_become_leader()` always returns False
- All nodes stuck in REPLICA state

**Causes:**

- Incorrect `raft_self_addr` (doesn't match node's actual address)
- Mismatched cluster members (node thinks cluster is different size)
- Network partition affecting quorum threshold

**Diagnosis:**

```python
from litefs.adapters.ports import RaftLeaderElectionPort

election: RaftLeaderElectionPort  # from create_raft_leader_election

# Check cluster membership
print(f"Cluster members: {election.get_cluster_members()}")
print(f"This node: {node_id}")
print(f"Node is member: {election.is_member_in_cluster(node_id)}")

# Check quorum status
print(f"Quorum reached: {election.is_quorum_reached()}")
```

**Solution:**

- Verify `raft_self_addr` matches the node's actual network address
- Verify all nodes agree on cluster members (same `raft_peers` list + `raft_self_addr`)
- Check network connectivity between nodes
- Ensure port 20202 is open on all nodes

### Issue: Leader Elected But Not Writing

**Symptoms:**

- Node is PRIMARY state
- Leader elected
- But `LiteFS` is in read-only mode
- Writes fail

**Cause:**

LiteFS doesn't know about the Raft leader. The node must write the `.primary` file for LiteFS to recognize it as primary.

**Solution:**

Ensure the application layer is writing the `.primary` file. This is usually handled by an integration adapter (e.g., `litefs-django` management command):

```bash
python manage.py litefs_primary_updater
```

Or implement custom logic:

```python
def update_primary_file():
    if coordinator.state == NodeState.PRIMARY:
        # Write .primary marker file for LiteFS
        with open("/litefs/.primary", "w") as f:
            f.write(node_id)
```

### Issue: Split-Brain Detection

**Symptoms:**

- Multiple nodes report `is_leader_elected() == True`
- Inconsistent state across nodes
- Data corruption warnings

**Causes:**

- Network partition lasting longer than quorum threshold
- Nodes manually reconfigured with different cluster members
- Clock skew (nodes' system clocks too far apart)

**Solution:**

1. Check for network partition:
   ```bash
   ping -c 5 node2
   ping -c 5 node3
   ```

2. Verify all nodes have the same cluster members:
   ```python
   print(election.get_cluster_members())  # Should be identical on all nodes
   ```

3. Check system clocks are synchronized:
   ```bash
   date  # On each node; should be within 1 second
   sudo ntpdate -s time.nist.gov  # Sync if needed
   ```

4. Manual recovery:
   - Identify the minority partition
   - Demote all nodes in the minority partition manually
   - Wait for majority partition leader to stabilize
   - Restore network and let Raft re-converge

---

## References

- **LiteFS Docs**: https://fly.io/docs/litefs/
- **Raft Consensus**: https://raft.github.io/
- **PySyncObj (Raft library)**: https://github.com/bakwc/PySyncObj
- **py-leader (Python wrapper)**: https://pypi.org/project/py-leader/
- **Tailscale (VPN for cross-network)**: https://tailscale.com/

## See Also

- [DEPLOYMENT.md](.claude/docs/DEPLOYMENT.md) - Deployment architecture and networking
- [CONFIGURATION.md](.claude/docs/CONFIGURATION.md) - General settings interface
- [SPLIT_BRAIN_ANALYSIS.md](.claude/docs/SPLIT_BRAIN_ANALYSIS.md) - Split-brain detection and recovery
