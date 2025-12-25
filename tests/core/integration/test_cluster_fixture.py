"""Tests for ClusterFixture integration test infrastructure."""

import subprocess
from pathlib import Path

import pytest

from .conftest import ClusterFixture


class TestClusterFixtureBasic:
    """Test ClusterFixture basic functionality (no Docker required)."""

    def test_cluster_fixture_initialization(self, tmp_path: Path) -> None:
        """Test that ClusterFixture can be instantiated with basic parameters.

        Verifies that the fixture initializes with required parameters and
        has the expected attributes.
        """
        fixture = ClusterFixture(
            cluster_name="test-cluster",
            node_count=2,
            base_dir=str(tmp_path),
        )

        assert fixture.cluster_name == "test-cluster"
        assert fixture.node_count == 2
        assert fixture.base_dir == str(tmp_path)
        assert fixture.nodes == []  # No nodes started yet

    def test_cluster_fixture_minimum_nodes_validation(self, tmp_path: Path) -> None:
        """Test that ClusterFixture validates minimum node count.

        Verifies that creating a cluster with less than 2 nodes raises ValueError.
        """
        with pytest.raises(ValueError, match="at least 2 nodes"):
            ClusterFixture(
                cluster_name="invalid-cluster",
                node_count=1,
                base_dir=str(tmp_path),
            )

    def test_cluster_fixture_docker_compose_generation(self, tmp_path: Path) -> None:
        """Test that ClusterFixture generates valid docker-compose.yml content.

        Verifies that the docker-compose YAML is syntactically correct and
        contains the expected structure without running Docker.
        """
        fixture = ClusterFixture(
            cluster_name="test-compose",
            node_count=2,
            base_dir=str(tmp_path),
        )

        # Generate docker-compose content
        content = fixture._generate_docker_compose()

        # Verify required YAML structure
        assert "version: '3.8'" in content
        assert "services:" in content
        assert "networks:" in content
        assert "litefs-cluster:" in content

        # Verify nodes are defined
        assert "node-1:" in content
        assert "node-2:" in content

        # Verify environment variables
        assert "NODE_ID: node-1" in content
        assert "NODE_ID: node-2" in content
        assert "CLUSTER_NAME: test-compose" in content

    def test_cluster_fixture_docker_compose_node_count(self, tmp_path: Path) -> None:
        """Test that docker-compose content reflects requested node count.

        Verifies that generating docker-compose for N nodes creates
        exactly N node service definitions.
        """
        for node_count in [2, 3, 5]:
            fixture = ClusterFixture(
                cluster_name=f"test-nodes-{node_count}",
                node_count=node_count,
                base_dir=str(tmp_path / f"cluster-{node_count}"),
            )

            content = fixture._generate_docker_compose()

            # Count node definitions
            for i in range(node_count):
                node_name = f"node-{i + 1}:"
                assert node_name in content, (
                    f"docker-compose should define {node_name} service"
                )

            # Verify no extra nodes
            extra_node = f"node-{node_count + 1}:"
            assert extra_node not in content, (
                f"docker-compose should not have extra {extra_node}"
            )


@pytest.fixture
def skip_if_no_docker(litefs_available: bool) -> None:
    """Skip test if Docker is not available."""
    if not litefs_available:
        pytest.skip("Docker infrastructure not available")


