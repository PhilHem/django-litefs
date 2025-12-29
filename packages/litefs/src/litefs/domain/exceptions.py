"""Domain exceptions.

Exception hierarchy:
- LiteFSConfigError: Base domain exception for configuration errors.
  All domain-level validation errors inherit from this.
  Used by use cases and domain entities to signal invalid configuration.
"""


class LiteFSConfigError(Exception):
    """Raised when LiteFS configuration is invalid.

    This is the base exception for all domain-level configuration errors.
    It is raised by domain entities (e.g., LiteFSSettings) and use cases
    (e.g., ConfigParser, MountValidator) when configuration validation fails.

    Framework adapters (Django, FastAPI) may catch this and re-raise as
    framework-specific exceptions, but the domain layer always uses this.
    """

    pass


class BinaryDownloadError(LiteFSConfigError):
    """Raised when binary download fails.

    This exception is raised during LiteFS binary download operations
    when network errors, HTTP errors, or other download failures occur.

    Attributes:
        message: Human-readable error description.
        url: The URL that failed to download (optional).
        original_error: The underlying exception that caused the failure (optional).
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize BinaryDownloadError.

        Args:
            message: Human-readable error description.
            url: The URL that failed to download.
            original_error: The underlying exception that caused the failure.
        """
        super().__init__(message)
        self.message = message
        self.url = url
        self.original_error = original_error
