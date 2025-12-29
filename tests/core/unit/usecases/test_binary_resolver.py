"""Unit tests for BinaryResolver use case."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from litefs.domain.binary import BinaryLocation, BinaryResolutionResult, Platform
from litefs.usecases.binary_resolver import BinaryResolver


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.BinaryResolver")
class TestBinaryResolver:
    """Test BinaryResolver use case."""

    def test_returns_resolution_result_with_found_binary(self) -> None:
        """Test that resolver returns result with path when binary is found."""
        # Arrange
        platform = Platform(os="linux", arch="amd64")
        binary_path = Path("/usr/local/bin/litefs")
        binary_location = BinaryLocation(path=binary_path, is_custom=False)

        platform_detector = Mock()
        platform_detector.detect.return_value = platform

        binary_resolver_port = Mock()
        binary_resolver_port.resolve.return_value = binary_location

        resolver = BinaryResolver(
            platform_detector=platform_detector,
            binary_resolver=binary_resolver_port,
        )

        # Act
        result = resolver()

        # Assert
        assert isinstance(result, BinaryResolutionResult)
        assert result.platform == platform
        assert result.resolved_path == binary_path

    def test_returns_resolution_result_with_none_path_when_binary_not_found(
        self,
    ) -> None:
        """Test that resolver returns result with None path when binary not found."""
        # Arrange
        platform = Platform(os="darwin", arch="arm64")

        platform_detector = Mock()
        platform_detector.detect.return_value = platform

        binary_resolver_port = Mock()
        binary_resolver_port.resolve.return_value = None

        resolver = BinaryResolver(
            platform_detector=platform_detector,
            binary_resolver=binary_resolver_port,
        )

        # Act
        result = resolver()

        # Assert
        assert isinstance(result, BinaryResolutionResult)
        assert result.platform == platform
        assert result.resolved_path is None

    def test_coordinates_platform_detection_then_resolution(self) -> None:
        """Test that use case calls platform detector before binary resolver."""
        # Arrange
        call_order: list[str] = []

        platform = Platform(os="linux", arch="arm64")

        platform_detector = Mock()

        def detect_with_tracking() -> Platform:
            call_order.append("detect")
            return platform

        platform_detector.detect.side_effect = detect_with_tracking

        binary_resolver_port = Mock()

        def resolve_with_tracking() -> BinaryLocation | None:
            call_order.append("resolve")
            return None

        binary_resolver_port.resolve.side_effect = resolve_with_tracking

        resolver = BinaryResolver(
            platform_detector=platform_detector,
            binary_resolver=binary_resolver_port,
        )

        # Act
        resolver()

        # Assert
        assert call_order == ["detect", "resolve"]

    def test_uses_injected_ports_not_hardcoded(self) -> None:
        """Test that use case uses injected ports via dependency injection."""
        # Arrange
        platform = Platform(os="darwin", arch="amd64")
        binary_path = Path("/custom/path/litefs")
        binary_location = BinaryLocation(path=binary_path, is_custom=True)

        platform_detector = Mock()
        platform_detector.detect.return_value = platform

        binary_resolver_port = Mock()
        binary_resolver_port.resolve.return_value = binary_location

        resolver = BinaryResolver(
            platform_detector=platform_detector,
            binary_resolver=binary_resolver_port,
        )

        # Act
        result = resolver()

        # Assert - verify mocks were called
        platform_detector.detect.assert_called_once()
        binary_resolver_port.resolve.assert_called_once()
        assert result.resolved_path == binary_path
