"""Config generator use case for LiteFS."""

import yaml
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litefs.domain.settings import LiteFSSettings


class ConfigGenerator:
    """Generates LiteFS YAML configuration from settings."""

    def generate(self, settings: "LiteFSSettings") -> str:
        """Generate LiteFS YAML config from settings.

        Args:
            settings: LiteFS settings domain entity

        Returns:
            YAML string representing LiteFS configuration
        """
        # Build proxy config
        proxy_config: dict[str, object] = {
            "addr": settings.proxy_addr,
        }

        # Add detailed proxy settings if provided
        if settings.proxy is not None:
            proxy_config["target"] = settings.proxy.target
            proxy_config["db"] = settings.proxy.db
            proxy_config["passthrough"] = settings.proxy.passthrough
            proxy_config["primary_redirect_timeout"] = (
                settings.proxy.primary_redirect_timeout
            )

        config = {
            "fuse": {
                "dir": settings.mount_path,
            },
            "data": {
                "dir": settings.data_path,
            },
            "databases": [
                {
                    "path": settings.database_name,
                }
            ],
            "lease": {
                "type": settings.leader_election,
            },
            "proxy": proxy_config,
        }

        return yaml.dump(config, default_flow_style=False)
