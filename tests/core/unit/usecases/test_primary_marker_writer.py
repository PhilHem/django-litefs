"""Unit tests for PrimaryMarkerWriter use case."""

import pytest
from pathlib import Path

from litefs.usecases.primary_marker_writer import PrimaryMarkerWriter


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryMarkerWriter")
class TestPrimaryMarkerWriter:
    """Test the PrimaryMarkerWriter use case."""

    def test_write_marker_creates_file(self, tmp_path: Path) -> None:
        """write_marker should create .primary file with node ID."""
        writer = PrimaryMarkerWriter(str(tmp_path))

        writer.write_marker("node1")

        primary_file = tmp_path / ".primary"
        assert primary_file.exists()
        assert primary_file.read_text() == "node1"

    def test_write_marker_overwrites_existing(self, tmp_path: Path) -> None:
        """write_marker should overwrite existing .primary file."""
        writer = PrimaryMarkerWriter(str(tmp_path))
        writer.write_marker("node1")

        writer.write_marker("node2")

        primary_file = tmp_path / ".primary"
        assert primary_file.read_text() == "node2"

    def test_remove_marker_deletes_file(self, tmp_path: Path) -> None:
        """remove_marker should delete .primary file."""
        writer = PrimaryMarkerWriter(str(tmp_path))
        writer.write_marker("node1")
        primary_file = tmp_path / ".primary"
        assert primary_file.exists()

        writer.remove_marker()

        assert not primary_file.exists()

    def test_remove_marker_idempotent(self, tmp_path: Path) -> None:
        """remove_marker should not raise if file doesn't exist."""
        writer = PrimaryMarkerWriter(str(tmp_path))
        # Don't write anything first

        # Should not raise
        writer.remove_marker()
        writer.remove_marker()  # Can call multiple times

    def test_marker_exists_true_when_present(self, tmp_path: Path) -> None:
        """marker_exists should return True when .primary exists."""
        writer = PrimaryMarkerWriter(str(tmp_path))
        writer.write_marker("node1")

        assert writer.marker_exists() is True

    def test_marker_exists_false_when_absent(self, tmp_path: Path) -> None:
        """marker_exists should return False when .primary doesn't exist."""
        writer = PrimaryMarkerWriter(str(tmp_path))

        assert writer.marker_exists() is False

    def test_read_marker_returns_content(self, tmp_path: Path) -> None:
        """read_marker should return file content."""
        writer = PrimaryMarkerWriter(str(tmp_path))
        writer.write_marker("node1")

        assert writer.read_marker() == "node1"

    def test_read_marker_returns_none_when_absent(self, tmp_path: Path) -> None:
        """read_marker should return None when file doesn't exist."""
        writer = PrimaryMarkerWriter(str(tmp_path))

        assert writer.read_marker() is None

    def test_read_marker_strips_whitespace(self, tmp_path: Path) -> None:
        """read_marker should strip whitespace from content."""
        writer = PrimaryMarkerWriter(str(tmp_path))
        # Write content with whitespace directly
        primary_file = tmp_path / ".primary"
        primary_file.write_text("  node1  \n")

        assert writer.read_marker() == "node1"

    def test_write_read_roundtrip(self, tmp_path: Path) -> None:
        """Written node ID should be readable back."""
        writer = PrimaryMarkerWriter(str(tmp_path))
        node_ids = ["node1", "my-host.local", "192.168.1.1", "node-with-dashes"]

        for node_id in node_ids:
            writer.write_marker(node_id)
            assert writer.read_marker() == node_id

    def test_mount_path_property(self, tmp_path: Path) -> None:
        """mount_path property should return the configured path."""
        writer = PrimaryMarkerWriter(str(tmp_path))

        assert writer.mount_path == tmp_path

    def test_primary_file_property(self, tmp_path: Path) -> None:
        """primary_file property should return path to .primary."""
        writer = PrimaryMarkerWriter(str(tmp_path))

        assert writer.primary_file == tmp_path / ".primary"


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryMarkerWriter")
class TestPrimaryMarkerWriterErrors:
    """Test error handling in PrimaryMarkerWriter."""

    def test_write_to_nonexistent_directory_raises(self) -> None:
        """write_marker should raise OSError if directory doesn't exist."""
        writer = PrimaryMarkerWriter("/nonexistent/path")

        with pytest.raises(OSError):
            writer.write_marker("node1")

    def test_write_to_readonly_directory_raises(self, tmp_path: Path) -> None:
        """write_marker should raise OSError if directory is read-only."""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        writer = PrimaryMarkerWriter(str(readonly_dir))

        try:
            with pytest.raises(OSError):
                writer.write_marker("node1")
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)
