"""Tests for litefs_django.adapters module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from litefs_django.adapters import StaticLeaderElection

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.StaticLeaderElection.is_leader_elected")
class TestStaticLeaderElection:
    """Tests for StaticLeaderElection adapter."""

    def test_is_leader_elected_returns_true_when_primary(self) -> None:
        """Test is_leader_elected returns True when node is primary."""
        mock_initializer: Mock = Mock(spec=["is_primary"])
        mock_initializer.is_primary.return_value = True

        election = StaticLeaderElection(mock_initializer, "node1")

        assert election.is_leader_elected() is True
        mock_initializer.is_primary.assert_called_once_with("node1")

    def test_is_leader_elected_returns_false_when_replica(self) -> None:
        """Test is_leader_elected returns False when node is replica."""
        mock_initializer: Mock = Mock(spec=["is_primary"])
        mock_initializer.is_primary.return_value = False

        election = StaticLeaderElection(mock_initializer, "node2")

        assert election.is_leader_elected() is False
        mock_initializer.is_primary.assert_called_once_with("node2")

    def test_elect_as_leader_is_noop(self) -> None:
        """Test elect_as_leader does nothing (static mode)."""
        mock_initializer: Mock = Mock(spec=["is_primary"])

        election = StaticLeaderElection(mock_initializer, "node1")

        # Should not raise
        election.elect_as_leader()
        # No calls to initializer
        mock_initializer.is_primary.assert_not_called()

    def test_demote_from_leader_is_noop(self) -> None:
        """Test demote_from_leader does nothing (static mode)."""
        mock_initializer: Mock = Mock(spec=["is_primary"])

        election = StaticLeaderElection(mock_initializer, "node1")

        # Should not raise
        election.demote_from_leader()
        # No calls to initializer
        mock_initializer.is_primary.assert_not_called()

    def test_implements_leader_election_port(self) -> None:
        """Test StaticLeaderElection implements LeaderElectionPort."""
        from litefs.adapters.ports import LeaderElectionPort

        mock_initializer: Mock = Mock(spec=["is_primary"])
        election = StaticLeaderElection(mock_initializer, "node1")

        assert isinstance(election, LeaderElectionPort)

    def test_consistent_leadership_status(self) -> None:
        """Test multiple calls return consistent results."""
        mock_initializer: Mock = Mock(spec=["is_primary"])
        mock_initializer.is_primary.return_value = True

        election = StaticLeaderElection(mock_initializer, "node1")

        # Multiple calls should return same result
        assert election.is_leader_elected() is True
        assert election.is_leader_elected() is True
        assert election.is_leader_elected() is True

        assert mock_initializer.is_primary.call_count == 3
