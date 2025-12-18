# litefs-py

A Python library for seamless SQLite replication via LiteFS, with framework adapters for Django, FastAPI, and more.

## Meta: Knowledge Management

> **Self-Correction Rule**: Continuously evaluate this file and suggest extraction when appropriate.
>
> | If knowledge is...               | Extract to                         | Example                                              |
> | -------------------------------- | ---------------------------------- | ---------------------------------------------------- |
> | General Python/dev patterns      | `~/.claude/skills/<name>/SKILL.md` | uv package management, Clean Architecture principles |
> | Project-specific workflows       | `.claude/skills/<name>/SKILL.md`   | LiteFS config generation, DB backend patterns        |
> | Detailed design docs (>50 lines) | `.claude/docs/<name>.md`           | Architecture diagrams, ADRs, deployment guides       |
>
> **Target**: Keep this file under 300 lines. Currently ~200 lines.
>
> **Before extracting, always**:
>
> 1. **Read the target file first** (if it exists) — deduplicate, don't duplicate
> 2. **Merge & improve** — strengthen existing content, discard if new is weaker
> 3. **Update references** — ensure all pointers reflect merged content
>
> **When creating skills**, use this YAML frontmatter template:
>
> ```yaml
> ---
> name: skill-name-here
> description: What this does AND when to use it. Include trigger keywords. Max 1024 chars.
> ---
> ```
>
> | Field         | Rules                                                                                      |
> | ------------- | ------------------------------------------------------------------------------------------ |
> | `name`        | Lowercase, numbers, hyphens only. Max 64 chars. Use gerund form (`processing-pdfs`).       |
> | `description` | Must include WHAT + WHEN. Include trigger terms users might say. Be specific, not generic. |
>
> **Why this matters**: Only `name` and `description` are pre-loaded at startup. Claude uses these to decide which skill to trigger from potentially 100+ available skills. The rest of SKILL.md loads on-demand.

## Reference Index

> Detail files are read on demand, not by default.

| Topic                          | Location                                       | Status       |
| ------------------------------ | ---------------------------------------------- | ------------ |
| Architecture layers & diagrams | `.claude/docs/ARCHITECTURE.md`                 | 🟢 Extracted |
| Design decisions & ADRs        | `.claude/docs/DECISIONS.md`                    | 🟢 Extracted |
| Deployment & networking        | `.claude/docs/DEPLOYMENT.md`                   | 🟢 Extracted |
| Settings interface examples    | `.claude/docs/CONFIGURATION.md`                | 🟢 Extracted |
| Dependencies tables            | `.claude/docs/DEPENDENCIES.md`                 | 🟢 Extracted |
| Testing patterns & fixtures    | `.claude/skills/litefs-testing/SKILL.md`       | 🟢 Extracted |
| Clean Architecture rules       | `~/.claude/skills/clean-architecture/SKILL.md` | 🟢 Extracted |

---

## Project Vision

- **Goal**: Framework-agnostic LiteFS integration; complexity abstracted away
- **Distribution**: Core package (`litefs-py`) + framework adapters (`django-litefs`, `fastapi-litefs`)
- **Target**: Python 3.10+
- **Use Case**: Multi-node HA deployments with synchronized SQLite (Kubernetes-like HA without Kubernetes)
- **Platform**: Self-hosted (Docker Compose, VMs, bare metal) — no external services required
- **Differentiator**: Embedded Raft leader election (no Consul/Fly.io dependency)

## Package Architecture

```
PyPI Packages:
├── litefs-py           # Core (framework-agnostic, bundles LiteFS binary)
├── litefs-django       # Django adapter (depends on litefs-py)
└── litefs-fastapi      # FastAPI adapter (future, depends on litefs-py)
```

| Layer   | Package          | Framework deps | Contents                                |
| ------- | ---------------- | -------------- | --------------------------------------- |
| Core    | `litefs-py`      | None           | Config generation, Raft, health, binary |
| Django  | `litefs-django`  | Django 5.x     | Settings reader, DB backend, commands   |
| FastAPI | `litefs-fastapi` | FastAPI        | Settings, middleware, routes (future)   |

