"""Config parser use case for LiteFS."""

import yaml
from typing import TYPE_CHECKING

from litefs.domain.exceptions import LiteFSConfigError

if TYPE_CHECKING:
    from litefs.domain.settings import LiteFSSettings


class ConfigParser:
    """Parses LiteFS YAML configuration to settings."""

    def parse(self, yaml_str: str) -> "LiteFSSettings":
        """Parse LiteFS YAML config to settings.

        Args:
            yaml_str: YAML string representing LiteFS configuration

        Returns:
            LiteFSSettings domain object

        Raises:
            LiteFSConfigError: If YAML is invalid or required fields are missing
        """
        try:
            config = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise LiteFSConfigError(f"Invalid YAML: {e}") from e

        if not isinstance(config, dict):
            raise LiteFSConfigError("Config must be a dictionary")

        # Extract required fields
        try:
            mount_path = config["fuse"]["dir"]
            data_path = config["data"]["dir"]
            database_name = config["databases"][0]["path"]
            leader_election = config["lease"]["type"]
        except (KeyError, IndexError, TypeError) as e:
            raise LiteFSConfigError(f"Missing required field in config: {e}") from e

        # Validate database path is not empty (PARSE-001)
        if not database_name or not database_name.strip():
            raise LiteFSConfigError("database path cannot be empty")

        # Extract optional proxy.addr field (default to empty string)
        proxy_addr = ""
        if "proxy" in config and isinstance(config["proxy"], dict):
            proxy_addr = config["proxy"].get("addr", "")

        # Import here to avoid circular dependency
        from litefs.domain.settings import LiteFSSettings

        # Create settings with defaults for non-YAML fields
        return LiteFSSettings(
            mount_path=mount_path,
            data_path=data_path,
            database_name=database_name,
            leader_election=leader_election,
            proxy_addr=proxy_addr,
            enabled=True,  # Default for non-YAML field
            retention="",  # Default for non-YAML field
            raft_self_addr=None,  # Optional field
            raft_peers=None,  # Optional field
        )





