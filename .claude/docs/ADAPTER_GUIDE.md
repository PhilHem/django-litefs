# Framework Adapter Integration Guide

This guide documents how to add LiteFS support to a new Python web framework (e.g., FastAPI, Flask, Starlette).

## Overview

LiteFS-py provides a framework-agnostic core package with ports (interfaces) that framework adapters implement. Framework adapters:

- Read settings from framework-specific configuration
- Implement ports defined in `litefs.adapters.ports`
- Delegate validation and business logic to core use cases
- Handle framework-specific error translation

**Reference**: `packages/litefs/src/litefs/adapters/ports.py`

---

## Port Contracts

### 1. Settings Reader

Framework adapters must read settings from their framework's configuration and convert them to `LiteFSSettings`.

```python
from litefs.domain.settings import LiteFSSettings

def get_litefs_settings() -> LiteFSSettings | None:
    """Read framework config and return domain settings."""
    config = get_framework_config()  # Framework-specific
    if not config.get('LITEFS'):
        return None

    # Map framework naming conventions to domain fields
    return LiteFSSettings(
        mount_path=config['LITEFS']['mount_path'],
        data_path=config['LITEFS'].get('data_path'),
        # ... other fields
    )
```

**Requirements**:
- Map framework naming conventions (e.g., `UPPER_CASE`) to domain fields (`snake_case`)
- Return `None` if LiteFS not configured (don't raise error)
- Let `LiteFSSettings` validation handle invalid values (don't duplicate)

### 2. PrimaryDetectorPort

Detects if the current node is the primary. Default implementation checks `.primary` file.

```python
from typing import Protocol

class PrimaryDetectorPort(Protocol):
    def is_primary(self) -> bool:
        """Return True if this node is the primary."""
        ...
```

**Default implementation**: `FileSystemPrimaryDetector` checks for `.primary` file in mount path.

### 3. NodeIDResolverPort

Resolves the current node's ID. Default reads from `LITEFS_NODE_ID` environment variable.

```python
class NodeIDResolverPort(Protocol):
    def resolve_node_id(self) -> str:
        """Return the current node's unique identifier."""
        ...
```

**Custom implementation example** (reading from framework config):
```python
class FrameworkNodeIDResolver:
    def __init__(self, config):
        self.config = config

    def resolve_node_id(self) -> str:
        node_id = self.config.get('node_id', '').strip()
        if not node_id:
            raise ValueError("node_id cannot be empty")
        return node_id
```

### 4. SplitBrainDetectorPort (Optional)

Detects split-brain conditions (multiple nodes claiming leadership).

```python
class SplitBrainDetectorPort(Protocol):
    def get_cluster_state(self) -> RaftClusterState:
        """Return current cluster state with leader information."""
        ...
```

If not configured, split-brain detection is skipped.

### 5. EventEmitterPort (Optional)

Emits events for observability (failover, health changes).

```python
class EventEmitterPort(Protocol):
    def emit(self, event: Event) -> None:
        """Emit event to observers. Fire-and-forget (never raises)."""
        ...
```

---

## Adapter Registration

Framework adapters should integrate with their framework's startup hooks.

### Django

```python
# apps.py
from django.apps import AppConfig

class LiteFSDjangoConfig(AppConfig):
    name = 'litefs_django'

    def ready(self):
        from .settings import get_litefs_settings
        settings = get_litefs_settings()
        if settings:
            # Validate at startup
            settings.validate()
```

### FastAPI

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_litefs_settings()
    if settings:
        settings.validate()
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)
```

---

## Validation Delegation

**Critical**: Adapters MUST delegate validation to the core domain layer. This maintains Clean Architecture boundaries.

```python
# CORRECT: Let domain validate
def get_litefs_settings():
    return LiteFSSettings(
        mount_path=config['mount_path']  # Domain validates this
    )

# WRONG: Adapter duplicates validation
def get_litefs_settings():
    mount_path = config['mount_path']
    if not mount_path.startswith('/'):  # DON'T DO THIS
        raise ValueError("mount_path must be absolute")
    return LiteFSSettings(mount_path=mount_path)
```

---

## Error Handling Contract

Adapters must handle and translate core errors appropriately.

| Core Error | Adapter Action |
|------------|----------------|
| `LiteFSConfigError` | Wrap in framework-specific config error, preserve message |
| `LiteFSNotRunningError` | Propagate or translate to "service unavailable" |
| `NotPrimaryError` | Translate to database error (for DB adapters) |
| `SplitBrainError` | Translate to database error, block writes |

**Always preserve the exception chain**:
```python
try:
    result = core_operation()
except LiteFSConfigError as e:
    raise FrameworkConfigError(str(e)) from e  # Preserve chain
```

---

## Testing Adapters

### Unit Tests

- Use mock ports, don't require LiteFS running
- Verify protocol compliance with `runtime_checkable`

```python
from typing import runtime_checkable
from litefs.adapters.ports import PrimaryDetectorPort

def test_implements_protocol():
    adapter = MyPrimaryDetector()
    assert isinstance(adapter, PrimaryDetectorPort)
```

### Integration Tests

- Use real `LiteFSSettings` domain object
- Mock filesystem access with temp directories

### Property Tests

- Use Hypothesis to generate random configurations
- Verify all valid configs work, invalid configs raise errors

---

## Checklist for New Adapters

- [ ] Settings reader returns `LiteFSSettings` or `None`
- [ ] No validation logic in adapter (delegated to domain)
- [ ] Startup hook validates configuration
- [ ] Error translation preserves exception chain
- [ ] Health check endpoint exposes node state
- [ ] Unit tests use mock ports
- [ ] Protocol compliance verified with `isinstance`

---

## Reference Implementations

- **Django**: `packages/litefs-django/src/litefs_django/`
  - `settings.py` - Settings reader
  - `adapters.py` - Port implementations
  - `apps.py` - AppConfig registration

---

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Package structure and layers
- [CONFIGURATION.md](./CONFIGURATION.md) - Settings examples
- [DECISIONS.md](./DECISIONS.md) - Design decisions
