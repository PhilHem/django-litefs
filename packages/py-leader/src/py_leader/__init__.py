"""py-leader: Raft consensus wrapper around PySyncObj.

Provides a clean API for distributed leader election using Raft consensus,
implementing the RaftLeaderElectionPort interface from litefs-py.
"""

from .raft_leader import RaftLeaderElection

__all__ = ["RaftLeaderElection"]
__version__ = "0.1.0"
