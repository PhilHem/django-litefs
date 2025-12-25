# LiteFS + Django Example Application

A minimal but complete example demonstrating **LiteFS integration with Django** for multi-node SQLite replication with static leader election.

## What This Example Shows

- **3-node LiteFS cluster** using Docker Compose
- **Static leader election**: node1 is the primary, nodes 2 & 3 are read-only replicas
- **Write routing**: Write requests to replicas are forwarded to the primary
- **Data replication**: All writes are replicated to replicas asynchronously
- **Read/write operations**: Simple API endpoints demonstrating both
- **Health checks**: Cluster status and database connectivity verification

## Project Structure

```
examples/django-app/
├── myproject/          # Django project (settings, URLs, WSGI)
│   ├── settings.py     # LiteFS configuration + Django settings
│   ├── urls.py         # Main URL dispatcher
│   └── wsgi.py         # WSGI entry point
├── myapp/              # Example Django app
│   ├── models.py       # Simple Message model
│   ├── views.py        # API endpoints
│   ├── urls.py         # App URL routes
│   └── admin.py        # Django admin
├── manage.py           # Django CLI
├── Dockerfile          # Container build configuration
├── docker-compose.yml  # 3-node cluster definition
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Prerequisites

- Docker and Docker Compose (latest versions)
- Or Python 3.10+ with Django 5.x and litefs-py/litefs-django installed

## Quick Start (Docker Compose)

### 1. Build and Start the Cluster

```bash
# Start all 3 nodes
docker-compose up -d

# Watch startup logs
docker-compose logs -f

# Wait for all nodes to be healthy (check healthcheck status)
docker-compose ps
```

The cluster will be ready when all 3 containers show status `healthy`.

### 2. Test the API

**Health check** - should return the same database count on all nodes:

```bash
# Primary (node1) - can read and write
curl http://localhost:8001/api/health/

# Replica (node2) - read-only
curl http://localhost:8002/api/health/

# Replica (node3) - read-only
curl http://localhost:8003/api/health/
```

**Create a message** on the primary:

```bash
curl -X POST http://localhost:8001/api/messages/create/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello from node1"}'
```

**Verify replication** - read from any node:

```bash
# From replica (node2) - should see the message created on node1
curl http://localhost:8002/api/messages/

# From replica (node3) - should see the same message
curl http://localhost:8003/api/messages/
```

**View statistics** - see message counts by creating node:

```bash
curl http://localhost:8001/api/stats/
```

### 3. Django Admin

Access Django admin panel to manage messages:

```
http://localhost:8001/admin/
```

Create an admin user on the primary:

```bash
docker-compose exec node1 python manage.py createsuperuser
```

## How It Works

### Static Leader Election

This example uses **static leader election** (V1), where the primary node is determined by the `PRIMARY_HOSTNAME` environment variable:

```python
# In myproject/settings.py
LITEFS = {
    "LEADER_ELECTION": "static",
    "PRIMARY_HOSTNAME": "node1",  # node1 is always primary
    ...
}
```

**Node Roles:**
- **node1** (Primary): Can read and write
- **node2** (Replica): Read-only, queries are handled locally, writes are forwarded to primary
- **node3** (Replica): Read-only, queries are handled locally, writes are forwarded to primary

### Data Flow

1. **Write Request to Replica (node2)**:
   ```
   User → node2:8002/messages/create
       → LiteFS proxy detects write
       → Forwards to primary (node1)
       → Primary executes write
       → Replicates to all replicas
       → Response returned to client
   ```

2. **Read Request (any node)**:
   ```
   User → node2:8002/messages/
       → Query executed locally on replica
       → Data returned from local copy
   ```

### LiteFS Configuration

The LiteFS configuration is embedded in Django settings (see `myproject/settings.py`):

```python
LITEFS = {
    "MOUNT_PATH": "/litefs",          # Where LiteFS mounts the DB
    "DATA_PATH": "/data",              # Where LiteFS stores state
    "DATABASE_NAME": "db.sqlite3",     # Database filename
    "LEADER_ELECTION": "static",       # Use static (not Raft) election
    "PRIMARY_HOSTNAME": "node1",       # Primary node hostname
    "PROXY_ADDR": ":8081",             # LiteFS proxy port
    "ENABLED": True,                   # Enable LiteFS
    "RETENTION": "1h",                 # Data retention
}
```

### Database Backend

The Django database is configured to use the LiteFS backend:

```python
DATABASES = {
    "default": {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "db.sqlite3",
        "OPTIONS": {
            "litefs_mount_path": "/litefs",
            "transaction_mode": "IMMEDIATE",  # Prevent lock contention
        },
    }
}
```

The `litefs_django.db.backends.litefs` backend:
- Delegates database queries to the standard SQLite3 backend
- Enforces primary detection before writes
- Prevents split-brain write attempts
- Automatically routes writes through the LiteFS proxy

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Health check, returns node name and DB status |
| GET | `/api/messages/` | List all messages in the database |
| POST | `/api/messages/create/` | Create a new message (primary only) |
| GET | `/api/stats/` | Get message counts by node |

### Example Requests

```bash
# Health check
curl http://localhost:8001/api/health/

