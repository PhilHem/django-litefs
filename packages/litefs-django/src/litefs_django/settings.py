"""Settings reader for Django LiteFS adapter."""

from typing import Any

from litefs.domain.exceptions import LiteFSConfigError
from litefs.domain.settings import LiteFSSettings

# Required fields that must be present in Django settings
_REQUIRED_FIELDS = (
    "MOUNT_PATH",
    "DATA_PATH",
    "DATABASE_NAME",
    "LEADER_ELECTION",
    "PROXY_ADDR",
    "ENABLED",
    "RETENTION",
)

# Optional fields that default to None if not provided
_OPTIONAL_FIELDS = ("RAFT_SELF_ADDR", "RAFT_PEERS")


def get_litefs_settings(django_settings: dict[str, Any]) -> LiteFSSettings:
    """Convert Django LITEFS settings dict to LiteFSSettings domain object.

    Maps UPPER_CASE Django keys to snake_case domain fields.

    Args:
        django_settings: Django settings dict with UPPER_CASE keys

    Returns:
        LiteFSSettings domain object

    Raises:
        LiteFSConfigError: If required settings are missing or invalid
    """
    # Validate required fields first (PROP-002)
    missing = [key for key in _REQUIRED_FIELDS if key not in django_settings]
    if missing:
        raise LiteFSConfigError(
            f"Missing required LiteFS settings: {', '.join(sorted(missing))}"
        )

    # Map UPPER_CASE Django keys to snake_case domain fields
    field_mapping = {
        "MOUNT_PATH": "mount_path",
        "DATA_PATH": "data_path",
        "DATABASE_NAME": "database_name",
        "LEADER_ELECTION": "leader_election",
        "PROXY_ADDR": "proxy_addr",
        "ENABLED": "enabled",
        "RETENTION": "retention",
        "RAFT_SELF_ADDR": "raft_self_addr",
        "RAFT_PEERS": "raft_peers",
    }

    # Convert Django dict to domain object kwargs
    kwargs: dict[str, Any] = {}
    for django_key, domain_field in field_mapping.items():
        if django_key in django_settings:
            kwargs[domain_field] = django_settings[django_key]
        elif django_key in _OPTIONAL_FIELDS:
            # Optional fields default to None if not provided
            kwargs[domain_field] = None

    # Create domain object (validation happens in __post_init__)
    return LiteFSSettings(**kwargs)




