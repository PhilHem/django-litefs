"""Unit tests for RaftLeaderElectionAdapter."""

import pytest
from unittest.mock import Mock

from litefs.adapters.raft_leader_election_adapter import RaftLeaderElectionAdapter
from litefs.adapters.ports import LeaderElectionPort, RaftLeaderElectionPort


@pytest.mark.unit
class TestRaftLeaderElectionAdapterProtocolCompliance:
    """Test that RaftLeaderElectionAdapter implements port protocols correctly."""

    def test_adapter_satisfies_leader_election_port(self) -> None:
        """Test that RaftLeaderElectionAdapter satisfies LeaderElectionPort protocol."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        assert isinstance(adapter, LeaderElectionPort)

    def test_adapter_satisfies_raft_leader_election_port(self) -> None:
        """Test that RaftLeaderElectionAdapter satisfies RaftLeaderElectionPort protocol."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        assert isinstance(adapter, RaftLeaderElectionPort)

    def test_adapter_has_all_leader_election_methods(self) -> None:
        """Test that adapter has all LeaderElectionPort methods."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        assert hasattr(adapter, "is_leader_elected")
        assert hasattr(adapter, "elect_as_leader")
        assert hasattr(adapter, "demote_from_leader")

    def test_adapter_has_all_raft_methods(self) -> None:
        """Test that adapter has all RaftLeaderElectionPort methods."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        assert hasattr(adapter, "get_cluster_members")
        assert hasattr(adapter, "is_member_in_cluster")
        assert hasattr(adapter, "get_election_timeout")
        assert hasattr(adapter, "get_heartbeat_interval")
        assert hasattr(adapter, "is_quorum_reached")


@pytest.mark.unit
class TestRaftLeaderElectionAdapterConstructor:
    """Test RaftLeaderElectionAdapter constructor and initialization."""

    def test_constructor_accepts_raft_port(self) -> None:
        """Test that constructor accepts RaftLeaderElectionPort."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        assert adapter is not None

    def test_constructor_stores_raft_port(self) -> None:
        """Test that constructor stores the RaftLeaderElectionPort."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        # Access internal state to verify storage
        assert adapter._raft_port is mock_raft_port

    def test_constructor_requires_raft_port(self) -> None:
        """Test that constructor requires a RaftLeaderElectionPort argument."""
        # Try to instantiate without argument - should fail
        with pytest.raises(TypeError):
            RaftLeaderElectionAdapter()  # type: ignore


