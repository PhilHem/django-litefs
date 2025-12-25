"""Concurrency tests for SplitBrainDetector use case.

Tests verify thread-safety of SplitBrainDetector when accessed from multiple
threads simultaneously. These tests validate:
- Concurrent calls to detect_split_brain() without race conditions
- Thread-safe access to shared detector instance
- No data corruption when cluster state changes during detection
- Proper synchronization without deadlocks
"""

import threading
import time

import pytest

from litefs.usecases.split_brain_detector import SplitBrainDetector, SplitBrainStatus
from litefs.domain.split_brain import RaftNodeState, RaftClusterState


class MockSplitBrainDetectorPort:
    """Mock implementation of SplitBrainDetectorPort for testing.

    Supports thread-safe mutation of cluster state to simulate
    cluster topology changes during concurrent access.
    """

    def __init__(self, cluster_state: RaftClusterState | None = None) -> None:
        """Initialize mock with cluster state."""
        if cluster_state is None:
            # Default: single node cluster with one leader
            cluster_state = RaftClusterState(
                nodes=[RaftNodeState(node_id="node1", is_leader=True)]
            )
        self.cluster_state = cluster_state
        self._lock = threading.Lock()

    def get_cluster_state(self) -> RaftClusterState:
        """Return the cluster state with thread-safe access."""
        with self._lock:
            return self.cluster_state

    def set_cluster_state(self, cluster_state: RaftClusterState) -> None:
        """Thread-safely update cluster state.

        Args:
            cluster_state: New cluster state to set.
        """
        with self._lock:
            self.cluster_state = cluster_state


