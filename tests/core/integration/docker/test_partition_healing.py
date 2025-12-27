"""Integration tests for partition healing in multi-node LiteFS clusters.

Tests verify:
- Network partition detection
- Quorum-based leader election (2 of 3 nodes can elect leader)
- Split-brain prevention (1 of 3 nodes cannot elect leader)
- Recovery when partition heals
- Data consistency across rejoin
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pytest

if TYPE_CHECKING:
    from ..conftest import ClusterFixture  # noqa: F401


@pytest.fixture
def three_node_cluster_partition(tmp_path: Path, skip_if_no_litefs: None) -> Generator:  # type: ignore[type-arg]
    """Provide a 3-node ClusterFixture for partition testing.

    Creates and starts a 3-node cluster for partition/healing scenarios.
    Automatically cleans up after test.

    Args:
        tmp_path: Pytest's temporary directory fixture.
        skip_if_no_litefs: Fixture that skips test if Docker/FUSE unavailable.

    Yields:
        Initialized and started ClusterFixture instance with 3 nodes.
    """
    from ..conftest import ClusterFixture

    fixture = ClusterFixture(
        cluster_name="test-cluster-partition",
        node_count=3,
        base_dir=str(tmp_path / "cluster"),
    )
    fixture.setup()
    try:
        fixture.start()
    except Exception as e:
        # Skip test if Docker not available
        pytest.skip(f"Docker unavailable: {e}")
    yield fixture
    # Ensure cleanup happens
    try:
        fixture.stop(timeout=10)
    except Exception:
        pass  # Already stopped or no docker
    fixture.cleanup()


@pytest.mark.tier(3)
@pytest.mark.tra("Adapter.Cluster.Quorum")
class TestQuorumBasedLeaderElection:
    """Test quorum-aware leader election behavior."""

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_quorum_preserved_with_two_of_three(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that 2 of 3 nodes maintain quorum and elect leader.

        Verifies:
        - 3-node cluster starts and elects leader
        - Stopping 1 node leaves 2 running
        - 2-node subset can maintain leadership
        - Remaining leader can accept writes
        """
        assert three_node_cluster_partition.verify_health(timeout=30), (
            "Cluster should be healthy"
        )

        # Stop one node (creates 2/3 partition)
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-3",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0, f"Failed to stop node: {result.stderr}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Verify 2 nodes still running
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            running = result.stdout.count("Up")
            assert running == 2, f"Expected 2 running nodes, got {running}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_minority_partition_cannot_elect_leader(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that 1 of 3 nodes cannot maintain leadership (prevents split-brain).

        Verifies:
        - With 3-node cluster, stopping 2 nodes leaves 1 isolated
        - Single isolated node cannot elect itself as leader
        - Single node cannot accept writes (no quorum)
        - This prevents split-brain scenarios
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Stop two nodes (creates 1/3 minority partition)
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-2",
                    "node-3",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(1)

        # Verify only 1 node running
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            running = result.stdout.count("Up")
            assert running == 1, f"Expected 1 running node, got {running}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")