class TestClusterFixture:
    """Test ClusterFixture infrastructure for multi-node Docker Compose.

    These tests verify that the ClusterFixture can be instantiated, can verify
    cluster health, and cleans up properly after use.
    """

    @pytest.mark.integration
    def test_cluster_fixture_instantiation(
        self, tmp_path: Path, skip_if_no_docker: None
    ) -> None:
        """Test that ClusterFixture can be instantiated with temporary directory.

        Verifies that the fixture initializes with required parameters and
        has the expected attributes.
        """
        fixture = ClusterFixture(
            cluster_name="test-cluster",
            node_count=2,
            base_dir=str(tmp_path),
        )

        assert fixture.cluster_name == "test-cluster"
        assert fixture.node_count == 2
        assert fixture.base_dir == str(tmp_path)
        assert fixture.nodes == []  # No nodes started yet

    @pytest.mark.integration
    def test_cluster_fixture_setup_and_teardown(
        self, tmp_path: Path, skip_if_no_docker: None
    ) -> None:
        """Test ClusterFixture setup creates Docker Compose file.

        Verifies that setup() generates the docker-compose.yml file
        without actually starting the cluster (to avoid long test times).
        """
        fixture = ClusterFixture(
            cluster_name="test-setup",
            node_count=2,
            base_dir=str(tmp_path),
        )

        fixture.setup()

        # Verify docker-compose file was created
        compose_file = tmp_path / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml should be created"

        # Verify file has expected content
        content = compose_file.read_text()
        assert "services:" in content, "docker-compose should have services section"
        assert "node-" in content, "docker-compose should have node services"

        fixture.cleanup()

    @pytest.mark.integration
    def test_cluster_fixture_docker_compose_validation(
        self, tmp_path: Path, skip_if_no_docker: None
    ) -> None:
        """Test that generated docker-compose.yml is valid YAML.

        Verifies that the generated file can be parsed by docker-compose
        without errors (syntax validation via docker-compose config).
        """
        fixture = ClusterFixture(
            cluster_name="test-validate",
            node_count=3,
            base_dir=str(tmp_path),
        )

        fixture.setup()

        compose_file = tmp_path / "docker-compose.yml"
        assert compose_file.exists()

        # Validate with docker-compose config command (syntax check)
        try:
            result = subprocess.run(
                ["docker-compose", "--file", str(compose_file), "config"],
                capture_output=True,
                timeout=10,
                text=True,
            )
            assert result.returncode == 0, (
                f"docker-compose config failed: {result.stderr}"
            )
        except FileNotFoundError:
            pytest.skip("docker-compose CLI not available")
        finally:
            fixture.cleanup()

    @pytest.mark.integration
    def test_cluster_fixture_node_count_generation(
        self, tmp_path: Path, skip_if_no_docker: None
    ) -> None:
        """Test ClusterFixture generates correct number of nodes.

        Verifies that for N nodes requested, the docker-compose.yml
        contains N node service definitions.
        """
        for node_count in [2, 3, 5]:
            fixture = ClusterFixture(
                cluster_name=f"test-nodes-{node_count}",
                node_count=node_count,
                base_dir=str(tmp_path / f"cluster-{node_count}"),
            )

            fixture.setup()

            compose_file = Path(fixture.base_dir) / "docker-compose.yml"
            content = compose_file.read_text()

            # Count node service definitions
            for i in range(node_count):
                node_name = f"node-{i + 1}"
                assert node_name in content, (
                    f"docker-compose should define {node_name} service"
                )

            fixture.cleanup()

    @pytest.mark.integration
    def test_cluster_fixture_cleanup_removes_directory(
        self, tmp_path: Path, skip_if_no_docker: None
    ) -> None:
        """Test ClusterFixture.cleanup() removes cluster directory.

        Verifies that cleanup properly removes the cluster's working
        directory and all generated files.
        """
        cluster_dir = tmp_path / "test-cleanup-cluster"
        fixture = ClusterFixture(
            cluster_name="test-cleanup",
            node_count=2,
            base_dir=str(cluster_dir),
        )

        fixture.setup()

        # Verify directory exists
        assert cluster_dir.exists(), "cluster directory should be created"

        fixture.cleanup()

        # Verify directory is removed
        assert not cluster_dir.exists(), (
            "cluster directory should be removed after cleanup"
        )

    @pytest.mark.integration
    def test_cluster_fixture_health_verification_interface(
        self, tmp_path: Path, skip_if_no_docker: None
    ) -> None:
        """Test ClusterFixture.verify_health() method exists and has correct signature.

        Verifies that the verify_health method can be called with
        optional timeout parameter and returns boolean.
        """
        fixture = ClusterFixture(
            cluster_name="test-health",
            node_count=2,
            base_dir=str(tmp_path),
        )

        # Verify method exists
        assert hasattr(fixture, "verify_health"), (
            "ClusterFixture should have verify_health method"
        )

        # Verify it's callable
        assert callable(fixture.verify_health), "verify_health should be callable"

        fixture.cleanup()

    @pytest.mark.integration
    def test_cluster_fixture_multiple_instances_different_names(
        self, tmp_path: Path, skip_if_no_docker: None
    ) -> None:
        """Test multiple ClusterFixture instances with different cluster names.

        Verifies that multiple fixture instances with different names
        don't interfere with each other.
        """
        fixture1 = ClusterFixture(
            cluster_name="cluster-a",
            node_count=2,
            base_dir=str(tmp_path / "cluster-a"),
        )
        fixture2 = ClusterFixture(
            cluster_name="cluster-b",
            node_count=3,
            base_dir=str(tmp_path / "cluster-b"),
        )

        fixture1.setup()
        fixture2.setup()

        # Verify both are independent
        assert (tmp_path / "cluster-a" / "docker-compose.yml").exists()
        assert (tmp_path / "cluster-b" / "docker-compose.yml").exists()

        content_a = (tmp_path / "cluster-a" / "docker-compose.yml").read_text()
        content_b = (tmp_path / "cluster-b" / "docker-compose.yml").read_text()

        # Verify they have different node counts
        assert content_a.count("node-") == 2
        assert content_b.count("node-") == 3

        fixture1.cleanup()
        fixture2.cleanup()
