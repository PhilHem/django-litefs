"""Unit tests for OsPlatformDetector adapter."""

import platform
from unittest.mock import patch

import pytest

from litefs.adapters.platform_detector import OsPlatformDetector
from litefs.adapters.ports import PlatformDetectorPort
from litefs.domain.binary import Platform
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.tier(1)
@pytest.mark.unit
@pytest.mark.tra("Adapter.OsPlatformDetector")
class TestOsPlatformDetector:
    """Test OsPlatformDetector implementation."""

    def test_detect_returns_platform(self) -> None:
        """Test that detect() returns a Platform value object."""
        detector = OsPlatformDetector()
        result = detector.detect()
        assert isinstance(result, Platform)

    def test_satisfies_protocol(self) -> None:
        """Test that OsPlatformDetector satisfies PlatformDetectorPort protocol."""
        detector = OsPlatformDetector()
        assert isinstance(detector, PlatformDetectorPort)

    def test_consistent_results_across_calls(self) -> None:
        """Test that detect() returns consistent results across multiple calls."""
        detector = OsPlatformDetector()
        first = detector.detect()
        second = detector.detect()
        assert first == second

    @patch("platform.system")
    @patch("platform.machine")
    def test_detect_on_linux_amd64(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test detection on Linux x86_64 system."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.os == "linux"
        assert result.arch == "amd64"

    @patch("platform.system")
    @patch("platform.machine")
    def test_detect_on_linux_arm64(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test detection on Linux aarch64 system."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "aarch64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.os == "linux"
        assert result.arch == "arm64"

    @patch("platform.system")
    @patch("platform.machine")
    def test_detect_on_darwin_arm64(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test detection on macOS Apple Silicon."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.os == "darwin"
        assert result.arch == "arm64"

    @patch("platform.system")
    @patch("platform.machine")
    def test_detect_on_darwin_amd64(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test detection on macOS Intel."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "x86_64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.os == "darwin"
        assert result.arch == "amd64"

    @patch("platform.system")
    @patch("platform.machine")
    def test_maps_x86_64_to_amd64(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test that x86_64 machine type is mapped to amd64."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.arch == "amd64"

    @patch("platform.system")
    @patch("platform.machine")
    def test_maps_aarch64_to_arm64(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test that aarch64 machine type is mapped to arm64."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "aarch64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.arch == "arm64"

    @patch("platform.system")
    @patch("platform.machine")
    def test_maps_AMD64_to_amd64(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test that AMD64 (Windows-style) is mapped to amd64."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "AMD64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.arch == "amd64"

    @patch("platform.system")
    @patch("platform.machine")
    def test_unsupported_os_raises_error(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test that unsupported OS raises LiteFSConfigError."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "x86_64"

        detector = OsPlatformDetector()
        with pytest.raises(LiteFSConfigError, match="Unsupported operating system"):
            detector.detect()

    @patch("platform.system")
    @patch("platform.machine")
    def test_unsupported_arch_raises_error(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test that unsupported architecture raises LiteFSConfigError."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "i386"

        detector = OsPlatformDetector()
        with pytest.raises(LiteFSConfigError, match="Unsupported architecture"):
            detector.detect()

    @patch("platform.system")
    @patch("platform.machine")
    def test_os_name_case_insensitive(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test that OS name detection is case-insensitive."""
        mock_system.return_value = "LINUX"
        mock_machine.return_value = "x86_64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.os == "linux"

    @patch("platform.system")
    @patch("platform.machine")
    def test_arch_name_case_insensitive(
        self, mock_machine: patch, mock_system: patch
    ) -> None:
        """Test that architecture detection is case-insensitive."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "AARCH64"

        detector = OsPlatformDetector()
        result = detector.detect()

        assert result.arch == "arm64"
