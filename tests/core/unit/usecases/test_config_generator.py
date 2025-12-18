"""Unit tests for ConfigGenerator use case."""

import pytest
import yaml

from litefs.domain.settings import LiteFSSettings
from litefs.usecases.config_generator import ConfigGenerator


@pytest.mark.unit
class TestConfigGenerator:
    """Test ConfigGenerator use case."""

    def test_generate_config_from_settings(self):
        """Test generating LiteFS config from settings."""
        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
        )
        generator = ConfigGenerator()
        config = generator.generate(settings)

        # Should be valid YAML
        parsed = yaml.safe_load(config)
        assert parsed is not None

        # Should contain mount path
        assert "fuse" in parsed
        assert parsed["fuse"]["dir"] == "/litefs"

        # Should contain data path
        assert "data" in parsed
        assert parsed["data"]["dir"] == "/var/lib/litefs"

        # Should contain database config
        assert "databases" in parsed
        assert len(parsed["databases"]) == 1
        assert parsed["databases"][0]["path"] == "db.sqlite3"

    def test_generate_config_with_static_leader_election(self):
        """Test config generation with static leader election."""
        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
        )
        generator = ConfigGenerator()
        config = generator.generate(settings)
        parsed = yaml.safe_load(config)

        # Static mode should have lease config
        assert "lease" in parsed
        assert parsed["lease"]["type"] == "static"
