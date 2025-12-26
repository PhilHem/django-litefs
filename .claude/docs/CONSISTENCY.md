# Read-Your-Writes Consistency with LiteFS Proxy

## Problem: Consistency Without Stickiness

When deploying Django with LiteFS behind a load balancer, users face a classic distributed systems challenge:

1. **Asynchronous Replication**: LiteFS replicates writes to replicas asynchronously
2. **Multiple Replicas**: Load balancer can route requests to any node
3. **Read-after-Write Risk**: User writes on primary, next request routes to replica that hasn't replicated yet

```
Request 1: User writes data (Primary)
         ▼
         LiteFS replicates (async)
         ▼
Request 2: User reads data (might route to Replica 2, which hasn't seen write yet)
         ▼
         "I just wrote this, where is my data?!"
```

**The Problem**: Without affinity or session stickiness, the user's second request could hit a replica that hasn't yet replicated the data from their first write, causing read-after-write inconsistency.

**Traditional Solutions** (Problematic):
- ❌ Session stickiness — reduces load balancer flexibility, breaks on node failure
- ❌ Master/replica routing — requires custom application logic
- ❌ Strongly consistent replication — high latency, incompatible with distributed SQL

## Solution: LiteFS Proxy with TXID Cookies

The LiteFS proxy solves this elegantly by tracking **transaction IDs (TXIDs)**:

### How It Works

1. **Client makes write request** → Proxy forwards to primary
2. **Primary writes to database** → Database returns TXID (transaction ID)
3. **Proxy embeds TXID in response cookie** → Response includes `litefs-txid=<txid>`
4. **Client makes read request** → Request includes `litefs-txid=<txid>` cookie
5. **Replica receives request with TXID** → Replica stalls reads until it has replicated to at least that TXID
6. **Replica catches up** → Returns consistent read of user's own write

**Key Insight**: The cookie travels with the client, not the session. If a user jumps between nodes, their requests automatically carry the necessary TXID, ensuring they always see their own writes.

### Architecture: Proxy Placement

```
                        ┌─────────────────┐
                        │  Load Balancer  │
                        │  (no stickiness)│
                        └────────┬────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
    ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
    │ Node 1      │      │ Node 2      │      │ Node 3      │
    │ (Primary)   │      │ (Replica)   │      │ (Replica)   │
    │             │      │             │      │             │
    │ LiteFS Proxy│      │ LiteFS Proxy│      │ LiteFS Proxy│
    │ :8080       │      │ :8080       │      │ :8080       │
    │    ▼        │      │    ▼        │      │    ▼        │
    │ Django :8000       │ Django :8000       │ Django :8000│
    │    ▼        │      │    ▼        │      │    ▼        │
    │ /litefs/db  │  ◄───┼──────────────────┼──────────►    │
    │ (read/write)│      │ (read-only) │      │ (read-only) │
    └─────────────┘      └─────────────┘      └─────────────┘
           │
           └──── Writes replicated asynchronously ──────┘
```

**Key Components**:
- **LiteFS Proxy** (port 8080): Sits between load balancer and Django, intercepts requests
- **TXID Cookie**: Automatic request/response header (transparent to application)
- **Replica Stalling**: When replica sees TXID header, it waits for replication to catch up before returning reads

### Proxy Configuration

The proxy is configured via `ProxySettings` in the domain layer:

**Required Fields**:
- `addr`: Proxy listen address (e.g., `:8080`) — where the proxy listens for incoming requests
- `target`: Application address (e.g., `localhost:8000`) — where Django is running
- `db`: Database name (e.g., `db.sqlite3`) — which database to track TXIDs for

**Optional Fields**:
- `passthrough`: URL patterns to bypass proxy (e.g., `/health`, `/static/*`) — useful for health checks
- `primary_redirect_timeout`: How long to hold writes during failover (default: `5s`) — allows primary to redirect writes to new leader during election

### Consistency Guarantees

| Scenario | Guarantee | How |
|----------|-----------|-----|
| Write then read (same client) | ✅ See own writes | TXID cookie ensures replica catches up |
| Read-heavy workload | ✅ Mostly replica reads | Only waits for TXID if needed |
| Primary failure | ✅ Automatic failover | New primary elected, `primary_redirect_timeout` buffers write redirects |
| Network partition | ⚠️ Writes disabled | Split-brain detection prevents inconsistency (see SPLIT_BRAIN_ANALYSIS.md) |

**What You Get**:
- ✅ No session stickiness needed
- ✅ Load balancer can route freely
- ✅ Transparent to application code
- ✅ Automatic replica stalling (no app logic needed)
- ✅ Works with multiple replicas