> See [.claude/docs/ARCHITECTURE.md] for full package structure and layer mapping.
> See [.claude/docs/DEPLOYMENT.md] for deployment diagrams and networking.

## Clean Architecture

This project follows Clean Architecture principles. **Flag violations when spotted.**

- Dependencies point **inward only**
- Inner layers know nothing about outer layers
- Domain/Entities have zero external dependencies

**Violations to flag:**

- ❌ Domain layer importing Django
- ❌ Use cases importing from interface adapters
- ❌ Business logic in management commands or views
- ❌ Database backend containing business rules

> See [~/.claude/skills/clean-architecture/SKILL.md] for detailed layer diagrams and guidelines.

## Build Commands

```bash
# Install dependencies
uv sync

# Run all tests (excludes integration by default)
uv run pytest

# Run specific test category
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m property

# Type checking
uv run mypy src/django_litefs/

# Linting
uv run ruff check src/django_litefs/
uv run ruff format src/django_litefs/

# Build wheels
uv run python -m build
```

### Package Management (uv only)

**Never edit `pyproject.toml` dependencies directly.** Always use uv commands:

```bash
uv add requests              # Add dependency
uv add --group dev pytest    # Add dev dependency
uv remove requests           # Remove dependency
uv lock                      # Update lock file
```

## Testing

> See [.claude/skills/litefs-testing/SKILL.md] for full testing strategy, fixtures, and patterns.

```bash
pytest -m unit           # Fast, no LiteFS process
pytest -m integration    # With Docker + FUSE
pytest -m property       # Property-based tests
```

**Unit tests must NOT** spawn subprocesses, access filesystem beyond temp dirs, or require FUSE/Docker.

## Pre-commit Hooks

```bash
uv run pre-commit install    # Install hooks
uv run pre-commit run --all-files  # Run manually
```

**NEVER bypass pre-commit hooks with `--no-verify`.** Fix issues or report hook configuration problems.

## CI Parity

**CI must use identical commands to local development.** No separate CI-specific scripts.

## Configuration

> See [.claude/docs/CONFIGURATION.md] for full settings examples (core, Django, FastAPI).

Django settings use `LITEFS = {...}` dict. Database backend: `litefs_django.db.backends.litefs`.

## Dependencies

> See [.claude/docs/DEPENDENCIES.md] for full dependency tables.

**Core**: pydantic, pyyaml, httpx. **Django adapter**: litefs-py, Django 5.x.

## Decisions & Roadmap

> See [.claude/docs/DECISIONS.md] for architecture decisions and answered questions.
> See [ROADMAP.md] for detailed development roadmap with task breakdowns, phases, goals, and outcomes.

## Project Documentation

**Root-level files** (user-facing, version-controlled):

- **`ROADMAP.md`**: Detailed development roadmap with task IDs (`TASK-{PREFIX}-XXX`), phases, goals, and outcomes. Updated as work progresses.
- **`CHANGELOG.md`**: Release history following [Keep a Changelog](https://keepachangelog.com/) format. Updated on each release with semantic versioning.

**`.claude/docs/`** (internal, design docs):

- Architecture, decisions, deployment, configuration, dependencies — detailed design documentation read on demand.

## License

MIT License. Note: LiteFS itself is Apache-2.0 (compatible with MIT).

## References

- [LiteFS Documentation](https://fly.io/docs/litefs/)
- [LiteFS GitHub](https://github.com/superfly/litefs)
- [PySyncObj](https://github.com/bakwc/PySyncObj) - Raft consensus library
- [Tailscale](https://tailscale.com/) - Recommended for cross-network setups
- [Django Custom Database Backends](https://docs.djangoproject.com/en/5.2/ref/databases/#subclassing-the-built-in-database-backends)
