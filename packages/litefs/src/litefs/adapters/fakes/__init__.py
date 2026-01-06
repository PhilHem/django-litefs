"""Fake adapters for testing.

This module provides test doubles for port interfaces, enabling
deterministic testing without real I/O operations.
"""

from litefs.adapters.fakes.fake_binary_downloader import FakeBinaryDownloader
from litefs.adapters.fakes.fake_binary_resolver import FakeBinaryResolver
from litefs.adapters.fakes.fake_platform_detector import FakePlatformDetector
from litefs.adapters.fakes.fake_metrics import FakeMetricsAdapter, MetricCall

__all__ = [
    "FakeBinaryDownloader",
    "FakeBinaryResolver",
    "FakePlatformDetector",
    "FakeMetricsAdapter",
    "MetricCall",
]
