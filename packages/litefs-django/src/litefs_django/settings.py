"""Settings reader for Django LiteFS adapter."""

from typing import Any

from litefs.domain.exceptions import LiteFSConfigError
from litefs.domain.settings import (
    LiteFSSettings,
    StaticLeaderConfig,
    ProxySettings,
    ForwardingSettings,
)

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
_OPTIONAL_FIELDS = ("RAFT_SELF_ADDR", "RAFT_PEERS", "PRIMARY_HOSTNAME")


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

    # Parse static leader configuration if leader_election is "static"
    leader_election = kwargs.get("leader_election")
    if leader_election == "static":
        # PRIMARY_HOSTNAME is required for static mode
        if "PRIMARY_HOSTNAME" not in django_settings:
            raise LiteFSConfigError(
                "PRIMARY_HOSTNAME is required when LEADER_ELECTION is 'static'"
            )
        primary_hostname = django_settings["PRIMARY_HOSTNAME"]
        # StaticLeaderConfig validates the hostname in __post_init__
        kwargs["static_leader_config"] = StaticLeaderConfig(
            primary_hostname=primary_hostname
        )
    else:
        # static_leader_config is None for non-static modes
        kwargs["static_leader_config"] = None

    # Parse proxy configuration if provided
    if "PROXY" in django_settings:
        proxy_dict = django_settings["PROXY"]

        # Validate required proxy fields
        required_proxy_fields = ("ADDR", "TARGET", "DB")
        missing_proxy_fields = [
            field for field in required_proxy_fields if field not in proxy_dict
        ]
        if missing_proxy_fields:
            raise LiteFSConfigError(
                f"Missing required PROXY settings: {', '.join(sorted(missing_proxy_fields))}"
            )

        # ProxySettings validates required fields in __post_init__
        kwargs["proxy"] = ProxySettings(
            addr=proxy_dict["ADDR"],
            target=proxy_dict["TARGET"],
            db=proxy_dict["DB"],
            passthrough=proxy_dict.get("PASSTHROUGH", []),
            primary_redirect_timeout=proxy_dict.get("PRIMARY_REDIRECT_TIMEOUT", "5s"),
        )
    else:
        # proxy is None if not provided
        kwargs["proxy"] = None

    # Parse forwarding configuration if provided
    if "FORWARDING" in django_settings:
        fwd_dict = django_settings["FORWARDING"]
        # Convert EXCLUDED_PATHS list to tuple for immutability
        excluded_paths = tuple(fwd_dict.get("EXCLUDED_PATHS", []))
        kwargs["forwarding"] = ForwardingSettings(
            enabled=fwd_dict.get("ENABLED", False),
            primary_url=fwd_dict.get("PRIMARY_URL"),
            timeout_seconds=fwd_dict.get("TIMEOUT_SECONDS", 30.0),
            retry_count=fwd_dict.get("RETRY_COUNT", 1),
            excluded_paths=excluded_paths,
            scheme=fwd_dict.get("SCHEME", "http"),
            connect_timeout=fwd_dict.get("CONNECT_TIMEOUT", 5.0),
            read_timeout=fwd_dict.get("READ_TIMEOUT", 30.0),
            retry_backoff_base=fwd_dict.get("RETRY_BACKOFF_BASE", 1.0),
            circuit_breaker_threshold=fwd_dict.get("CIRCUIT_BREAKER_THRESHOLD", 5),
            circuit_breaker_reset_timeout=fwd_dict.get(
                "CIRCUIT_BREAKER_RESET_TIMEOUT", 30.0
            ),
            circuit_breaker_enabled=fwd_dict.get("CIRCUIT_BREAKER_ENABLED", True),
        )
    else:
        # forwarding is None if not provided
        kwargs["forwarding"] = None

    # Create domain object (validation happens in __post_init__)
    return LiteFSSettings(**kwargs)


def is_dev_mode(django_settings: dict[str, Any] | None) -> bool:
    """Check if LiteFS is in dev mode (disabled).

    Dev mode is active when:
    - LITEFS settings dict is missing entirely (None)
    - LITEFS.ENABLED is explicitly set to False

    Production mode is active when:
    - LITEFS dict exists and ENABLED is True or not specified

    Args:
        django_settings: Django LITEFS settings dict, or None if not configured

    Returns:
        True if in dev mode (LiteFS disabled), False if in production mode
    """
    if django_settings is None:
        return True
    # If ENABLED key exists and is False, we're in dev mode
    # If ENABLED key doesn't exist or is True, we're in production mode
    return django_settings.get("ENABLED", True) is False