## Configuration Examples

### Django Settings with Proxy

```python
# settings.py

LITEFS = {
    # Core LiteFS configuration
    "MOUNT_PATH": "/litefs",
    "DATA_PATH": "/var/lib/litefs",
    "DATABASE_NAME": "db.sqlite3",
    "LEADER_ELECTION": "raft",  # or "static" for static primary
    "PROXY_ADDR": ":8080",
    "ENABLED": True,
    "RETENTION": "1h",

    # Raft consensus for automatic failover
    "RAFT_SELF_ADDR": "node-1:4321",
    "RAFT_PEERS": ["node-1:4321", "node-2:4321", "node-3:4321"],

    # Proxy configuration for read-your-writes consistency
    "PROXY": {
        "ADDR": ":8080",                           # Proxy listens here
        "TARGET": "localhost:8000",                # Django runs here
        "DB": "db.sqlite3",                        # Database to track TXIDs for
        "PASSTHROUGH": ["/health", "/static/*"],  # Routes that skip proxy
        "PRIMARY_REDIRECT_TIMEOUT": "10s",         # Hold writes during failover
    }
}

# Django database backend (unchanged)
DATABASES = {
    "default": {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "default",
    }
}
```

### Docker Compose with Proxy

```yaml
version: "3.8"
services:
  node-1:
    build: .
    environment:
      LITEFS_NODE_ID: "node-1"
      DJANGO_SETTINGS_MODULE: "config.settings"
    ports:
      - "8080:8080"  # Expose proxy port (load balancer points here)
    volumes:
      - litefs-data-1:/litefs
      - litefs-state-1:/var/lib/litefs

  node-2:
    build: .
    environment:
      LITEFS_NODE_ID: "node-2"
      DJANGO_SETTINGS_MODULE: "config.settings"
    ports:
      - "8081:8080"  # Expose proxy on different host port
    volumes:
      - litefs-data-2:/litefs
      - litefs-state-2:/var/lib/litefs

  node-3:
    build: .
    environment:
      LITEFS_NODE_ID: "node-3"
      DJANGO_SETTINGS_MODULE: "config.settings"
    ports:
      - "8082:8080"
    volumes:
      - litefs-data-3:/litefs
      - litefs-state-3:/var/lib/litefs

  load-balancer:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - node-1
      - node-2
      - node-3

volumes:
  litefs-data-1:
  litefs-state-1:
  litefs-data-2:
  litefs-state-2:
  litefs-data-3:
  litefs-state-3:
```

### Nginx Configuration (Load Balancer)

```nginx
upstream django_backends {
    server node-1:8080;
    server node-2:8080;
    server node-3:8080;

    # No sticky sessions needed!
    # Each request can route to any backend
}

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://django_backends;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Proxy automatically handles litefs-txid cookie forwarding
        # No special configuration needed here
    }
}
```

### litefs.yml (Generated Automatically)

The proxy configuration is embedded in the `litefs.yml` file that litefs-py generates. You typically don't edit this directly, but here's what it looks like:

```yaml
# This is generated by litefs-py, not manually edited
fuse:
  dir: /litefs

data:
  dir: /var/lib/litefs

proxy:
  addr: :8080
  target: localhost:8000
  db: db.sqlite3
  passthrough:
    - /health
    - /static/*
  primary-redirect-timeout: 10s

lease:
  type: static
  advertise-url: http://node-1:20202
  promote: true
```

## Deployment Strategies

### Strategy 1: Multi-Node Kubernetes

```
┌──────────────────────────────────────────────┐
│          Kubernetes Cluster                  │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  Ingress (LoadBalancer Service)        │ │
│  └────────────────────────────────────────┘ │
│           ▼              ▼              ▼    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐
│  │  Pod 1   │    │  Pod 2   │    │  Pod 3   │
│  │ (Primary)│    │(Replica) │    │(Replica) │
│  │  Django  │    │  Django  │    │  Django  │
│  │ LiteFS   │    │ LiteFS   │    │ LiteFS   │
│  └──────────┘    └──────────┘    └──────────┘
│       │               │               │      │
│       └───────────────┼───────────────┘      │
│               Replication                    │
└──────────────────────────────────────────────┘
```

**Setup**:
1. Deploy Django app with LiteFS to Kubernetes as StatefulSet
2. Each pod gets persistent volume for `/litefs` and `/var/lib/litefs`
3. Service exposes port 8080 (LiteFS proxy) to Ingress
4. Ingress routes traffic to all pods (no sticky sessions)
5. Proxy handles TXID consistency automatically

