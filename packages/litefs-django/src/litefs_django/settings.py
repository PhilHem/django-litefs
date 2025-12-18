"""Settings reader for Django LiteFS adapter."""

from typing import Any

from litefs.domain.settings import LiteFSSettings


def get_litefs_settings(django_settings: dict[str, Any]) -> LiteFSSettings:
    """Convert Django LITEFS settings dict to LiteFSSettings domain object.

    Maps UPPER_CASE Django keys to snake_case domain fields.

    Args:
        django_settings: Django settings dict with UPPER_CASE keys

    Returns:
        LiteFSSettings domain object

    Raises:
        LiteFSConfigError: If settings are invalid (delegates to domain validation)
    """
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
        elif domain_field in ("raft_self_addr", "raft_peers"):
            # Optional fields default to None if not provided
            kwargs[domain_field] = None

    # Create domain object (validation happens in __post_init__)
    return LiteFSSettings(**kwargs)
