"""Unit tests for Django split-brain detection signals."""

import pytest
from unittest.mock import Mock

from litefs.domain.split_brain import RaftNodeState
from litefs.usecases.split_brain_detector import SplitBrainStatus
from litefs_django.signals import split_brain_detected


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestSplitBrainSignals:
    """Test split-brain detection signals."""

    def test_split_brain_signal_is_django_signal(self) -> None:
        """split_brain_detected should be a Django signal."""
        from django.dispatch import Signal

        assert isinstance(split_brain_detected, Signal)

    def test_split_brain_signal_can_be_connected(self) -> None:
        """split_brain_detected signal should support connect()."""
        receiver = Mock()
        split_brain_detected.connect(receiver)

        # Clean up
        split_brain_detected.disconnect(receiver)

    def test_split_brain_signal_can_send_status(self) -> None:
        """split_brain_detected signal should be able to send SplitBrainStatus."""
        # Create receiver to track signal
        signal_data = []

        def receiver(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            signal_data.append((sender, status))

        split_brain_detected.connect(receiver)

        try:
            # Create test status
            leader1 = RaftNodeState(node_id="node1", is_leader=True)
            leader2 = RaftNodeState(node_id="node2", is_leader=True)
            status = SplitBrainStatus(
                is_split_brain=True, leader_nodes=[leader1, leader2]
            )

            # Send signal
            split_brain_detected.send(sender=object(), status=status)

            # Assert: Receiver got the signal
            assert len(signal_data) == 1
            assert signal_data[0][1] is status
        finally:
            split_brain_detected.disconnect(receiver)

    def test_split_brain_signal_includes_is_split_brain_flag(self) -> None:
        """Signal should include is_split_brain flag in status."""
        signal_data = []

        def receiver(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            signal_data.append(status)

        split_brain_detected.connect(receiver)

        try:
            # Create status with is_split_brain=True
            leader1 = RaftNodeState(node_id="node1", is_leader=True)
            leader2 = RaftNodeState(node_id="node2", is_leader=True)
            status = SplitBrainStatus(
                is_split_brain=True, leader_nodes=[leader1, leader2]
            )

            split_brain_detected.send(sender=object(), status=status)

            # Assert: is_split_brain flag present and True
            assert signal_data[0].is_split_brain is True
        finally:
            split_brain_detected.disconnect(receiver)

    def test_split_brain_signal_includes_leader_nodes(self) -> None:
        """Signal should include list of leader nodes."""
        signal_data = []

        def receiver(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            signal_data.append(status)

        split_brain_detected.connect(receiver)

        try:
            # Create status with multiple leaders
            leader1 = RaftNodeState(node_id="node1", is_leader=True)
            leader2 = RaftNodeState(node_id="node2", is_leader=True)
            _replica = RaftNodeState(node_id="node3", is_leader=False)  # noqa: F841
            status = SplitBrainStatus(
                is_split_brain=True, leader_nodes=[leader1, leader2]
            )

            split_brain_detected.send(sender=object(), status=status)

            # Assert: leader_nodes contains both leaders
            assert len(signal_data[0].leader_nodes) == 2
            assert signal_data[0].leader_nodes[0].node_id == "node1"
            assert signal_data[0].leader_nodes[1].node_id == "node2"
        finally:
            split_brain_detected.disconnect(receiver)

    def test_split_brain_signal_with_single_leader_status(self) -> None:
        """Signal should work with healthy (single leader) status."""
        signal_data = []

        def receiver(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            signal_data.append(status)

        split_brain_detected.connect(receiver)

        try:
            # Create status with single leader (healthy)
            leader = RaftNodeState(node_id="node1", is_leader=True)
            _replica = RaftNodeState(node_id="node2", is_leader=False)  # noqa: F841
            status = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader])

            split_brain_detected.send(sender=object(), status=status)

            # Assert: Status correctly represents healthy state
            assert signal_data[0].is_split_brain is False
            assert len(signal_data[0].leader_nodes) == 1
        finally:
            split_brain_detected.disconnect(receiver)

    def test_split_brain_signal_with_no_leaders_status(self) -> None:
        """Signal should work with no-leader status (degraded)."""
        signal_data = []

        def receiver(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            signal_data.append(status)

        split_brain_detected.connect(receiver)

        try:
            # Create status with no leaders (degraded)
            _replica1 = RaftNodeState(node_id="node1", is_leader=False)  # noqa: F841
            _replica2 = RaftNodeState(node_id="node2", is_leader=False)  # noqa: F841
            status = SplitBrainStatus(is_split_brain=False, leader_nodes=[])

            split_brain_detected.send(sender=object(), status=status)

            # Assert: Status correctly represents degraded state
            assert signal_data[0].is_split_brain is False
            assert len(signal_data[0].leader_nodes) == 0
        finally:
            split_brain_detected.disconnect(receiver)

    def test_multiple_receivers_get_signal(self) -> None:
        """Multiple signal receivers should all be called."""
        receiver1_data = []
        receiver2_data = []

        def receiver1(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            receiver1_data.append(status)

        def receiver2(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            receiver2_data.append(status)

        split_brain_detected.connect(receiver1)
        split_brain_detected.connect(receiver2)

        try:
            # Create and send status
            leader1 = RaftNodeState(node_id="node1", is_leader=True)
            leader2 = RaftNodeState(node_id="node2", is_leader=True)
            status = SplitBrainStatus(
                is_split_brain=True, leader_nodes=[leader1, leader2]
            )

            split_brain_detected.send(sender=object(), status=status)

            # Assert: Both receivers got the signal
            assert len(receiver1_data) == 1
            assert len(receiver2_data) == 1
            assert receiver1_data[0] is status
            assert receiver2_data[0] is status
        finally:
            split_brain_detected.disconnect(receiver1)
            split_brain_detected.disconnect(receiver2)

    def test_signal_sender_is_configurable(self) -> None:
        """Signal should allow different sender objects (must be hashable)."""
        signal_data = []

        def receiver(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            signal_data.append((sender, status))

        split_brain_detected.connect(receiver)

        try:
            # Create test status
            leader = RaftNodeState(node_id="node1", is_leader=True)
            status = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader])

            # Send with different sender (must be hashable - use string or class)
            custom_sender = "middleware.detector"
            split_brain_detected.send(sender=custom_sender, status=status)

            # Assert: Sender is preserved
            assert signal_data[0][0] == custom_sender
        finally:
            split_brain_detected.disconnect(receiver)

    def test_signal_disconnect_prevents_further_calls(self) -> None:
        """Disconnected receiver should not be called again."""
        signal_data = []

        def receiver(
            sender: object, status: SplitBrainStatus, **kwargs: object
        ) -> None:
            signal_data.append(status)

        split_brain_detected.connect(receiver)

        # Create and send first signal
        leader = RaftNodeState(node_id="node1", is_leader=True)
        status1 = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader])
        split_brain_detected.send(sender=object(), status=status1)

        assert len(signal_data) == 1

        # Disconnect
        split_brain_detected.disconnect(receiver)

        # Send second signal
        status2 = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader])
        split_brain_detected.send(sender=object(), status=status2)

        # Assert: Receiver was not called for second signal
        assert len(signal_data) == 1
