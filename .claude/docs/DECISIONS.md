# Design Decisions & ADRs

## Project Decisions

| Item             | Decision                                          |
| ---------------- | ------------------------------------------------- |
| License          | MIT                                               |
| Repository       | Monorepo                                          |
| Package name     | `litefs-py`                                       |
| Platform support | Linux and macOS (FUSE required)                   |
| Min cluster size | 2 nodes (single failover), 3+ nodes (Raft quorum) |
| Example app      | Yes, in `examples/` directory                     |

## Architecture Decisions

### Django Integration

- **Database Backend**: Custom `DatabaseWrapper` subclass of `django.db.backends.sqlite3`
- **Write Forwarding**: Handled by LiteFS proxy (HTTP layer), not database backend
- **Transaction Mode**: Enforce `IMMEDIATE` mode by default for better lock handling
- **WAL Mode**: Auto-configured (LiteFS requirement)
- **Migrations**: Only run on primary node (check via LiteFS `.primary` file)

### Process Management

- **LiteFS Lifecycle**: LiteFS is the container entrypoint; it spawns Django as a child process
- **Startup Hook**: `AppConfig.ready` validates settings and checks LiteFS availability
- **Signal Handling**: LiteFS handles SIGTERM; Django receives it via process tree
- **Health Checks**: Django exposes health endpoint that queries LiteFS for replica lag

### Binary Distribution

- **Approach**: Platform-specific wheels
- **Platforms**:
  - `manylinux_2_17_x86_64`
  - `manylinux_2_17_aarch64`
  - `macosx_11_0_x86_64`
  - `macosx_11_0_arm64`
- **Build System**: `hatchling` with custom build hook
- **LiteFS Version**: Pin to specific release, document upgrade process
- **CI**: GitHub Actions builds wheels for each platform

### Config Generation

- Generate `litefs.yml` from Django settings at runtime
- Store generated config in temp directory or `DATA_PATH`
- Validate settings on Django startup

## Answered Questions

### LiteFS version to bundle

**Decision**: Latest stable release (currently 0.5.x series). Pin to specific version in `pyproject.toml`, document upgrade process in CHANGELOG. Check [LiteFS releases](https://github.com/superfly/litefs/releases) before initial release.

### PySyncObj vs alternatives

**Decision**: Use **PySyncObj**

- Mature library (3k+ GitHub stars)
- Pure Python, no C dependencies
- Battle-tested Raft implementation
- Supports dynamic cluster membership
- Alternatives considered: raft-py (less mature), dragonboat (Go, not Python)

### How Raft integrates with LiteFS

**Decision**: We manage the `.primary` file externally

1. LiteFS runs in `static` lease mode (no Consul)
2. PySyncObj elects a Raft leader among Django processes
3. Raft leader writes `.primary` file to LiteFS mount
4. LiteFS reads `.primary` to determine which node accepts writes
5. On leader change, new leader updates `.primary` file

This works because LiteFS's static mode just checks for the `.primary` file—it doesn't care how the file gets there.




