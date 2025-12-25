"""Unit tests for factory functions."""

import pytest
from unittest.mock import patch, MagicMock

from litefs.factories import (
    create_raft_leader_election,
    PyLeaderNotInstalledError,
)
from litefs.domain.settings import LiteFSSettings


def make_raft_settings(
    raft_self_addr: str = "node1:20202",
    raft_peers: list[str] | None = None,
) -> LiteFSSettings:
    """Helper to create valid Raft settings for tests."""
    return LiteFSSettings(
        mount_path="/litefs",
        data_path="/data",
        database_name="app.db",
        leader_election="raft",
        proxy_addr="localhost:8080",
        enabled=True,
        retention="24h",
        raft_self_addr=raft_self_addr,
        raft_peers=raft_peers or ["node2:20202", "node3:20202"],
    )


def make_static_settings() -> LiteFSSettings:
    """Helper to create static leader settings for tests."""
    from litefs.domain.settings import StaticLeaderConfig

    return LiteFSSettings(
        mount_path="/litefs",
        data_path="/data",
        database_name="app.db",
        leader_election="static",
        proxy_addr="localhost:8080",
        enabled=True,
        retention="24h",
        static_leader_config=StaticLeaderConfig(primary_hostname="node1"),
    )


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestCreateRaftLeaderElection:
    """Tests for create_raft_leader_election factory function."""

    def test_creates_raft_leader_election_with_valid_settings(self) -> None:
        """Factory creates RaftLeaderElection with valid Raft settings."""
        settings = make_raft_settings()
        mock_raft_class = MagicMock()
        mock_instance = MagicMock()
        mock_raft_class.return_value = mock_instance

        with patch.dict(
            "sys.modules",
            {"py_leader": MagicMock(RaftLeaderElection=mock_raft_class)},
        ):
            result = create_raft_leader_election(
                settings=settings,
                node_id="node1:20202",
            )

        mock_raft_class.assert_called_once_with(
            node_id="node1:20202",
            cluster_members=["node1:20202", "node2:20202", "node3:20202"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert result is mock_instance

    def test_passes_custom_timeout_and_interval(self) -> None:
        """Factory passes custom election_timeout and heartbeat_interval."""
        settings = make_raft_settings()
        mock_raft_class = MagicMock()

        with patch.dict(
            "sys.modules",
            {"py_leader": MagicMock(RaftLeaderElection=mock_raft_class)},
        ):
            create_raft_leader_election(
                settings=settings,
                node_id="node1:20202",
                election_timeout=10.0,
                heartbeat_interval=2.0,
            )

        mock_raft_class.assert_called_once_with(
            node_id="node1:20202",
            cluster_members=["node1:20202", "node2:20202", "node3:20202"],
            election_timeout=10.0,
            heartbeat_interval=2.0,
        )

    def test_raises_error_for_static_leader_election(self) -> None:
        """Factory raises ValueError when settings use static leader election."""
        settings = make_static_settings()

        with pytest.raises(ValueError, match="must be 'raft'"):
            create_raft_leader_election(settings=settings, node_id="node1")

    def test_raises_error_when_raft_self_addr_is_none(self) -> None:
        """Factory raises ValueError when raft_self_addr is None.

        Note: LiteFSSettings validation should prevent this, but factory
        provides its own validation for defense in depth.
        """
        # Create settings object bypassing validation
        settings = LiteFSSettings.__new__(LiteFSSettings)
        settings.mount_path = "/litefs"
        settings.data_path = "/data"
        settings.database_name = "app.db"
        settings.leader_election = "raft"
        settings.proxy_addr = "localhost:8080"
        settings.enabled = True
        settings.retention = "24h"
        settings.raft_self_addr = None
        settings.raft_peers = ["node2:20202"]
        settings.static_leader_config = None

        with pytest.raises(ValueError, match="raft_self_addr is required"):
            create_raft_leader_election(settings=settings, node_id="node1")

    def test_raises_error_when_raft_peers_is_none(self) -> None:
        """Factory raises ValueError when raft_peers is None."""
        # Create settings object bypassing validation
        settings = LiteFSSettings.__new__(LiteFSSettings)
        settings.mount_path = "/litefs"
        settings.data_path = "/data"
        settings.database_name = "app.db"
        settings.leader_election = "raft"
        settings.proxy_addr = "localhost:8080"
        settings.enabled = True
        settings.retention = "24h"
        settings.raft_self_addr = "node1:20202"
        settings.raft_peers = None
        settings.static_leader_config = None

        with pytest.raises(ValueError, match="raft_peers is required"):
            create_raft_leader_election(settings=settings, node_id="node1")


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestPyLeaderNotInstalledError:
    """Tests for PyLeaderNotInstalledError."""

    def test_error_message_includes_install_instructions(self) -> None:
        """Error message tells users how to install py-leader."""
        error = PyLeaderNotInstalledError()
        assert "py-leader is not installed" in str(error)
        assert "pip install litefs-py[raft]" in str(error)

    def test_is_import_error_subclass(self) -> None:
        """PyLeaderNotInstalledError is an ImportError subclass."""
        error = PyLeaderNotInstalledError()
        assert isinstance(error, ImportError)

    def test_raised_when_py_leader_not_installed(self) -> None:
        """Factory raises PyLeaderNotInstalledError when py-leader missing."""
        settings = make_raft_settings()

        # Simulate py_leader not being installed
        with patch.dict("sys.modules", {"py_leader": None}):
            with pytest.raises(PyLeaderNotInstalledError):
                create_raft_leader_election(settings=settings, node_id="node1:20202")
