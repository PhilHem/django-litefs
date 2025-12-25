"""Pytest fixtures for LiteFS core integration tests."""

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Generator

import pytest


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests (requires Docker + FUSE)"
    )
    config.addinivalue_line(
        "markers", "concurrency: Concurrency tests with timing constraints"
    )


def _check_fuse_available() -> bool:
    """Check if FUSE is available on the current platform.

    Returns:
        True if FUSE is available or on non-POSIX systems (fallback).
    """
    if os.name != "posix":
        # Non-POSIX systems (Windows) - assume FUSE available via fallback
        return True

    # POSIX systems - check platform-specific FUSE paths
    if platform.system() == "Darwin":
        # macOS uses osxfuse or macfuse
        return os.path.exists("/dev/osxfuse") or os.path.exists("/dev/macfuse")
    else:
        # Linux and other POSIX systems use /dev/fuse
        return os.path.exists("/dev/fuse")


def _check_docker_available() -> bool:
    """Check if Docker is available and running.

    Returns:
        True if Docker is available and responding, False otherwise.
    """
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def litefs_available() -> bool:
    """Check if LiteFS/FUSE is available for integration tests.

    Returns True if LiteFS infrastructure is available, False otherwise.
    Integration tests should skip if this returns False.

    Thread-safe implementation using subprocess.run instead of os.system.
    """
    # Check for Docker availability (thread-safe)
    docker_available = _check_docker_available()

    # Check for FUSE availability (cross-platform)
    fuse_available = _check_fuse_available()

    return docker_available and fuse_available


@pytest.fixture
def skip_if_no_litefs(litefs_available: bool) -> None:
    """Fixture that skips test if LiteFS infrastructure is not available."""
    if not litefs_available:
        pytest.skip("LiteFS infrastructure (Docker/FUSE) not available")


