# litefs-django

Django adapter for [LiteFS](https://fly.io/docs/litefs/) SQLite replication with built-in high availability, automatic leader election, and split-brain detection.

## What is litefs-django?

**litefs-django** is a Django database backend that seamlessly integrates [LiteFS](https://github.com/superfly/litefs) into Django applications. It enables:

- **Multi-node SQLite replication** — synchronized SQLite databases across multiple nodes without external databases
- **Automatic leader election** — static (V1) or Raft consensus (V2) modes to elect a primary node that handles writes
- **High availability** — replica nodes can safely handle reads while the primary handles all writes
- **Split-brain detection** — prevents data inconsistency when network partitions occur
- **Zero external services** — all consensus and replication handled locally via LiteFS, no Consul, etcd, or external coordination

Built on top of the [litefs-py](https://github.com/superfly/litefs-py) core library.

## Installation

Install via pip:

```bash
pip install litefs-django
```

This will also install the required `litefs-py` core package, which bundles the LiteFS binary.

**Requirements:**
- Python 3.10+
- Django 5.0+
- LiteFS binary (automatically included in litefs-py)

## Quick Start

### 1. Add to Django Settings

In your Django `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    "litefs_django",
]

# Configure LiteFS
LITEFS = {
    "MOUNT_PATH": "/litefs",           # Where LiteFS mounts the replicated database
    "DATA_PATH": "/var/lib/litefs",    # Where LiteFS stores state and WAL
    "DATABASE_NAME": "db.sqlite3",     # Name of your SQLite database file
    "LEADER_ELECTION": "static",       # "static" (V1) or "raft" (V2)
    "PRIMARY_HOSTNAME": "node-0",      # For static mode: hostname of the primary node
    "PROXY_ADDR": ":8080",             # Port for LiteFS proxy
    "ENABLED": True,
    "RETENTION": "1h",                 # How long to keep WAL files
}

# Configure Django database backend
DATABASES = {
    "default": {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "default",
    }
}
```

### 2. Set Environment Variable (for node identification)

Each node running your application must set `LITEFS_NODE_ID` to identify itself:

```bash
export LITEFS_NODE_ID="node-0"  # Unique identifier for this node
```

This is required for leader election and split-brain detection to work correctly.

### 3. Handle Write Operations on Replicas

When a replica receives a write request, litefs-django raises `NotPrimaryError`:

```python
from litefs_django.exceptions import NotPrimaryError, SplitBrainError

try:
    # This will fail if the current node is a replica
    user = User.objects.create(username="alice")
except NotPrimaryError:
    # Route write to primary node or return an error
    return redirect_to_primary(request)
except SplitBrainError:
    # Network partition detected - writes disabled temporarily
    return retry_later(request)
```

Alternatively, use middleware to handle writes automatically:

```python
# In your views, check if the node is primary before writes:
from litefs_django.settings import get_litefs_settings
from django.conf import settings

def create_user(request):
    litefs_config = settings.LITEFS
    # Application logic to route writes based on node role
    # ...
```

### 4. Run Database Migrations

Since litefs-django uses SQLite locally, migrations work as normal:

```bash
python manage.py migrate
```

Migrations will be replicated to all nodes automatically by LiteFS.

## Configuration

### Required Settings

| Setting | Type | Description |
|---------|------|-------------|
| `MOUNT_PATH` | str | Path where LiteFS mounts the replicated database (default: `/litefs`) |
| `DATA_PATH` | str | Directory where LiteFS stores state files and WAL (default: `/var/lib/litefs`) |
| `DATABASE_NAME` | str | Name of the SQLite database file (default: `db.sqlite3`) |
| `LEADER_ELECTION` | str | Leader election mode: `"static"` or `"raft"` |
| `PROXY_ADDR` | str | LiteFS proxy address for replication (default: `:8080`) |
| `ENABLED` | bool | Enable LiteFS integration (default: `True`) |
| `RETENTION` | str | WAL retention duration, e.g., `"1h"`, `"24h"` (default: `"1h"`) |

### Conditional Settings

**For static leader election mode** (`LEADER_ELECTION: "static"`):
- `PRIMARY_HOSTNAME` (required) — hostname of the node designated as primary

**For Raft mode** (`LEADER_ELECTION: "raft"`):
- `RAFT_SELF_ADDR` — network address of this node (e.g., `"localhost:4321"`)
- `RAFT_PEERS` — list of peer node addresses for Raft consensus

For detailed configuration examples, see the [Configuration Guide](../../../.claude/docs/CONFIGURATION.md) in the project repository.

## Features

### Static Leader Election (V1)

In static mode, a single designated primary node handles all writes:

```python
LITEFS = {
    "LEADER_ELECTION": "static",
    "PRIMARY_HOSTNAME": "node-0",
    # ... other settings
}
```

Use when you have a stable, predictable primary node and don't need automatic failover.

### Raft Consensus (V2)

In Raft mode, nodes dynamically elect a leader via consensus:

```python
LITEFS = {
    "LEADER_ELECTION": "raft",
    "RAFT_SELF_ADDR": "localhost:4321",
    "RAFT_PEERS": ["node-1:4321", "node-2:4321"],
    # ... other settings
}
```

Use for automatic failover and high availability without manual primary designation.

### Split-Brain Detection

litefs-django detects split-brain conditions (network partitions causing multiple leaders):

```python
from litefs_django.exceptions import SplitBrainError

try:
    obj = MyModel.objects.create(field="value")
except SplitBrainError:
    # Network partition detected - writes prevented
    logger.error("Split-brain detected, writes disabled")
```

Connect to the `split_brain_detected` signal to log or alert:

```python
from litefs_django import split_brain_detected
from django.dispatch import receiver

@receiver(split_brain_detected)
def on_split_brain(sender, **kwargs):
    logger.critical("Split-brain condition detected!")
    # Send alerts, scale down replicas, etc.
```

## Exceptions

### NotPrimaryError

Raised when a write operation is attempted on a replica node:

```python
from litefs_django.exceptions import NotPrimaryError
from django.db import DatabaseError

try:
    obj = MyModel.objects.create(...)
except NotPrimaryError as e:
    # This node is a replica, route to primary
    pass
```

Inherits from Django's `DatabaseError` for integration with Django error handling.

### SplitBrainError

Raised when a write operation is attempted during a split-brain condition:

```python
from litefs_django.exceptions import SplitBrainError

try:
    obj = MyModel.objects.create(...)
except SplitBrainError as e:
    # Network partition detected, writes temporarily disabled
    pass
```

Inherits from Django's `DatabaseError` and should trigger alerting in production.

## Architecture

litefs-django follows Clean Architecture principles:

- **Django adapter** (`litefs_django/`) — Framework integration, settings reader, database backend
- **Core library** (`litefs-py`) — Leader election, health checking, config generation
- **LiteFS** — Underlying binary for SQLite replication and consensus

The adapter delegates all business logic to the core library and focuses on Django integration.

## Read-Your-Writes Consistency with Proxy (Quick Start)

When deploying behind a load balancer without session stickiness, use the LiteFS proxy to ensure read-your-writes consistency:

```python
LITEFS = {
    # ... standard LiteFS settings ...

    # Enable proxy for automatic consistency
    "PROXY": {
        "ADDR": ":8080",              # Proxy listen port
        "TARGET": "localhost:8000",   # Django app address
        "DB": "db.sqlite3",           # Database to track TXIDs
    }
}
```

**How it works**: The proxy automatically embeds transaction IDs (TXIDs) in cookies. When a user writes data, the proxy captures the TXID. On subsequent reads, the proxy ensures replicas have caught up to that TXID before returning results. This guarantees users always see their own writes, even across multiple replica nodes.

**Benefits**:
- ✅ No session stickiness needed
- ✅ Load balancer can route freely
- ✅ Transparent to application code
- ✅ Works automatically for all requests

**For detailed explanation, deployment examples, and troubleshooting**: See [Consistency Documentation](../../../.claude/docs/CONSISTENCY.md).

## Deployment

### Docker Compose Example

```yaml
version: "3.8"
services:
  app-primary:
    build: .
    environment:
      LITEFS_NODE_ID: "node-0"
      DJANGO_SETTINGS_MODULE: "config.settings"
    volumes:
      - litefs:/litefs
      - litefs-data:/var/lib/litefs

  app-replica:
    build: .
    environment:
      LITEFS_NODE_ID: "node-1"
      DJANGO_SETTINGS_MODULE: "config.settings"
    volumes:
      - litefs:/litefs
      - litefs-data:/var/lib/litefs

volumes:
  litefs:
  litefs-data:
```

For detailed deployment guides, see [Deployment Documentation](../../../.claude/docs/DEPLOYMENT.md).

## Testing

To test your Django app with litefs-django:

```bash
# Unit tests (no LiteFS process required)
pytest -m unit

# Integration tests (requires Docker + FUSE)
pytest -m integration

# All tests
pytest
```

Example test with split-brain handling:

```python
import pytest
from litefs_django.exceptions import SplitBrainError, NotPrimaryError

@pytest.mark.unit
def test_replica_write_raises_not_primary():
    with pytest.raises(NotPrimaryError):
        User.objects.create(username="alice")

@pytest.mark.unit
def test_split_brain_raises_error():
    with pytest.raises(SplitBrainError):
        User.objects.create(username="bob")
```

## API Reference

### Settings Reader

```python
from litefs_django.settings import get_litefs_settings
from django.conf import settings

# Convert Django settings to domain object
litefs_settings = get_litefs_settings(settings.LITEFS)
print(litefs_settings.mount_path)  # "/litefs"
print(litefs_settings.leader_election)  # "static" or "raft"
```

### App Configuration

```python
from litefs_django.apps import LiteFSDjangoConfig

# Automatically runs on Django startup:
# - Validates LiteFS settings
# - Checks mount path
# - Logs primary/replica status
```

### Signals

```python
from litefs_django import split_brain_detected

@receiver(split_brain_detected)
def handle_split_brain(sender, **kwargs):
    # Log, alert, or trigger failover logic
    pass
```

## Troubleshooting

### "LiteFS mount path validation failed"

The LiteFS mount path doesn't exist or LiteFS is not running:

1. Check that LiteFS is running: `ps aux | grep litefs`
2. Verify mount path exists: `ls -la /litefs`
3. Check LiteFS logs for errors

### "Missing required LiteFS settings"

One or more required LITEFS settings are not configured in Django settings:

```python
# Ensure all required keys are present:
LITEFS = {
    "MOUNT_PATH": "/litefs",
    "DATA_PATH": "/var/lib/litefs",
    "DATABASE_NAME": "db.sqlite3",
    "LEADER_ELECTION": "static",
    "PRIMARY_HOSTNAME": "node-0",  # Required for static mode
    "PROXY_ADDR": ":8080",
    "ENABLED": True,
    "RETENTION": "1h",
}
```

### "Split-brain condition detected"

A network partition has caused consensus to break down. Writes are blocked to prevent data inconsistency:

1. Check network connectivity between nodes
2. Review LiteFS logs for partition details
3. Consider reducing the split-brain timeout or investigating root cause

## Documentation

- **[LiteFS Documentation](https://fly.io/docs/litefs/)** — LiteFS architecture, deployment, troubleshooting
- **[LiteFS GitHub](https://github.com/superfly/litefs)** — Source code and issues
- **[litefs-py Core Library](https://github.com/superfly/litefs-py)** — Python library documentation
- **[Configuration Guide](./../../../.claude/docs/CONFIGURATION.md)** — Detailed settings reference
- **[Architecture Guide](./../../../.claude/docs/ARCHITECTURE.md)** — Package structure and layer diagram
- **[Deployment Guide](./../../../.claude/docs/DEPLOYMENT.md)** — Kubernetes, Docker Compose, VMs

## License

MIT License. Note: LiteFS itself is Apache-2.0 (compatible with MIT).

## Support

- File issues on [GitHub](https://github.com/superfly/litefs-py/issues)
- Check [LiteFS documentation](https://fly.io/docs/litefs/) for LiteFS-specific questions
- Review the [ARCHITECTURE guide](./../../../.claude/docs/ARCHITECTURE.md) for design decisions
