# Settings Interface

## Core API (litefs-py)

```python
from litefs import LiteFSSettings

settings = LiteFSSettings(
    mount_path="/litefs",
    data_path="/var/lib/litefs",
    database_name="db.sqlite3",
    leader_election="static",          # "static" (V1) or "raft" (V2)
    raft_self_addr="localhost:4321",   # V2 only
    raft_peers=[],                     # V2 only
    proxy_addr=":8080",
    enabled=True,
    retention="1h",
)
```

## Django Adapter (litefs-django)

```python
# settings.py
INSTALLED_APPS = [
    ...
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
    "LEADER_ELECTION": "static",       # "static" (V1) or "raft" (V2)
    "RAFT_SELF_ADDR": "localhost:4321",
    "RAFT_PEERS": [],
    "PROXY_ADDR": ":8080",
    "ENABLED": True,
    "RETENTION": "1h",
}
```

## FastAPI Adapter (future)

```python
from litefs_fastapi import LiteFSMiddleware, get_litefs_settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    litefs_mount_path: str = "/litefs"
    litefs_raft_peers: list[str] = []
    # ... maps to LiteFSSettings

app.add_middleware(LiteFSMiddleware, settings=get_litefs_settings())
```