class ClusterFixture:
    """Manages multi-node Docker Compose clusters for integration testing.

    This fixture sets up, verifies, and tears down multi-node LiteFS clusters
    using Docker Compose. It provides health verification for cluster nodes
    and ensures proper cleanup after tests.

    Attributes:
        cluster_name: Unique identifier for the cluster (used in docker-compose project name).
        node_count: Number of nodes in the cluster.
        base_dir: Base directory where cluster files (docker-compose.yml, etc.) are stored.
        nodes: List of node identifiers in the cluster (populated after setup).
    """

    def __init__(
        self,
        cluster_name: str,
        node_count: int,
        base_dir: str,
    ) -> None:
        """Initialize ClusterFixture.

        Args:
            cluster_name: Unique identifier for the cluster (e.g., "test-cluster").
            node_count: Number of nodes to create in the cluster (minimum 2).
            base_dir: Base directory for cluster files (will be created if not exists).

        Raises:
            ValueError: If node_count < 2.
        """
        if node_count < 2:
            raise ValueError("Cluster must have at least 2 nodes")

        self.cluster_name = cluster_name
        self.node_count = node_count
        self.base_dir = base_dir
        self.nodes: list[str] = []

    def setup(self) -> None:
        """Set up the cluster by generating docker-compose.yml.

        Creates the base directory and generates the docker-compose.yml file
        with the specified number of nodes. Does NOT start the containers.

        Raises:
            OSError: If directory creation fails.
        """
        base_path = Path(self.base_dir)
        base_path.mkdir(parents=True, exist_ok=True)

        # Generate docker-compose.yml
        compose_content = self._generate_docker_compose()
        compose_file = base_path / "docker-compose.yml"
        compose_file.write_text(compose_content)

        # Populate nodes list
        self.nodes = [f"node-{i + 1}" for i in range(self.node_count)]

    def cleanup(self) -> None:
        """Clean up cluster resources.

        Stops and removes containers if running, and removes the cluster directory
        and all generated files.
        """
        base_path = Path(self.base_dir)

        if base_path.exists():
            # Stop containers if running
            try:
                subprocess.run(
                    [
                        "docker-compose",
                        "--project-name",
                        self.cluster_name,
                        "--file",
                        str(base_path / "docker-compose.yml"),
                        "down",
                    ],
                    capture_output=True,
                    timeout=30,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Docker not available or already stopped - continue with cleanup
                pass

            # Remove cluster directory
            shutil.rmtree(base_path)

    def start(self, timeout: int = 60) -> None:
        """Start the cluster by bringing up all containers.

        Args:
            timeout: Maximum time in seconds to wait for containers to start.

        Raises:
            subprocess.TimeoutExpired: If containers don't start within timeout.
            FileNotFoundError: If docker-compose is not available.
        """
        base_path = Path(self.base_dir)
        if not base_path.exists():
            raise FileNotFoundError(f"Cluster directory not found: {self.base_dir}")

        subprocess.run(
            [
                "docker-compose",
                "--project-name",
                self.cluster_name,
                "--file",
                str(base_path / "docker-compose.yml"),
                "up",
                "-d",
            ],
            timeout=timeout,
            check=True,
        )

    def stop(self, timeout: int = 30) -> None:
        """Stop the cluster by stopping all containers.

        Args:
            timeout: Maximum time in seconds to wait for containers to stop.

        Raises:
            subprocess.TimeoutExpired: If containers don't stop within timeout.
            FileNotFoundError: If docker-compose is not available.
        """
        base_path = Path(self.base_dir)
        if not base_path.exists():
            return

        subprocess.run(
            [
                "docker-compose",
                "--project-name",
                self.cluster_name,
                "--file",
                str(base_path / "docker-compose.yml"),
                "stop",
            ],
            timeout=timeout,
            check=False,
        )

    def verify_health(
        self,
        timeout: int = 30,
    ) -> bool:
        """Verify that all cluster nodes are healthy.

        Checks that all containers are running and responsive.

        Args:
            timeout: Maximum time in seconds to wait for health checks.

        Returns:
            True if all nodes are healthy, False otherwise.
        """
        if not self.nodes:
            return False

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if all containers are running
                result = subprocess.run(
                    [
                        "docker-compose",
                        "--project-name",
                        self.cluster_name,
                        "--file",
                        str(Path(self.base_dir) / "docker-compose.yml"),
                        "ps",
                    ],
                    capture_output=True,
                    timeout=5,
                    text=True,
                )

                if result.returncode != 0:
                    time.sleep(0.5)
                    continue

                # Count running containers
                running_count = result.stdout.count("Up")

                if running_count == self.node_count:
                    return True

                time.sleep(0.5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                time.sleep(0.5)
                continue

        return False

    def _generate_docker_compose(self) -> str:
        """Generate docker-compose.yml content for multi-node cluster.

        Creates a docker-compose file with specified number of nodes.
        Each node has a unique name (node-1, node-2, etc.) and is networked
        together via a shared network.

        Returns:
            String containing valid docker-compose.yml YAML content.
        """
        services: dict[str, dict[str, Any]] = {}
        for i in range(self.node_count):
            node_name = f"node-{i + 1}"
            services[node_name] = {
                "image": "litefs:latest",
                "container_name": f"{self.cluster_name}-{node_name}",
                "environment": {
                    "NODE_ID": node_name,
                    "CLUSTER_NAME": self.cluster_name,
                },
                "networks": ["litefs-cluster"],
            }

        # Convert to YAML manually (avoid extra dependency)
        yaml_lines: list[str] = []
        yaml_lines.append("version: '3.8'")
        yaml_lines.append("")
        yaml_lines.append("services:")

        for node_name, config in services.items():
            yaml_lines.append(f"  {node_name}:")
            image_val: Any = config["image"]
            yaml_lines.append(f"    image: {image_val}")
            container_val: Any = config["container_name"]
            yaml_lines.append(f"    container_name: {container_val}")
            yaml_lines.append("    environment:")
            env_dict: Any = config["environment"]
            for key, value in env_dict.items():
                yaml_lines.append(f"      {key}: {value}")
            yaml_lines.append("    networks:")
            networks_list: Any = config["networks"]
            for network in networks_list:
                yaml_lines.append(f"      - {network}")

        yaml_lines.append("")
        yaml_lines.append("networks:")
        yaml_lines.append("  litefs-cluster:")
        yaml_lines.append("    driver: bridge")

        return "\n".join(yaml_lines)


@pytest.fixture
def cluster_fixture(tmp_path: Path) -> Generator[ClusterFixture, None, None]:
    """Provide a reusable ClusterFixture for integration tests.

    Creates a ClusterFixture instance with a temporary directory.
    The fixture is cleaned up automatically after each test.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Yields:
        Initialized ClusterFixture instance.

    Example:
        @pytest.mark.integration
        def test_cluster_startup(cluster_fixture: ClusterFixture) -> None:
            cluster_fixture.setup()
            cluster_fixture.start()
            assert cluster_fixture.verify_health()
            cluster_fixture.cleanup()
    """
    fixture = ClusterFixture(
        cluster_name="test-cluster",
        node_count=2,
        base_dir=str(tmp_path / "cluster"),
    )
    yield fixture
    # Ensure cleanup happens
    fixture.cleanup()
