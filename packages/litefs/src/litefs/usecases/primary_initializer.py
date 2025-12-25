"""Primary initializer use case for static leader election."""

from litefs.domain.settings import StaticLeaderConfig


class PrimaryInitializer:
    """Determines if the current node should initialize as primary.

    Use case for static leader election that compares the current node's hostname
    against the configured primary hostname to determine if this node should
    initialize as the primary (leader) node.

    This is a stateless, pure logic component with zero framework dependencies.
    """

    def __init__(self, config: StaticLeaderConfig) -> None:
        """Initialize the primary initializer.

        Args:
            config: StaticLeaderConfig specifying the designated primary hostname.
        """
        self.config = config

    def is_primary(self, current_hostname: str) -> bool:
        """Determine if the current node should be the primary.

        Compares the current node's hostname against the configured primary hostname
        for exact string matching. The comparison is case-sensitive.

        Args:
            current_hostname: The hostname of the current node.

        Returns:
            True if current_hostname matches the configured primary_hostname,
            False otherwise.
        """
        return current_hostname == self.config.primary_hostname
