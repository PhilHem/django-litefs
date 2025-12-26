"""Unit tests for ConfigGenerator use case."""

import pytest
import yaml
from hypothesis import given, strategies as st

from litefs.domain.settings import LiteFSSettings
from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.config_generator import ConfigGenerator


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
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

    def test_generate_includes_proxy_addr(self):
        """Test that generated config includes proxy.addr field."""
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

        # Should contain proxy config
        assert "proxy" in parsed
        assert "addr" in parsed["proxy"]
        assert parsed["proxy"]["addr"] == ":8080"

    def test_generate_proxy_addr_value(self):
        """Test that proxy.addr value matches settings.proxy_addr."""
        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr="localhost:3000",
            enabled=True,
            retention="1h",
        )
        generator = ConfigGenerator()
        config = generator.generate(settings)
        parsed = yaml.safe_load(config)

        assert parsed["proxy"]["addr"] == "localhost:3000"


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestConfigParser:
    """Test ConfigParser use case."""

    def test_parse_yaml_to_settings(self):
        """Test basic parsing of YAML to LiteFSSettings."""
        yaml_str = """
fuse:
  dir: /litefs
data:
  dir: /var/lib/litefs
databases:
  - path: db.sqlite3
lease:
  type: static
proxy:
  addr: :8080
"""
        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        settings = parser.parse(yaml_str)

        assert isinstance(settings, LiteFSSettings)
        assert settings.mount_path == "/litefs"
        assert settings.data_path == "/var/lib/litefs"
        assert settings.database_name == "db.sqlite3"
        assert settings.leader_election == "static"
        assert settings.proxy_addr == ":8080"
        assert settings.enabled is True
        assert settings.retention == ""
        assert settings.raft_self_addr is None
        assert settings.raft_peers is None

    def test_parse_includes_proxy_addr(self):
        """Test that proxy.addr is parsed correctly."""
        yaml_str = """
fuse:
  dir: /litefs
data:
  dir: /var/lib/litefs
databases:
  - path: db.sqlite3
lease:
  type: static
proxy:
  addr: localhost:3000
"""
        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        settings = parser.parse(yaml_str)

        assert settings.proxy_addr == "localhost:3000"

    def test_parse_missing_proxy_addr(self):
        """Test that missing proxy.addr defaults to empty string."""
        yaml_str = """
fuse:
  dir: /litefs
data:
  dir: /var/lib/litefs
databases:
  - path: db.sqlite3
lease:
  type: static
"""
        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        settings = parser.parse(yaml_str)

        assert settings.proxy_addr == ""

    def test_parse_invalid_yaml(self):
        """Test that invalid YAML raises LiteFSConfigError."""
        invalid_yaml = "invalid: yaml: ["
        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        with pytest.raises(LiteFSConfigError):
            parser.parse(invalid_yaml)

    def test_parse_missing_required_fields(self):
        """Test that missing required fields raises LiteFSConfigError."""
        incomplete_yaml = """
fuse:
  dir: /litefs
"""
        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        with pytest.raises(LiteFSConfigError):
            parser.parse(incomplete_yaml)

    def test_parse_empty_database_path_raises_config_error(self):
        """Test that empty database path raises LiteFSConfigError (PARSE-001)."""
        yaml_config = """
fuse:
  dir: /litefs
data:
  dir: /var/lib/litefs
databases:
  - path: ""
lease:
  type: static
"""
        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        with pytest.raises(LiteFSConfigError, match="database path"):
            parser.parse(yaml_config)

    def test_parse_whitespace_database_path_raises_config_error(self):
        """Test that whitespace-only database path raises LiteFSConfigError (PARSE-001)."""
        yaml_config = """
fuse:
  dir: /litefs
data:
  dir: /var/lib/litefs
databases:
  - path: "   "
lease:
  type: static
"""
        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        with pytest.raises(LiteFSConfigError, match="database path"):
            parser.parse(yaml_config)


@pytest.mark.tier(3)
@pytest.mark.tra("UseCase")
class TestConfigRoundTrip:
    """Property-based tests for config round-trip idempotence."""

    @given(
        mount_path=st.just("/litefs"),
        data_path=st.just("/var/lib/litefs"),
        database_name=st.text(min_size=1, max_size=50),
        proxy_addr=st.text(min_size=0, max_size=100),
    )
    def test_round_trip_idempotence(
        self,
        mount_path,
        data_path,
        database_name,
        proxy_addr,
    ):
        """Property-based test: generate(settings) → parse → verify YAML fields match.

        Note: Only tests 'static' mode since ConfigGenerator/ConfigParser don't
        yet serialize raft_self_addr/raft_peers fields. Raft round-trip requires
        updating config_generator.py and config_parser.py (separate task).
        """
        # Skip if values would fail domain validation
        if ".." in mount_path or ".." in data_path:
            return
        if not mount_path.startswith("/") or not data_path.startswith("/"):
            return
        # Skip if database_name is empty or whitespace-only (rejected by domain)
        if not database_name or not database_name.strip():
            return

        settings = LiteFSSettings(
            mount_path=mount_path,
            data_path=data_path,
            database_name=database_name,
            leader_election="static",  # Only static mode round-trips correctly
            proxy_addr=proxy_addr,
            enabled=True,
            retention="1h",
        )

        generator = ConfigGenerator()
        yaml_str = generator.generate(settings)

        from litefs.usecases.config_parser import ConfigParser

        parser = ConfigParser()
        parsed_settings = parser.parse(yaml_str)

        # Verify YAML-representable fields match
        assert parsed_settings.mount_path == settings.mount_path
        assert parsed_settings.data_path == settings.data_path
        assert parsed_settings.database_name == settings.database_name
        assert parsed_settings.leader_election == settings.leader_election
        assert parsed_settings.proxy_addr == settings.proxy_addr


