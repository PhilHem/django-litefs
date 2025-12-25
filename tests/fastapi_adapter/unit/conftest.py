"""Fixtures for FastAPI adapter unit tests."""

import pytest


@pytest.fixture
def pydantic_settings_dict() -> dict[str, str | bool | list[str] | None]:
    """Example Pydantic settings dict (snake_case keys)."""
    return {
        "mount_path": "/litefs",
        "data_path": "/var/lib/litefs",
        "database_name": "db.sqlite3",
        "leader_election": "static",
        "proxy_addr": ":8080",
        "enabled": True,
        "retention": "1h",
    }
