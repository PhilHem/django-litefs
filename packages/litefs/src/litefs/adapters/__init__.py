"""Interface adapters: Generic adapters for file I/O and subprocess execution."""

from litefs.adapters.ports import (
    NodeIDResolverPort,
    EnvironmentNodeIDResolver,
    PrimaryDetectorPort,
    LeaderElectionPort,
    RaftLeaderElectionPort,
    SplitBrainDetectorPort,
    ForwardingPort,
    ForwardingResult,
    PlatformDetectorPort,
    BinaryDownloaderPort,
    BinaryResolverPort,
)
from litefs.adapters.raft_leader_election_adapter import RaftLeaderElectionAdapter
from litefs.adapters.httpx_forwarding import HTTPXForwardingAdapter
from litefs.adapters.platform_detector import OsPlatformDetector
from litefs.adapters.httpx_binary_downloader import HttpxBinaryDownloader
from litefs.adapters.filesystem_binary_resolver import FilesystemBinaryResolver

__all__ = [
    "PrimaryDetectorPort",
    "NodeIDResolverPort",
    "EnvironmentNodeIDResolver",
    "LeaderElectionPort",
    "RaftLeaderElectionPort",
    "RaftLeaderElectionAdapter",
    "SplitBrainDetectorPort",
    "ForwardingPort",
    "ForwardingResult",
    "HTTPXForwardingAdapter",
    "PlatformDetectorPort",
    "OsPlatformDetector",
    "BinaryDownloaderPort",
    "HttpxBinaryDownloader",
    "BinaryResolverPort",
    "FilesystemBinaryResolver",
]








