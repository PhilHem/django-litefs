"""Tests for the example Django app to validate it can be instantiated and configured."""

import os
from pathlib import Path


def test_django_settings_module_configured():
    """Test that Django settings module is properly configured."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
    assert os.environ.get("DJANGO_SETTINGS_MODULE") == "myproject.settings"


def test_settings_file_exists():
    """Test that settings.py file exists in the expected location."""
    settings_path = Path(__file__).parent / "myproject" / "settings.py"
    assert settings_path.exists(), f"Settings file not found at {settings_path}"


def test_models_file_exists():
    """Test that models.py file exists in the expected location."""
    models_path = Path(__file__).parent / "myapp" / "models.py"
    assert models_path.exists(), f"Models file not found at {models_path}"


def test_views_file_exists():
    """Test that views.py file exists in the expected location."""
    views_path = Path(__file__).parent / "myapp" / "views.py"
    assert views_path.exists(), f"Views file not found at {views_path}"


def test_docker_compose_file_exists():
    """Test that docker-compose.yml exists."""
    compose_path = Path(__file__).parent / "docker-compose.yml"
    assert compose_path.exists(), f"docker-compose.yml not found at {compose_path}"


def test_readme_file_exists():
    """Test that README.md exists."""
    readme_path = Path(__file__).parent / "README.md"
    assert readme_path.exists(), f"README.md not found at {readme_path}"


def test_dockerfile_exists():
    """Test that Dockerfile exists."""
    dockerfile_path = Path(__file__).parent / "Dockerfile"
    assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"


def test_requirements_txt_exists():
    """Test that requirements.txt exists."""
    requirements_path = Path(__file__).parent / "requirements.txt"
    assert requirements_path.exists(), f"requirements.txt not found at {requirements_path}"


def test_manage_py_exists():
    """Test that manage.py exists."""
    manage_path = Path(__file__).parent / "manage.py"
    assert manage_path.exists(), f"manage.py not found at {manage_path}"


def test_litefs_config_template_exists():
    """Test that litefs.yml template exists."""
    config_path = Path(__file__).parent / "litefs.yml"
    assert config_path.exists(), f"litefs.yml not found at {config_path}"


def test_django_project_structure():
    """Test that Django project structure is complete."""
    base_dir = Path(__file__).parent

    # Project package files
    assert (base_dir / "myproject" / "__init__.py").exists()
    assert (base_dir / "myproject" / "settings.py").exists()
    assert (base_dir / "myproject" / "urls.py").exists()
    assert (base_dir / "myproject" / "wsgi.py").exists()

    # App package files
    assert (base_dir / "myapp" / "__init__.py").exists()
    assert (base_dir / "myapp" / "apps.py").exists()
    assert (base_dir / "myapp" / "models.py").exists()
    assert (base_dir / "myapp" / "views.py").exists()
    assert (base_dir / "myapp" / "urls.py").exists()
    assert (base_dir / "myapp" / "admin.py").exists()


def test_settings_has_litefs_config():
    """Test that Django settings includes LiteFS configuration."""
    import sys
    from pathlib import Path

    # Add the example app to the path
    example_dir = Path(__file__).parent
    if str(example_dir) not in sys.path:
        sys.path.insert(0, str(example_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

    # Import settings module
    from myproject import settings as django_settings

    # Verify LITEFS configuration exists
    assert hasattr(django_settings, "LITEFS"), "LITEFS setting not found"

    litefs_config = django_settings.LITEFS
    assert isinstance(litefs_config, dict), "LITEFS should be a dictionary"

    # Verify required LITEFS fields
    required_fields = [
        "MOUNT_PATH",
        "DATA_PATH",
        "DATABASE_NAME",
        "LEADER_ELECTION",
        "PRIMARY_HOSTNAME",
        "PROXY_ADDR",
        "ENABLED",
        "RETENTION",
    ]
    for field in required_fields:
        assert field in litefs_config, f"LITEFS config missing required field: {field}"

    # Verify values
    assert litefs_config["LEADER_ELECTION"] == "static", "Should use static leader election"
    assert litefs_config["ENABLED"] is True, "LiteFS should be enabled"


def test_settings_has_litefs_database_backend():
    """Test that Django settings uses LiteFS database backend."""
    import sys
    from pathlib import Path

    # Add the example app to the path
    example_dir = Path(__file__).parent
    if str(example_dir) not in sys.path:
        sys.path.insert(0, str(example_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

    # Import settings module
    from myproject import settings as django_settings

    # Verify DATABASES configuration
    assert hasattr(django_settings, "DATABASES"), "DATABASES setting not found"

    databases = django_settings.DATABASES
    assert "default" in databases, "default database not found"

    default_db = databases["default"]
    assert (
        "litefs_django.db.backends.litefs" in default_db.get("ENGINE", "")
    ), "Database engine should use LiteFS backend"

    # Verify OPTIONS
    assert "OPTIONS" in default_db, "OPTIONS not found in database config"
    assert (
        "litefs_mount_path" in default_db["OPTIONS"]
    ), "litefs_mount_path not in OPTIONS"


def test_docker_compose_has_three_nodes():
    """Test that docker-compose.yml defines three nodes."""
    import yaml

    compose_path = Path(__file__).parent / "docker-compose.yml"

    with open(compose_path) as f:
        compose_config = yaml.safe_load(f)

    services = compose_config.get("services", {})
    node_services = [s for s in services.keys() if s.startswith("node")]

    assert len(node_services) >= 3, f"Expected at least 3 nodes, found {len(node_services)}"
    assert "node1" in services, "node1 service not found"
    assert "node2" in services, "node2 service not found"
    assert "node3" in services, "node3 service not found"

    # Verify node1 is configured as primary
    node1 = services["node1"]
    environment = node1.get("environment", {})
    assert (
        environment.get("PRIMARY_HOSTNAME") == "node1"
    ), "node1 should be the primary"


def test_dockerfile_has_required_dependencies():
    """Test that Dockerfile includes required system packages."""
    dockerfile_path = Path(__file__).parent / "Dockerfile"

    with open(dockerfile_path) as f:
        dockerfile_content = f.read()

    # Should install build tools
    assert "build-essential" in dockerfile_content, "build-essential not in Dockerfile"

    # Should copy requirements
    assert "requirements.txt" in dockerfile_content, "requirements.txt not copied"

    # Should expose port 8000
    assert "8000" in dockerfile_content, "Port 8000 not exposed"


def test_readme_documents_usage():
    """Test that README documents how to use the example."""
    readme_path = Path(__file__).parent / "README.md"

    with open(readme_path) as f:
        readme_content = f.read()

    # Check for key documentation sections
    assert (
        "docker-compose up" in readme_content
    ), "README should document how to start the cluster"
    assert (
        "API Endpoints" in readme_content
    ), "README should document API endpoints"
    assert (
        "health" in readme_content
    ), "README should document health check endpoint"
    assert (
        "messages" in readme_content
    ), "README should document message endpoints"
    assert (
        "Primary" in readme_content or "primary" in readme_content
    ), "README should document primary node"
    assert (
        "replication" in readme_content.lower()
    ), "README should document data replication"