# Create message (on primary)
curl -X POST http://localhost:8001/api/messages/create/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'

# List messages (on any node)
curl http://localhost:8001/api/messages/

# Stats
curl http://localhost:8001/api/stats/
```

## Testing Write Routing

To verify that writes are correctly routed to the primary:

1. Create a message on a replica:

```bash
curl -X POST http://localhost:8002/api/messages/create/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Created on replica"}'
```

2. You should see the message was actually created by node1 (check `node_name` field)

3. Verify on all nodes:

```bash
curl http://localhost:8001/api/messages/
curl http://localhost:8002/api/messages/
curl http://localhost:8003/api/messages/
```

All nodes should show the same messages, with `node_name: "node1"` indicating the primary created them.

## Testing Replication

To simulate replication in action:

1. Create a message on the primary:

```bash
curl -X POST http://localhost:8001/api/messages/create/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Replication test"}'
```

2. Immediately query all replicas (fast enough to see replication happening):

```bash
# May not see the message immediately (in-flight)
curl http://localhost:8002/api/messages/

# Retry - should eventually appear
curl http://localhost:8002/api/messages/
```

## Stopping the Cluster

```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (clears data)
docker-compose down -v
```

## Troubleshooting

### Containers keep restarting

Check logs for errors:

```bash
docker-compose logs node1
docker-compose logs node2
docker-compose logs node3
```

### Write requests fail with "Write operation attempted on replica node"

This is expected if you're trying to write to a replica. Write requests should go to node1:

```bash
# Correct - write to primary
curl -X POST http://localhost:8001/api/messages/create/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Test"}'

# This may fail if LiteFS proxy is not forwarding correctly
curl -X POST http://localhost:8002/api/messages/create/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Test"}'
```

### Database not found errors

Check that `/litefs` volume is mounted:

```bash
docker-compose exec node1 ls -la /litefs/
```

Should show `db.sqlite3` file.

### Replication not happening

Check LiteFS logs to verify nodes are connected:

```bash
docker-compose logs node1 | grep -i litefs
docker-compose logs node2 | grep -i litefs
```

## Production Considerations

This example uses static leader election, which is suitable for:
- **Small deployments** with known primary node
- **Simple setups** without automatic failover requirement
- **Development/testing** before moving to automatic leader election

For production deployments with automatic failover, consider using embedded Raft leader election (V2) or managed services like Fly.io.

### Networking for Multi-Node Deployments

For nodes running on different physical machines:

1. **Firewall Rules**: Allow port 20202 (LiteFS replication) between nodes
2. **VPN**: Use Tailscale or similar for encrypted cross-network replication
3. **Load Balancer**: Put nginx or HAProxy in front of all 3 nodes
4. **DNS**: Use stable hostnames resolvable from all nodes

Example load balancer config (nginx):

```nginx
upstream django_nodes {
    server node1:8000;
    server node2:8000;
    server node3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://django_nodes;
    }
}
```

## Customization

### Change the Primary Node

Edit `docker-compose.yml` and change `PRIMARY_HOSTNAME`:

```yaml
node1:
  environment:
    PRIMARY_HOSTNAME: node2  # node2 becomes primary
```

Then restart:

```bash
docker-compose down
docker-compose up -d
```

### Add More Replicas

Add a new service in `docker-compose.yml`:

```yaml
node4:
  # Copy node2 service and update hostname/ports
```

### Create New Django Models

1. Create model in `myapp/models.py`
2. Create migrations:

```bash
docker-compose exec node1 python manage.py makemigrations
```

3. Apply migrations:

```bash
docker-compose exec node1 python manage.py migrate
```

4. Models are automatically replicated to all nodes

## References

- [LiteFS Documentation](https://fly.io/docs/litefs/)
- [Django Custom Database Backends](https://docs.djangoproject.com/en/5.2/ref/databases/#subclassing-the-built-in-database-backends)
- [litefs-py Documentation](https://github.com/superfly/litefs-py)
- [litefs-django Documentation](https://github.com/superfly/litefs-py)

## License

This example is part of litefs-py and is available under the same license as the parent project.