### Strategy 2: Docker Compose (Local Development)

See example above. Each node runs in a container, load balancer (nginx) routes traffic to all three.

### Strategy 3: VM-Based (Single Zone)

```
VMs in Same Zone/Network:
- vm-1 (Primary): runs Django + LiteFS
- vm-2 (Replica): runs Django + LiteFS
- vm-3 (Replica): runs Django + LiteFS

Load Balancer (nginx on vm-lb):
- Routes to vm-1:8080, vm-2:8080, vm-3:8080
```

**Key Difference**: Faster replication (LAN speeds), no external VPN needed. Replication typically <100ms.

### Strategy 4: Cross-Zone / Multi-Region (Requires VPN)

```
Zone 1 (us-east):           Zone 2 (us-west):
┌──────────────────┐        ┌──────────────────┐
│ vm-1 (Primary)   │        │ vm-2 (Replica)   │
└──────────────────┘        └──────────────────┘
         │                           │
         └──────────(Tailscale VPN)──┘

LiteFS replication works over VPN tunnel
```

**Recommended**: Use [Tailscale](https://tailscale.com/) for automatic mesh VPN. LiteFS replication will work transparently over the encrypted tunnel.

## Troubleshooting

### "litefs-txid header not being set"

**Symptom**: User doesn't see their own writes on replica.

**Cause**: Proxy might not be running or misconfigured.

**Fix**:
1. Check proxy is listening: `curl -v http://localhost:8080/health | grep litefs-txid`
2. Verify `PROXY` settings in Django `LITEFS` dict
3. Check LiteFS logs for proxy errors: `docker logs <container> | grep proxy`

### "Replica is slower than expected"

**Symptom**: Reads are slow when TXID cookie is present.

**Cause**: Replica is stalling to wait for replication. Normal behavior.

**Fix**: This is expected during high write loads. The replica is ensuring consistency. Consider:
- Increasing `primary_redirect_timeout` if primary failures are frequent
- Reducing write load per request
- Adding more replicas to distribute read load

### "Writes timing out during failover"

**Symptom**: Client gets timeout when primary fails during write.

**Cause**: `primary_redirect_timeout` is too short for your failover time.

**Fix**: Increase `PRIMARY_REDIRECT_TIMEOUT` in proxy config:

```python
"PROXY": {
    "ADDR": ":8080",
    "TARGET": "localhost:8000",
    "DB": "db.sqlite3",
    "PRIMARY_REDIRECT_TIMEOUT": "30s",  # Increase if needed
}
```

### "Cannot write from replica even with proxy"

**Symptom**: Replica raises `NotPrimaryError` despite using proxy.

**Cause**: Application is not routing writes through proxy (routing directly to LiteFS, bypassing proxy).

**Fix**: Ensure load balancer points to proxy port (8080), not Django (8000). The proxy must intercept all requests.

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Write on primary | ~5ms | Local disk write (SSD recommended) |
| Read on primary | ~1ms | No replication wait |
| Read on replica (no TXID) | ~1ms | Immediate, may be stale |
| Read on replica (with TXID) | 50-500ms | Waits for replication, varies by network |
| Failover time | 1-5s | Raft election time |

**Recommendation**: Use primary for writes in single-user workflows, replicas for distributed read loads. The TXID cookie makes this transparent to the application.

## When to Use This Pattern

✅ **Use LiteFS proxy when**:
- You have multiple replicas and want automatic failover (Raft)
- Load balancer cannot have session stickiness
- You need to support multi-tab browsing (users jumping between nodes)
- You want transparent read-your-writes without application logic
- You're deploying to Kubernetes or distributed infrastructure

❌ **Alternatives**:
- Single primary + session stickiness: Simpler, no TXID overhead, but less flexible
- Strongly consistent replication: Higher latency, use only if latency not critical
- Application-level routing: More control but requires custom logic

## Related Documentation

- **[DEPLOYMENT.md]** — Architecture diagrams, networking, node-to-node replication
- **[SPLIT_BRAIN_ANALYSIS.md]** — How LiteFS detects and prevents split-brain
- **[RAFT_CONFIGURATION.md]** — Raft consensus details for automatic leader election
- **[CONFIGURATION.md]** — Complete settings reference

## References

- [LiteFS Proxy Documentation](https://fly.io/docs/litefs/proxy/)
- [Transaction ID (TXID) Semantics](https://fly.io/docs/litefs/consistency/)
- [Read-Your-Writes Consistency Pattern](https://en.wikipedia.org/wiki/Read-your-writes_consistency)