@pytest.mark.tier(3)
@pytest.mark.tra("UseCase")
class TestYAMLGenerationPBT:
    """Property-based tests for YAML generation validity."""

    @given(
        database_name=st.text(min_size=1, max_size=100),
        proxy_addr=st.text(max_size=200),
    )
    def test_generated_yaml_is_valid(self, database_name, proxy_addr):
        """PBT: Generated YAML is always valid and parseable."""
        # Skip if database_name is whitespace-only (rejected by domain validation)
        if not database_name.strip():
            return

        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name=database_name,
            leader_election="static",
            proxy_addr=proxy_addr,
            enabled=True,
            retention="1h",
        )

        generator = ConfigGenerator()
        yaml_str = generator.generate(settings)

        # Should be parseable YAML
        parsed = yaml.safe_load(yaml_str)
        assert parsed is not None

        # Should contain expected structure
        assert "databases" in parsed
        assert len(parsed["databases"]) == 1
        assert parsed["databases"][0]["path"] == database_name
        assert parsed["proxy"]["addr"] == proxy_addr

    @given(value=st.text(max_size=100))
    def test_yaml_special_chars_handled(self, value):
        """PBT: YAML special chars (@*&!|>) produce valid output."""
        # Skip if value is empty or whitespace-only (rejected by domain validation)
        if not value or not value.strip():
            return

        # Use value in database_name and proxy_addr
        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name=value,
            leader_election="static",
            proxy_addr=value,
            enabled=True,
            retention="1h",
        )

        generator = ConfigGenerator()
        yaml_str = generator.generate(settings)

        # Should be parseable YAML regardless of special chars
        parsed = yaml.safe_load(yaml_str)
        assert parsed is not None


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestConfigDeterminism:
    """Tests for config output determinism."""

    def test_generate_produces_identical_output_for_same_input(self):
        """Same settings always produce byte-identical YAML."""
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

        # Generate multiple times
        yaml1 = generator.generate(settings)
        yaml2 = generator.generate(settings)
        yaml3 = generator.generate(settings)

        # All outputs should be byte-identical
        assert yaml1 == yaml2 == yaml3


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestConfigGeneratorProxy:
    """Test ConfigGenerator proxy section generation."""

    def test_generate_proxy_with_all_fields(self) -> None:
        """Test generating config with complete proxy configuration."""
        from litefs.domain.settings import ProxySettings

        proxy_settings = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
            passthrough=["/static/*", "*.css"],
            primary_redirect_timeout="10s",
        )

        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
            proxy=proxy_settings,
        )

        generator = ConfigGenerator()
        config = generator.generate(settings)
        parsed = yaml.safe_load(config)

        # Verify proxy section exists
        assert "proxy" in parsed
        proxy = parsed["proxy"]

        # Verify all proxy fields
        assert proxy["addr"] == ":8080"
        assert proxy["target"] == "localhost:8081"
        assert proxy["db"] == "db.sqlite3"
        assert proxy["passthrough"] == ["/static/*", "*.css"]
        assert proxy["primary_redirect_timeout"] == "10s"

    def test_generate_proxy_with_default_timeout(self) -> None:
        """Test generating config with default primary_redirect_timeout."""
        from litefs.domain.settings import ProxySettings

        proxy_settings = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )

        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
            proxy=proxy_settings,
        )

        generator = ConfigGenerator()
        config = generator.generate(settings)
        parsed = yaml.safe_load(config)

        proxy = parsed["proxy"]
        assert proxy["primary_redirect_timeout"] == "5s"

    def test_generate_proxy_with_empty_passthrough(self) -> None:
        """Test generating config with empty passthrough list."""
        from litefs.domain.settings import ProxySettings

        proxy_settings = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
            passthrough=[],
        )

        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
            proxy=proxy_settings,
        )

        generator = ConfigGenerator()
        config = generator.generate(settings)
        parsed = yaml.safe_load(config)

        proxy = parsed["proxy"]
        assert proxy["passthrough"] == []

    def test_generate_without_proxy_settings(self) -> None:
        """Test generating config with proxy=None (backward compat)."""
        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
            proxy=None,
        )

        generator = ConfigGenerator()
        config = generator.generate(settings)
        parsed = yaml.safe_load(config)

        # Should have proxy section with just addr (backward compat)
        assert "proxy" in parsed
        assert parsed["proxy"]["addr"] == ":8080"


