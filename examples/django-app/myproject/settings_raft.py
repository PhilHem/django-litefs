"""Django settings for LiteFS example project with Raft leader election.

This configuration uses py-leader for automatic leader election instead of
static primary. See docker-compose.raft.yml for the Docker Compose setup.
"""

import os

# Import everything from base settings
from myproject.settings import *  # noqa: F401, F403

# Override LiteFS configuration for Raft leader election
LITEFS = {
    "MOUNT_PATH": "/litefs",
    "DATA_PATH": "/data",
    "DATABASE_NAME": "db.sqlite3",
    "LEADER_ELECTION": "raft",  # Use Raft leader election
    "NODE_ID": os.getenv("LITEFS_NODE_ID", "node1"),
    "CLUSTER_MEMBERS": os.getenv(
        "LITEFS_CLUSTER_MEMBERS", "node1:20202,node2:20202,node3:20202"
    ).split(","),
    "ELECTION_TIMEOUT": 5.0,  # Seconds
    "HEARTBEAT_INTERVAL": 1.0,  # Seconds
    "PROXY_ADDR": ":8081",
    "ENABLED": True,
    "RETENTION": "1h",
}
