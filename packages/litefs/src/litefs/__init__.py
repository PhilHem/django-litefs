"""litefs-py: Framework-agnostic LiteFS integration for Python."""

__version__ = "0.1.1"

from litefs.domain.settings import LiteFSSettings
from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.config_generator import ConfigGenerator
from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs.factories import create_raft_leader_election, PyLeaderNotInstalledError

__all__ = [
    "LiteFSSettings",
    "LiteFSConfigError",
    "ConfigGenerator",
    "PrimaryDetector",
    "LiteFSNotRunningError",
    "create_raft_leader_election",
    "PyLeaderNotInstalledError",
]








