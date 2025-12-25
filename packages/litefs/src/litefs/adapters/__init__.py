"""Interface adapters: Generic adapters for file I/O and subprocess execution."""

from litefs.adapters.ports import (
    NodeIDResolverPort,
    EnvironmentNodeIDResolver,
    PrimaryDetectorPort,
)

__all__ = [
    "PrimaryDetectorPort",
    "NodeIDResolverPort",
    "EnvironmentNodeIDResolver",
]




