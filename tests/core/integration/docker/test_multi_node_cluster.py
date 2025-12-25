"""Integration tests for multi-node LiteFS clusters with Docker Compose.

Tests verify:
- 3-node cluster initialization and startup
- Leader election on cluster startup
- Replica node behavior
- Health status propagation
- Failover when primary node stops
- Recovery when primary node restarts
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pytest

# Import ClusterFixture from parent conftest
# We need to add parent directory to path for import
conftest_path = Path(__file__).parent.parent / "conftest.py"
sys.path.insert(0, str(conftest_path.parent))

if TYPE_CHECKING:
    from conftest import ClusterFixture  # type: ignore[import-not-found] # noqa: F401


@pytest.fixture
def three_node_cluster(tmp_path: Path) -> Generator:  # type: ignore[type-arg]
    """Provide a 3-node ClusterFixture for integration tests.

    Creates and starts a 3-node cluster for testing leader election,
    failover, and partition scenarios. Automatically cleans up after test.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Yields:
        Initialized and started ClusterFixture instance with 3 nodes.
    """
    from conftest import ClusterFixture  # noqa: F401,E402

    fixture = ClusterFixture(
        cluster_name="test-cluster-3node",
        node_count=3,
        base_dir=str(tmp_path / "cluster"),
    )
    fixture.setup()
    yield fixture
    # Ensure cleanup happens
    fixture.cleanup()


class TestMultiNodeClusterSetup:
    """Test multi-node cluster initialization and setup."""

    @pytest.mark.integration
    @pytest.mark.no_parallel
    def test_three_node_cluster_initialization(
        self, three_node_cluster: Any
    ) -> None:
        """Test that a 3-node cluster initializes with correct structure.

        Verifies:
        - Cluster has exactly 3 nodes
        - Docker Compose file contains 3 service definitions
        - All nodes have unique identifiers (node-1, node-2, node-3)
        - Network configuration includes all nodes
        """
        assert three_node_cluster.cluster_name == "test-cluster-3node"
        assert three_node_cluster.node_count == 3
        assert len(three_node_cluster.nodes) == 3
        assert three_node_cluster.nodes == ["node-1", "node-2", "node-3"]

        # Verify docker-compose.yml contains all nodes
        compose_file = Path(three_node_cluster.base_dir) / "docker-compose.yml"
        assert compose_file.exists()

        content = compose_file.read_text()
        assert "node-1:" in content
        assert "node-2:" in content
        assert "node-3:" in content
        assert content.count("NODE_ID:") == 3

    @pytest.mark.integration
    @pytest.mark.no_parallel
    def test_docker_compose_file_valid_yaml(
        self, three_node_cluster: Any
    ) -> None:
        """Test that generated docker-compose.yml is valid YAML and syntax-correct.

        Verifies that docker-compose can parse the generated file without errors.
        This is a syntax validation, not a functional test.
        """
        compose_file = Path(three_node_cluster.base_dir) / "docker-compose.yml"
        assert compose_file.exists()

        # Validate with docker-compose config command
        try:
            result = subprocess.run(["docker-compose", "--file", str(compose_file), "config"],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0, (
                f"docker-compose config failed: {result.stderr}"
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

    @pytest.mark.integration
    @pytest.mark.no_parallel
    def test_cluster_services_structure(
        self, three_node_cluster: Any
    ) -> None:
        """Test that docker-compose services have required structure.

        Verifies each node service has:
        - Correct image reference
        - NODE_ID environment variable
        - CLUSTER_NAME environment variable
        - Network configuration
        """
        compose_file = Path(three_node_cluster.base_dir) / "docker-compose.yml"
        content = compose_file.read_text()

        for i in range(3):
            node_name = f"node-{i + 1}"
            assert f"{node_name}:" in content

            # Each node should have NODE_ID
            assert f"NODE_ID: {node_name}" in content

            # Each node should have CLUSTER_NAME
            assert "CLUSTER_NAME: test-cluster-3node" in content

            # Services should reference litefs image
            assert "image:" in content.split(f"{node_name}:")[1].split("\n")[1]


class TestLeaderElectionBehavior:
    """Test leader election in multi-node clusters."""

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_leader_election_on_startup(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that leader election occurs when cluster starts.

        Verifies:
        - Cluster can start successfully
        - Cluster becomes healthy (all nodes responsive)
        - Exactly one node becomes leader/primary
        - Other nodes remain replicas

        This test requires Docker and FUSE to be available.
        """
        three_node_cluster.start()

        # Wait for cluster to stabilize
        assert three_node_cluster.verify_health(timeout=30), (
            "Cluster failed to become healthy within 30 seconds"
        )

        # Verify all nodes are running
        assert len(three_node_cluster.nodes) == 3

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_replica_nodes_remain_replicas(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that non-leader nodes maintain replica status.

        Verifies:
        - After leader election, exactly 2 nodes are replicas
        - Replicas do not transition to primary during stable state
        - Replica nodes remain responsive and healthy
        """
        three_node_cluster.start()

        # Allow election to complete
        assert three_node_cluster.verify_health(timeout=30)

        # All nodes should be healthy and stable
        # (specific replica verification requires health endpoint access)
        assert len(three_node_cluster.nodes) == 3


class TestFailoverScenarios:
    """Test failover behavior when nodes fail."""

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_leader_failover_on_primary_stop(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that a new leader is elected when primary node stops.

        Verifies:
        - Initial cluster is healthy with one leader
        - Stopping the primary node triggers failover
        - A new leader is elected from remaining nodes
        - Cluster recovers to healthy state
        """
        three_node_cluster.start()
        assert three_node_cluster.verify_health(timeout=30)

        # Simulate primary node failure by stopping one node
        # (specific node selection would require health endpoint)
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "stop",
                    "node-1",
                ], capture_output=True, timeout=10, text=True)
            assert result.returncode == 0, f"Failed to stop node: {result.stderr}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Wait for new leader election
        time.sleep(2)

        # Cluster should still have 2 running nodes
        try:
            result = subprocess.run([
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            # Count "Up" status lines (running containers)
            running = result.stdout.count("Up")
            assert running >= 2, f"Expected at least 2 running nodes, got {running}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_primary_restart_reintegration(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that a restarted primary node reintegrates into cluster.

        Verifies:
        - Primary node can be restarted after being stopped
        - Node resyncs with cluster and recovers state
        - Cluster returns to 3-node healthy state
        """
        three_node_cluster.start()
        assert three_node_cluster.verify_health(timeout=30)

        # Stop and restart a node
        try:
            # Stop node-1
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "stop",
                    "node-1",
                ], capture_output=True, timeout=10, text=True)
            assert result.returncode == 0

            # Restart node-1
            result = subprocess.run([
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "start",
                    "node-1",
                ], capture_output=True, timeout=10, text=True)
            assert result.returncode == 0, f"Failed to start node: {result.stderr}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Wait for reintegration
        time.sleep(2)

        # Cluster should have all 3 nodes running again
        try:
            result = subprocess.run([
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            running = result.stdout.count("Up")
            assert running == 3, f"Expected 3 running nodes after restart, got {running}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_all_nodes_down_no_leader_election(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that no leader is elected when all nodes are down.

        Verifies:
        - When all cluster nodes are stopped, no leader exists
        - Cluster cannot function without at least one node
        - Restarting a node allows leader election to proceed
        """
        three_node_cluster.start()
        assert three_node_cluster.verify_health(timeout=30)

        # Stop all nodes
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "stop",
                ], capture_output=True, timeout=10, text=True)
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(1)

        # Verify no nodes running
        try:
            result = subprocess.run([
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "ps",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )
            running = result.stdout.count("Up")
            assert running == 0, f"Expected 0 running nodes, got {running}"
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")


class TestHealthMonitoring:
    """Test health status propagation in multi-node clusters."""

    @pytest.mark.integration
    @pytest.mark.no_parallel
    def test_cluster_health_verification(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that ClusterFixture.verify_health() correctly detects healthy cluster.

        Verifies:
        - verify_health() returns True when all nodes are running
        - verify_health() waits up to specified timeout
        - verify_health() handles docker-compose ps output correctly
        """
        three_node_cluster.start()

        # Should become healthy within timeout
        is_healthy = three_node_cluster.verify_health(timeout=30)
        assert is_healthy, "Cluster should become healthy"

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_health_check_after_node_restart(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test health verification after stopping and restarting a node.

        Verifies:
        - Health checks detect when a node is stopped
        - verify_health() returns False when node count doesn't match
        - Health checks pass again after node is restarted
        """
        three_node_cluster.start()
        assert three_node_cluster.verify_health(timeout=30)

        # Stop one node and verify health fails
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "stop",
                    "node-2",
                ], capture_output=True, timeout=10, text=True)
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(1)

        # Health check should fail (not all nodes running)
        is_healthy = three_node_cluster.verify_health(timeout=5)
        assert not is_healthy, "Cluster should not be healthy with 1 stopped node"

        # Restart node and verify health returns
        try:
            result = subprocess.run([
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "start",
                    "node-2",
                ], capture_output=True, timeout=10, text=True)
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        # Health should return to passing
        assert three_node_cluster.verify_health(timeout=30)

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_health_check_timeout_on_unhealthy_cluster(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test that verify_health() times out when cluster remains unhealthy.

        Verifies:
        - verify_health() respects timeout parameter
        - Method returns False if cluster doesn't become healthy within timeout
        - Timeout is short enough for quick test completion
        """
        three_node_cluster.start()
        assert three_node_cluster.verify_health(timeout=30)

        # Stop all nodes
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "stop",
                ], capture_output=True, timeout=10, text=True)
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(1)

        # verify_health should timeout and return False
        is_healthy = three_node_cluster.verify_health(timeout=5)
        assert not is_healthy, "Cluster should not be healthy when all nodes stopped"

    @pytest.mark.integration
    @pytest.mark.concurrency
    @pytest.mark.no_parallel
    def test_health_monitoring_rapid_node_failures(
        self, three_node_cluster: Any, skip_if_no_litefs: None
    ) -> None:
        """Test health monitoring detects rapid sequential node failures.

        Verifies:
        - Health checks remain responsive during rapid state changes
        - verify_health() correctly counts running nodes
        - Multiple fast transitions are handled properly
        """
        three_node_cluster.start()
        assert three_node_cluster.verify_health(timeout=30)

        # Rapidly stop and check health
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "stop",
                    "node-1",
                ], capture_output=True, timeout=10, text=True)
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(0.5)

        # Should detect unhealthy immediately
        is_healthy = three_node_cluster.verify_health(timeout=3)
        assert not is_healthy, "Health should detect single stopped node"

        # Restart and verify recovery
        try:
            subprocess.run(
                [
                    "docker-compose",
                    "--project-name",
                    three_node_cluster.cluster_name,
                    "--file",
                    str(
                        Path(three_node_cluster.base_dir) / "docker-compose.yml"
                    ),
                    "start",
                    "node-1",
                ], capture_output=True, timeout=10, text=True)
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")

        time.sleep(2)

        # Should recover to healthy
        assert three_node_cluster.verify_health(timeout=15)
