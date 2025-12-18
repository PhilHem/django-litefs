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
            "proxy": {
                "addr": settings.proxy_addr,
            },
        }

        return yaml.dump(config, default_flow_style=False)
