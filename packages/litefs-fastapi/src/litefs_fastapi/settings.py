"""Settings reader for FastAPI LiteFS adapter."""

from typing import Any

from litefs.domain.exceptions import LiteFSConfigError
from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig

# Required fields that must be present in Pydantic settings
_REQUIRED_FIELDS = (
    "mount_path",
    "data_path",
    "database_name",
    "leader_election",
    "proxy_addr",
    "enabled",
    "retention",
)

# Optional fields that default to None if not provided
_OPTIONAL_FIELDS = ("raft_self_addr", "raft_peers", "primary_hostname")


def get_litefs_settings(pydantic_settings: dict[str, Any]) -> LiteFSSettings:
    """Convert Pydantic settings dict to LiteFSSettings domain object.

    Maps snake_case Pydantic keys directly to domain fields (both are snake_case).

    Args:
        pydantic_settings: Pydantic settings dict with snake_case keys

    Returns:
        LiteFSSettings domain object

    Raises:
        LiteFSConfigError: If required settings are missing or invalid
    """
    # Validate required fields first
    missing = [key for key in _REQUIRED_FIELDS if key not in pydantic_settings]
    if missing:
        raise LiteFSConfigError(
            f"Missing required LiteFS settings: {', '.join(sorted(missing))}"
        )

    # Extract values directly (no mapping needed - both use snake_case)
    kwargs: dict[str, Any] = {}
    for field in _REQUIRED_FIELDS:
        kwargs[field] = pydantic_settings[field]

    # Add optional fields (except primary_hostname - it goes into static_leader_config)
    for field in ("raft_self_addr", "raft_peers"):
        if field in pydantic_settings:
            kwargs[field] = pydantic_settings[field]
        else:
            kwargs[field] = None

    # Parse static leader configuration if leader_election is "static"
    leader_election = kwargs.get("leader_election")
    if leader_election == "static":
        # primary_hostname is required for static mode
        if (
            "primary_hostname" not in pydantic_settings
            or pydantic_settings["primary_hostname"] is None
        ):
            raise LiteFSConfigError(
                "primary_hostname is required when leader_election is 'static'"
            )
        primary_hostname = pydantic_settings["primary_hostname"]
        # StaticLeaderConfig validates the hostname in __post_init__
        kwargs["static_leader_config"] = StaticLeaderConfig(
            primary_hostname=primary_hostname
        )
    else:
        # static_leader_config is None for non-static modes
        kwargs["static_leader_config"] = None

    # Create domain object (validation happens in __post_init__)
    return LiteFSSettings(**kwargs)