@pytest.mark.unit
class TestRaftLeaderElectionAdapterDelegation:
    """Test that RaftLeaderElectionAdapter delegates to the wrapped port."""

    def test_is_leader_elected_delegates_to_port(self) -> None:
        """Test that is_leader_elected() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.is_leader_elected.return_value = True

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.is_leader_elected()

        assert result is True
        mock_raft_port.is_leader_elected.assert_called_once()

    def test_is_leader_elected_returns_false(self) -> None:
        """Test that is_leader_elected() returns False from port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.is_leader_elected.return_value = False

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.is_leader_elected()

        assert result is False
        mock_raft_port.is_leader_elected.assert_called_once()

    def test_elect_as_leader_delegates_to_port(self) -> None:
        """Test that elect_as_leader() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.elect_as_leader.return_value = None

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        adapter.elect_as_leader()

        mock_raft_port.elect_as_leader.assert_called_once()

    def test_demote_from_leader_delegates_to_port(self) -> None:
        """Test that demote_from_leader() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.demote_from_leader.return_value = None

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        adapter.demote_from_leader()

        mock_raft_port.demote_from_leader.assert_called_once()

    def test_get_cluster_members_delegates_to_port(self) -> None:
        """Test that get_cluster_members() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.get_cluster_members.return_value = ["node-1", "node-2", "node-3"]

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.get_cluster_members()

        assert result == ["node-1", "node-2", "node-3"]
        mock_raft_port.get_cluster_members.assert_called_once()

    def test_get_cluster_members_returns_empty_list(self) -> None:
        """Test that get_cluster_members() returns empty list from port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.get_cluster_members.return_value = []

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.get_cluster_members()

        assert result == []
        mock_raft_port.get_cluster_members.assert_called_once()

    def test_is_member_in_cluster_delegates_to_port(self) -> None:
        """Test that is_member_in_cluster() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.is_member_in_cluster.return_value = True

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.is_member_in_cluster("node-1")

        assert result is True
        mock_raft_port.is_member_in_cluster.assert_called_once_with("node-1")

    def test_is_member_in_cluster_returns_false(self) -> None:
        """Test that is_member_in_cluster() returns False from port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.is_member_in_cluster.return_value = False

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.is_member_in_cluster("node-1")

        assert result is False
        mock_raft_port.is_member_in_cluster.assert_called_once_with("node-1")

    def test_is_member_in_cluster_passes_node_id_correctly(self) -> None:
        """Test that is_member_in_cluster() passes node ID to port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.is_member_in_cluster.return_value = True

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        adapter.is_member_in_cluster("my-custom-node-id")

        mock_raft_port.is_member_in_cluster.assert_called_once_with("my-custom-node-id")

    def test_get_election_timeout_delegates_to_port(self) -> None:
        """Test that get_election_timeout() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.get_election_timeout.return_value = 5.0

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.get_election_timeout()

        assert result == 5.0
        mock_raft_port.get_election_timeout.assert_called_once()

    def test_get_election_timeout_returns_different_values(self) -> None:
        """Test that get_election_timeout() returns various values from port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.get_election_timeout.return_value = 10.5

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.get_election_timeout()

        assert result == 10.5

    def test_get_heartbeat_interval_delegates_to_port(self) -> None:
        """Test that get_heartbeat_interval() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.get_heartbeat_interval.return_value = 1.0

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.get_heartbeat_interval()

        assert result == 1.0
        mock_raft_port.get_heartbeat_interval.assert_called_once()

    def test_get_heartbeat_interval_returns_different_values(self) -> None:
        """Test that get_heartbeat_interval() returns various values from port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.get_heartbeat_interval.return_value = 0.5

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.get_heartbeat_interval()

        assert result == 0.5

    def test_is_quorum_reached_delegates_to_port(self) -> None:
        """Test that is_quorum_reached() delegates to wrapped port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.is_quorum_reached.return_value = True

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.is_quorum_reached()

        assert result is True
        mock_raft_port.is_quorum_reached.assert_called_once()

    def test_is_quorum_reached_returns_false(self) -> None:
        """Test that is_quorum_reached() returns False from port."""
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        mock_raft_port.is_quorum_reached.return_value = False

        adapter = RaftLeaderElectionAdapter(mock_raft_port)
        result = adapter.is_quorum_reached()

        assert result is False
        mock_raft_port.is_quorum_reached.assert_called_once()


@pytest.mark.unit
class TestRaftLeaderElectionAdapterCleanArchitecture:
    """Test that adapter follows Clean Architecture principles."""

    def test_adapter_module_has_no_direct_py_leader_imports(self) -> None:
        """Test that adapter doesn't directly import py-leader/pysyncobj.

        This ensures py-leader is only used through the RaftLeaderElectionPort
        abstraction, not directly imported in this adapter module.
        """
        import inspect
        import re

        # Get the adapter module
        from litefs.adapters import raft_leader_election_adapter

        module_source = inspect.getsource(raft_leader_election_adapter)

        # Check for actual import statements (not just mentions in docstrings)
        # Match: "from pysyncobj import", "import pysyncobj", "from py_leader import"
        forbidden_patterns = [
            r"^\s*(from\s+pysyncobj|import\s+pysyncobj)",
            r"^\s*(from\s+py[_\-]?leader|import\s+py[_\-]?leader)",
        ]

        for pattern in forbidden_patterns:
            matches = re.findall(pattern, module_source, re.MULTILINE | re.IGNORECASE)
            assert not matches, f"Found forbidden import pattern: {pattern}"

    def test_adapter_only_wraps_port_interface(self) -> None:
        """Test that adapter has minimal implementation (pure wrapper).

        A thin adapter should only wrap and delegate, with no business logic.
        """
        mock_raft_port: Mock = Mock(spec=RaftLeaderElectionPort)
        adapter = RaftLeaderElectionAdapter(mock_raft_port)

        # Set up multiple return values to verify pure delegation
        mock_raft_port.is_leader_elected.return_value = True
        mock_raft_port.get_cluster_members.return_value = ["node-1", "node-2"]
        mock_raft_port.get_election_timeout.return_value = 5.0
        mock_raft_port.is_quorum_reached.return_value = True

        # Call all methods - each should delegate exactly once
        adapter.is_leader_elected()
        adapter.get_cluster_members()
        adapter.get_election_timeout()
        adapter.is_quorum_reached()

        # Verify each method was called exactly once (no logic, just delegation)
        mock_raft_port.is_leader_elected.assert_called_once()
        mock_raft_port.get_cluster_members.assert_called_once()
        mock_raft_port.get_election_timeout.assert_called_once()
        mock_raft_port.is_quorum_reached.assert_called_once()