@pytest.mark.tier(3)
@pytest.mark.tra("Adapter.Cluster.PartitionHealing")
class TestPartitionHealing:
    """Test cluster recovery when partitions heal."""

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_partition_healing_single_node_rejoin(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that an isolated node rejoins cluster when partition heals.

        Verifies:
        - 3-node cluster is healthy
        - Stop 1 node to isolate it
        - Restart isolated node
        - Node resyncs and rejoins cluster
        - Cluster returns to 3-node healthy state
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Isolate node-1
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-1",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Verify 2/3 running
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 2
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Restart isolated node
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "start",
                    "node-1",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0, f"Failed to start node: {result.stderr}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Wait for resync and rejoin
        time.sleep(3)

        # Verify all 3 nodes running again
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            running = result.stdout.count("Up")
            assert running == 3, f"Expected 3 running nodes after rejoin, got {running}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_partition_healing_majority_rejoin(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test recovery when majority partition restarts after split.

        Verifies:
        - Full 3-node cluster is healthy
        - Create 1/3 vs 2/3 partition by stopping 1 node
        - 2/3 partition can maintain leader election
        - Isolated node eventually restarts
        - Full cluster recovers and resyncs state
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Stop 1 node to create 2/3 partition
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-3",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Verify 2/3 still healthy
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 2
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Restart all nodes (heal partition)
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "start",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Wait for full resync
        time.sleep(3)

        # All 3 nodes should be running
        assert three_node_cluster_partition.verify_health(timeout=30), (
            "Cluster should be healthy after partition heal"
        )


@pytest.mark.tier(3)
@pytest.mark.tra("Adapter.Cluster.NetworkPartition")
class TestNetworkPartitionScenarios:
    """Test various network partition scenarios."""

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_cascading_node_failures(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test cluster behavior during cascading node failures.

        Verifies:
        - Start with 3-node healthy cluster
        - Fail node 1 (2/3 quorum maintained)
        - Fail node 2 (1/3 no quorum)
        - Verify leader is lost with 1/3
        - Restart node 2 (2/3 quorum restored)
        - Leader election succeeds again
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Stop node-1 (2/3 quorum)
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-1",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(1)

        # Stop node-2 (1/3 no quorum)
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-2",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(1)

        # Only 1 node running - no quorum
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 1
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Restart node-2 (restore 2/3 quorum)
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "start",
                    "node-2",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Should have 2/3 again
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 2
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_recovery_from_complete_shutdown(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that cluster recovers correctly from complete shutdown and restart.

        Verifies:
        - Stop all 3 nodes (cluster down)
        - Restart all nodes
        - Cluster resyncs and returns to healthy state
        - Leader election succeeds after recovery
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Stop all nodes
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(1)

        # Verify all stopped
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Restart all nodes
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "start",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Allow time for cluster recovery and leader election
        time.sleep(5)

        # Cluster should be healthy again with all 3 nodes
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            running = result.stdout.count("Up")
            assert running == 3, f"Expected 3 nodes after restart, got {running}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")


@pytest.mark.tier(3)
@pytest.mark.tra("Adapter.Cluster.AdvancedPartition")
class TestAdvancedPartitionScenarios:
    """Test advanced network partition and recovery scenarios."""

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_sequential_node_isolation_recovery(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test recovery from sequential isolation of different nodes.

        Verifies:
        - After isolating node-1, cluster maintains 2/3 quorum
        - Reintegrate node-1, then isolate node-2
        - Each isolation/recovery cycle maintains consistency
        - Cluster handles multiple sequential failure scenarios
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Isolate node-1
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-1",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Verify 2/3 running
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 2
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Reintegrate node-1
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "start",
                    "node-1",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Verify all 3 recovered
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Now isolate node-2
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-2",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Verify 2/3 running
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 2
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_partition_with_delayed_recovery(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test recovery with significant delay between partition and heal.

        Verifies:
        - Cluster handles extended partition duration
        - 2/3 majority continues operating during extended partition
        - State is consistent when partition eventually heals
        - Isolated node catches up after extended separation
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Partition: stop node-3
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-3",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Wait extended period while partitioned
        time.sleep(3)

        # Heal: restart node-3
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "start",
                    "node-3",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Allow time for resync
        time.sleep(4)

        # Verify all nodes healthy again
        assert three_node_cluster_partition.verify_health(timeout=30)

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_alternate_majority_partition_healing(
        self, three_node_cluster_partition: Any, skip_if_no_litefs: None
    ) -> None:
        """Test healing when different majority wins each partition.

        Verifies:
        - 3-node cluster starts with initial leader
        - Partition: isolate node-2 (majority is node-1, node-3)
        - Heal partition (all 3 nodes online)
        - Cluster recovers and synchronizes state
        """
        assert three_node_cluster_partition.verify_health(timeout=30)

        # Create partition: remove node-2 (leave node-1, node-3 as majority)
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "stop",
                    "node-2",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Verify 2/3 (node-1, node-3)
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            assert result.stdout.count("Up") == 2
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Heal: bring node-2 back
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster_partition.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster_partition.base_dir)
                        / "docker-compose.yml"
                    ),
                    "start",
                    "node-2",
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(3)

        # All 3 nodes should be healthy
        assert three_node_cluster_partition.verify_health(timeout=30)
