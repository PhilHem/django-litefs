# Target Deployment Architecture

```
                   ┌─────────────────┐
                   │  Load Balancer  │
                   │  (nginx/traefik)│
                   └────────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Container 1   │ │   Container 2   │ │   Container 3   │
│   (Primary)     │ │   (Replica)     │ │   (Replica)     │
│                 │ │                 │ │                 │
│ LiteFS :8080 ───┼─│ LiteFS :8080 ───┼─│ LiteFS :8080    │
│   ↓ (proxy)     │ │   ↓ (proxy)     │ │   ↓ (proxy)     │
│ Django :8000    │ │ Django :8000    │ │ Django :8000    │
│   ↓             │ │   ↓             │ │   ↓             │
│ /litefs/db ◄────┼─┼───────◄─────────┼─┼───────◄────────│
│ (read/write)    │ │ (read-only)     │ │ (read-only)     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
        │
        └──── Writes replicated to all replicas ──────┘
```

## Key Points

- LiteFS proxy handles write forwarding automatically
- Load balancer can hit any node; writes forwarded to primary
- Single primary holds write lease; replicas sync asynchronously
- No Kubernetes required—works with Docker Compose, VMs, or bare metal

## Leader Election (V2: Embedded Raft)

No external services required. Uses PySyncObj for Raft consensus:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Container 1   │     │   Container 2   │     │   Container 3   │
│                 │     │                 │     │                 │
│  Django + Raft ◄├─────┼► Django + Raft ◄├─────┼► Django + Raft  │
│  (Leader)       │     │  (Follower)     │     │  (Follower)     │
│       ↓         │     │       ↓         │     │       ↓         │
│  Writes .primary│     │  Reads .primary │     │  Reads .primary │
│       ↓         │     │       ↓         │     │       ↓         │
│  LiteFS (write) │     │  LiteFS (read)  │     │  LiteFS (read)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**How it works:**

1. PySyncObj runs embedded in each Django process
2. Raft elects a leader (quorum-based, automatic failover)
3. Leader writes `.primary` file to signal LiteFS
4. LiteFS uses static lease mode; we manage the `.primary` file externally
5. If leader dies, Raft elects new leader within seconds

## Networking (Cross-Network Replication)

LiteFS requires HTTP connectivity between nodes. Cross-network setups need external VPN/tunneling.

| Port  | Purpose                           |
| ----- | --------------------------------- |
| 20202 | LiteFS replication (node-to-node) |
| 8080  | LiteFS proxy (client requests)    |
| 4321  | Raft leader election (V2)         |

**Recommended**: Use [Tailscale](https://tailscale.com/) for easy mesh VPN between nodes in different networks. This is out of scope for litefs-py—documented but not implemented.