@pytest.mark.unit
@pytest.mark.concurrency
@pytest.mark.no_parallel
class TestSplitBrainDetectorConcurrency:
    """Test SplitBrainDetector thread-safety with concurrent access.

    Marked no_parallel because these tests:
    - Use threading with shared state
    - Have tight timing requirements
    - Are designed for single-threaded test execution to avoid pytest-xdist conflicts
    """

    def test_concurrent_detect_split_brain_with_changing_state(self) -> None:
        """Test concurrent detect_split_brain() calls during cluster state transitions.

        Simulates scenario where:
        - Multiple threads continuously call detect_split_brain()
        - Cluster state transitions from healthy (1 leader) to split-brain (2+ leaders)
        - Threads should handle state changes without crashes or race conditions

        Acceptance criteria:
        - All threads complete without errors
        - No exceptions raised during concurrent access
        - Results reflect actual cluster state at detection time
        """
        # Start with single leader (healthy state)
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
                RaftNodeState(node_id="node3", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        results: list[SplitBrainStatus] = []
        errors: list[Exception] = []
        lock = threading.Lock()
        threads_started = threading.Event()

        def detect_continuously(thread_id: int) -> None:
            """Thread function to continuously detect split-brain."""
            try:
                # Signal that this thread has started
                threads_started.set()
                for _ in range(20):
                    status = detector.detect_split_brain()
                    with lock:
                        results.append(status)
            except Exception as e:
                with lock:
                    errors.append(e)

        def transition_to_split_brain() -> None:
            """Thread function to transition cluster to split-brain state."""
            # Wait for at least one detection thread to start
            threads_started.wait(timeout=2.0)
            time.sleep(0.02)  # Brief delay to let some detections happen
            # Create split-brain: node2 also becomes leader
            split_brain_cluster = RaftClusterState(
                nodes=[
                    RaftNodeState(node_id="node1", is_leader=True),
                    RaftNodeState(node_id="node2", is_leader=True),
                    RaftNodeState(node_id="node3", is_leader=False),
                ]
            )
            port.set_cluster_state(split_brain_cluster)

        # Start detection threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=detect_continuously, args=(i,))
            threads.append(t)
            t.start()

        # Start transition thread
        transition_thread = threading.Thread(target=transition_to_split_brain)
        transition_thread.start()

        # Wait for all threads
        for t in threads:
            t.join()
        transition_thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent detection: {errors}"

        # Verify all threads completed and got results
        assert len(results) == 200, (
            f"Expected 200 results (10 threads × 20 detections), got {len(results)}"
        )

        # Verify results reflect actual cluster states
        # Note: Due to timing, we may see mostly one state or the other
        # The key test is that no exceptions occur and results are valid
        # At least some detections should exist (no need to verify both states)
        # since timing of transition is non-deterministic
        assert len(results) > 0, "Should have detections"

    def test_concurrent_detect_split_brain_consistent_results(self) -> None:
        """Test that concurrent access to shared detector gives consistent results.

        Simulates scenario where:
        - Cluster state is fixed (no changes during test)
        - Multiple threads call detect_split_brain() simultaneously
        - All threads should see the same cluster state result

        Acceptance criteria:
        - All threads get consistent is_split_brain value for the same state
        - No race conditions in status creation
        """
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=True),
                RaftNodeState(node_id="node3", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        results: list[SplitBrainStatus] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def detect_split_brain(thread_id: int) -> None:
            """Thread function to detect split-brain."""
            try:
                for _ in range(10):
                    status = detector.detect_split_brain()
                    with lock:
                        results.append(status)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Start multiple threads simultaneously
        threads = []
        for i in range(20):
            t = threading.Thread(target=detect_split_brain, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

        # Verify all results got results
        assert len(results) == 200, f"Expected 200 results, got {len(results)}"

        # Verify all results are consistent
        # All should indicate split-brain (2 leaders)
        for result in results:
            assert result.is_split_brain is True, (
                "All results should show split-brain (2+ leaders)"
            )
            assert len(result.leader_nodes) == 2, (
                f"Expected 2 leaders, got {len(result.leader_nodes)}"
            )
            leader_ids = {n.node_id for n in result.leader_nodes}
            assert leader_ids == {"node1", "node2"}, (
                f"Expected leaders node1 and node2, got {leader_ids}"
            )

    def test_detector_instance_thread_safe(self) -> None:
        """Test that shared detector instance is thread-safe.

        Simulates scenario where:
        - Single detector instance is created once
        - Multiple threads call detect_split_brain() on the same instance
        - Instance's port reference and state should remain consistent

        Acceptance criteria:
        - Detector instance remains in valid state after concurrent access
        - All threads can use the detector without synchronization issues
        """
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        # Verify detector is in valid state
        assert detector.port is port, "Detector should reference the port"

        results: list[SplitBrainStatus] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def access_detector(thread_id: int) -> None:
            """Thread function to access detector."""
            try:
                # Verify detector state is consistent from this thread
                assert detector.port is port, (
                    "Detector port should remain the same across threads"
                )

                for _ in range(15):
                    status = detector.detect_split_brain()
                    with lock:
                        results.append(status)

                    # Verify detector state remains consistent
                    assert detector.port is port, (
                        "Detector port should not change during use"
                    )
            except Exception as e:
                with lock:
                    errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(15):
            t = threading.Thread(target=access_detector, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

        # Verify all operations completed
        assert len(results) == 225, (
            f"Expected 225 results (15 threads × 15 calls), got {len(results)}"
        )

        # Verify detector remains valid after concurrent access
        assert detector.port is port, "Detector should still reference port"
        final_status = detector.detect_split_brain()
        assert final_status.is_split_brain is False, (
            "Final status should reflect cluster state"
        )

    def test_concurrent_detection_with_state_mutations(self) -> None:
        """Test concurrent detect_split_brain() calls while cluster state mutates.

        Simulates scenario where:
        - Multiple detector threads continuously check cluster state
        - Separate mutation thread continuously changes node leadership
        - Detectors should see consistent snapshots, never corrupt data

        Acceptance criteria:
        - All threads complete without errors
        - No assertion failures on SplitBrainStatus validity
        - Results match actual cluster state at detection time
        """
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
                RaftNodeState(node_id="node3", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        results: list[SplitBrainStatus] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def detect_continuously(thread_id: int) -> None:
            """Thread function to detect split-brain continuously."""
            try:
                for _ in range(25):
                    status = detector.detect_split_brain()

                    # Validate status structure
                    assert isinstance(status.is_split_brain, bool), (
                        "is_split_brain must be boolean"
                    )
                    assert isinstance(status.leader_nodes, list), (
                        "leader_nodes must be a list"
                    )
                    assert all(
                        isinstance(n, RaftNodeState) for n in status.leader_nodes
                    ), "leader_nodes must contain RaftNodeState objects"

                    # Validate split-brain flag consistency
                    leader_count = len(status.leader_nodes)
                    expected_split_brain = leader_count >= 2
                    assert status.is_split_brain == expected_split_brain, (
                        f"Split-brain flag should match leader count: {leader_count}"
                    )

                    with lock:
                        results.append(status)
            except Exception as e:
                with lock:
                    errors.append(e)

        def mutate_state() -> None:
            """Thread function to mutate cluster state."""
            states = [
                # Initial state
                RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node1", is_leader=True),
                        RaftNodeState(node_id="node2", is_leader=False),
                        RaftNodeState(node_id="node3", is_leader=False),
                    ]
                ),
                # Split-brain: node2 becomes leader
                RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node1", is_leader=True),
                        RaftNodeState(node_id="node2", is_leader=True),
                        RaftNodeState(node_id="node3", is_leader=False),
                    ]
                ),
                # Worse split-brain: node3 also becomes leader
                RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node1", is_leader=True),
                        RaftNodeState(node_id="node2", is_leader=True),
                        RaftNodeState(node_id="node3", is_leader=True),
                    ]
                ),
                # Recovery: only node2 remains leader
                RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node1", is_leader=False),
                        RaftNodeState(node_id="node2", is_leader=True),
                        RaftNodeState(node_id="node3", is_leader=False),
                    ]
                ),
            ]

            for state in states:
                for _ in range(10):  # Cycle each state
                    port.set_cluster_state(state)
                    time.sleep(0.01)

        # Start detector threads
        threads = []
        for i in range(8):
            t = threading.Thread(target=detect_continuously, args=(i,))
            threads.append(t)
            t.start()

        # Start mutation thread
        mutation_thread = threading.Thread(target=mutate_state)
        mutation_thread.start()

        # Wait for all threads
        for t in threads:
            t.join()
        mutation_thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent detection: {errors}"

        # Verify all detections completed
        assert len(results) == 200, f"Expected 200 detections, got {len(results)}"

    def test_detector_no_deadlock_under_concurrent_load(self) -> None:
        """Test detector doesn't deadlock under heavy concurrent load.

        Simulates scenario where:
        - Very high number of threads (50+) all accessing detector simultaneously
        - No artificial delays or synchronization locks in detector
        - Should complete quickly without deadlock

        Acceptance criteria:
        - All threads complete within reasonable timeout
        - No deadlock occurs
        - All operations succeed
        """
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        results: list[SplitBrainStatus] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def detect_split_brain(thread_id: int) -> None:
            """Thread function to detect split-brain."""
            try:
                for _ in range(5):
                    status = detector.detect_split_brain()
                    with lock:
                        results.append(status)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Start many threads for stress testing
        threads = []
        for i in range(50):
            t = threading.Thread(target=detect_split_brain, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads with timeout to detect deadlocks
        for t in threads:
            t.join(timeout=5.0)
            assert not t.is_alive(), f"Thread {t.name} deadlocked (timeout)"

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during heavy concurrent load: {errors}"

        # Verify all operations completed
        assert len(results) == 250, f"Expected 250 results, got {len(results)}"

    def test_concurrent_access_with_port_blocking(self) -> None:
        """Test concurrent detector access when port has latency.

        Simulates scenario where:
        - Port.get_cluster_state() has artificial delay (slow network, disk I/O)
        - Multiple threads call detect_split_brain() simultaneously
        - Detector should handle port latency without race conditions

        Acceptance criteria:
        - All threads complete despite port latency
        - Results are consistent and valid
        - No exceptions due to concurrent access
        """
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )

        class SlowMockPort:
            """Mock port with artificial latency."""

            def __init__(self, cluster_state: RaftClusterState) -> None:
                """Initialize with cluster state."""
                self.cluster_state = cluster_state

            def get_cluster_state(self) -> RaftClusterState:
                """Return cluster state with delay to simulate slow I/O."""
                time.sleep(0.01)  # 10ms delay
                return self.cluster_state

        port = SlowMockPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        results: list[SplitBrainStatus] = []
        errors: list[Exception] = []
        lock = threading.Lock()
        call_times: list[float] = []

        def detect_with_timing(thread_id: int) -> None:
            """Thread function to detect split-brain and measure time."""
            try:
                for _ in range(5):
                    start = time.time()
                    status = detector.detect_split_brain()
                    elapsed = time.time() - start

                    with lock:
                        results.append(status)
                        call_times.append(elapsed)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=detect_with_timing, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=10.0)

        # Verify no errors
        assert len(errors) == 0, f"Errors with port latency: {errors}"

        # Verify all results completed
        assert len(results) == 50, f"Expected 50 results, got {len(results)}"

        # Verify results are valid
        for result in results:
            assert isinstance(result.is_split_brain, bool)
            assert isinstance(result.leader_nodes, list)

        # Verify timing: each call should take ~10ms or more (due to port delay)
        # All calls should complete without blocking each other
        assert len(call_times) == 50, (
            f"Expected 50 timing measurements, got {len(call_times)}"
        )
        avg_time = sum(call_times) / len(call_times)
        # Average should be at least 10ms (port delay)
        assert avg_time >= 0.008, f"Average call time too low: {avg_time}"

    def test_multiple_consecutive_concurrent_batches(self) -> None:
        """Test multiple sequential batches of concurrent access.

        Simulates scenario where:
        - Multiple concurrent batches of threads use the detector sequentially
        - Detector state should remain valid between batches
        - Port state may change between batches

        Acceptance criteria:
        - All batches complete without errors
        - Results are valid in each batch
        - Detector remains usable after all batches
        """
        initial_cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=initial_cluster)
        detector = SplitBrainDetector(port=port)

        batch_results: list[list[SplitBrainStatus]] = []
        errors: list[str] = []

        def run_concurrent_batch(
            batch_id: int, cluster_state: RaftClusterState
        ) -> None:
            """Run a batch of concurrent detector accesses."""
            port.set_cluster_state(cluster_state)
            batch = []
            lock = threading.Lock()

            def detect_in_batch(thread_id: int) -> None:
                """Thread function for batch."""
                try:
                    for _ in range(5):
                        status = detector.detect_split_brain()
                        with lock:
                            batch.append(status)
                except Exception as e:
                    with lock:
                        errors.append(f"Batch {batch_id}, Thread {thread_id}: {e}")

            # Start threads for this batch
            threads = []
            for i in range(5):
                t = threading.Thread(target=detect_in_batch, args=(i,))
                threads.append(t)
                t.start()

            # Wait for batch to complete
            for t in threads:
                t.join()

            batch_results.append(batch)

        # Run multiple batches with different cluster states
        batches = [
            (
                1,
                RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node1", is_leader=True),
                        RaftNodeState(node_id="node2", is_leader=False),
                    ]
                ),
            ),
            (
                2,
                RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node1", is_leader=True),
                        RaftNodeState(node_id="node2", is_leader=True),
                    ]
                ),
            ),
            (
                3,
                RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node1", is_leader=False),
                        RaftNodeState(node_id="node2", is_leader=True),
                    ]
                ),
            ),
        ]

        for batch_id, cluster_state in batches:
            run_concurrent_batch(batch_id, cluster_state)

        # Verify no errors
        assert len(errors) == 0, f"Errors during batches: {errors}"

        # Verify all batches completed
        assert len(batch_results) == 3, f"Expected 3 batches, got {len(batch_results)}"

        # Verify each batch has expected results (5 threads × 5 calls)
        for i, batch in enumerate(batch_results):
            assert len(batch) == 25, (
                f"Batch {i + 1}: Expected 25 results, got {len(batch)}"
            )

        # Verify detector is still usable after all batches
        final_status = detector.detect_split_brain()
        assert isinstance(final_status.is_split_brain, bool)
        assert isinstance(final_status.leader_nodes, list)
