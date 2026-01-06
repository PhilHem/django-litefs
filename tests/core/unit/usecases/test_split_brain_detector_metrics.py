"""Tests for SplitBrainDetector metrics integration."""

from __future__ import annotations

import pytest

from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from litefs.adapters.fakes.fake_metrics import FakeMetricsAdapter


class FakeSplitBrainDetectorPort:
    """Minimal fake for SplitBrainDetectorPort."""

    def __init__(self, nodes: list[RaftNodeState] | None = None) -> None:
        self._nodes = nodes or []

    def get_cluster_state(self) -> RaftClusterState:
        return RaftClusterState(nodes=self._nodes)

    def set_nodes(self, nodes: list[RaftNodeState]) -> None:
        """Test helper to change cluster state."""
        self._nodes = nodes


@pytest.mark.unit
class TestSplitBrainDetectorMetrics:
    """Tests for SplitBrainDetector metrics emission."""

    def test_emits_no_split_brain_metric_with_single_leader(self) -> None:
        """Should emit split_brain_detected=False with single leader."""
        metrics = FakeMetricsAdapter()
        port = FakeSplitBrainDetectorPort(
            nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=False),
                RaftNodeState(node_id="node-3", is_leader=False),
            ]
        )
        detector = SplitBrainDetector(port=port, metrics=metrics)

        result = detector.detect_split_brain()

        assert result.is_split_brain is False
        assert metrics.current_split_brain_detected is False

    def test_emits_split_brain_metric_with_multiple_leaders(self) -> None:
        """Should emit split_brain_detected=True with multiple leaders."""
        metrics = FakeMetricsAdapter()
        port = FakeSplitBrainDetectorPort(
            nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=True),  # Split brain!
                RaftNodeState(node_id="node-3", is_leader=False),
            ]
        )
        detector = SplitBrainDetector(port=port, metrics=metrics)

        result = detector.detect_split_brain()

        assert result.is_split_brain is True
        assert metrics.current_split_brain_detected is True

    def test_emits_no_split_brain_metric_with_no_leaders(self) -> None:
        """Should emit split_brain_detected=False with no leaders."""
        metrics = FakeMetricsAdapter()
        port = FakeSplitBrainDetectorPort(
            nodes=[
                RaftNodeState(node_id="node-1", is_leader=False),
                RaftNodeState(node_id="node-2", is_leader=False),
            ]
        )
        detector = SplitBrainDetector(port=port, metrics=metrics)

        result = detector.detect_split_brain()

        assert result.is_split_brain is False
        assert metrics.current_split_brain_detected is False

    def test_works_without_metrics(self) -> None:
        """Should work correctly when metrics not provided."""
        port = FakeSplitBrainDetectorPort(
            nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=False),
            ]
        )
        detector = SplitBrainDetector(port=port)

        # Should not raise
        result = detector.detect_split_brain()
        assert result.is_split_brain is False

    def test_metric_updated_on_each_detection(self) -> None:
        """Metrics should be updated on each detect_split_brain call."""
        metrics = FakeMetricsAdapter()
        port = FakeSplitBrainDetectorPort(
            nodes=[RaftNodeState(node_id="node-1", is_leader=True)]
        )
        detector = SplitBrainDetector(port=port, metrics=metrics)

        detector.detect_split_brain()
        assert len(metrics.calls) == 1

        detector.detect_split_brain()
        assert len(metrics.calls) == 2
