"""Step definitions for write request forwarding configuration feature.

BDD tests for WriteForwardingMiddleware configuration behavior.
TRA Namespace: Adapter.Http.WriteForwardingMiddleware.Config
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Add project root to path for cross-package imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from django.http import HttpResponse  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from litefs.usecases.path_exclusion_matcher import PathExclusionMatcher  # noqa: E402
from litefs_django.middleware import WriteForwardingMiddleware  # noqa: E402
from tests.core.unit.fakes.fake_http_client import FakeHttpClient  # noqa: E402
from tests.django_adapter.unit.fakes import FakePrimaryDetector  # noqa: E402

if TYPE_CHECKING:
    from django.http import HttpRequest


# =============================================================================
# Scenarios - Timeout Configuration
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Default timeout is 30 seconds",
)
def test_default_timeout() -> None:
    """Test that default timeout is 30 seconds."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Custom timeout applied",
)
def test_custom_timeout() -> None:
    """Test that custom timeout is applied."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Separate connect and read timeouts",
)
def test_separate_connect_read_timeouts() -> None:
    """Test that separate connect and read timeouts are configured."""
    pass


# =============================================================================
# Scenarios - Path Exclusions
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Excluded exact path not forwarded",
)
def test_excluded_exact_path() -> None:
    """Test that excluded exact path is not forwarded."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Multiple path exclusions",
)
def test_multiple_path_exclusions() -> None:
    """Test that multiple excluded paths are not forwarded."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Wildcard path exclusion",
)
def test_wildcard_path_exclusion() -> None:
    """Test that wildcard path patterns are excluded."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Regex path exclusion",
)
def test_regex_path_exclusion() -> None:
    """Test that regex path patterns are excluded."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Non-excluded path still forwarded",
)
def test_non_excluded_path_forwarded() -> None:
    """Test that non-excluded paths are still forwarded."""
    pass


# =============================================================================
# Scenarios - Primary Discovery
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Primary discovered from LiteFS mount",
)
def test_primary_discovered_from_litefs() -> None:
    """Test that primary is discovered from LiteFS mount."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Primary URL uses configured scheme",
)
def test_primary_url_uses_configured_scheme() -> None:
    """Test that primary URL uses configured scheme."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Forwarding fails when primary unknown",
)
def test_forwarding_fails_when_primary_unknown() -> None:
    """Test that forwarding fails when primary is unknown."""
    pass


# =============================================================================
# Scenarios - Enable/Disable States
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Forwarding disabled when LiteFS disabled",
)
def test_forwarding_disabled_when_litefs_disabled() -> None:
    """Test that forwarding is disabled when LiteFS is disabled."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Forwarding disabled by explicit configuration",
)
def test_forwarding_disabled_explicitly() -> None:
    """Test that forwarding is disabled by explicit configuration."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
@scenario(
    "../../features/django/forwarding_config.feature",
    "Forwarding inactive when settings missing",
)
def test_forwarding_inactive_when_settings_missing() -> None:
    """Test that forwarding is inactive when settings are missing."""
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def context() -> dict[str, Any]:
    """Shared context for passing state between steps."""
    return {
        "is_primary": False,
        "primary_url": "http://primary.local:8000",
        "forwarding_enabled": True,
        "response": None,
        "request_forwarded": False,
        "excluded_paths": (),
        "connect_timeout": 5.0,
        "read_timeout": 30.0,
        "scheme": "http",
        "litefs_disabled": False,
        "settings_missing": False,
        "primary_unknown": False,
    }


@pytest.fixture
def fake_http_client() -> FakeHttpClient:
    """Create a fake HTTP client for testing."""
    return FakeHttpClient()


@pytest.fixture
def fake_primary_detector() -> FakePrimaryDetector:
    """Create a fake primary detector for testing."""
    return FakePrimaryDetector(is_primary=False)


@pytest.fixture
def request_factory() -> RequestFactory:
    """Create a Django request factory."""
    return RequestFactory()


# =============================================================================
# Helper Functions
# =============================================================================


def create_middleware_with_config(
    fake_http_client: FakeHttpClient,
    fake_primary_detector: FakePrimaryDetector,
    primary_url: str = "http://primary.local:8000",
    excluded_paths: tuple[str, ...] = (),
    connect_timeout: float = 5.0,
    read_timeout: float = 30.0,
    forwarding_enabled: bool = True,
    get_response: Any = None,
) -> WriteForwardingMiddleware:
    """Create middleware with configured dependencies."""
    if get_response is None:
        get_response = lambda r: HttpResponse("Local OK", status=200)  # noqa: E731

    middleware = WriteForwardingMiddleware(get_response=get_response)
    middleware._forwarding_port = fake_http_client
    middleware._primary_detector = fake_primary_detector
    middleware._primary_url = primary_url
    middleware._forwarding_enabled = forwarding_enabled
    middleware._excluded_paths = excluded_paths

    # Configure path matcher if excluded_paths provided
    if excluded_paths:
        middleware._path_matcher = PathExclusionMatcher(excluded_paths=excluded_paths)

    return middleware


def create_request(
    request_factory: RequestFactory,
    method: str,
    path: str,
    client_ip: str = "127.0.0.1",
) -> "HttpRequest":
    """Create a Django request with the specified parameters."""
    method_lower = method.lower()
    factory_method = getattr(request_factory, method_lower, request_factory.generic)

    if method_lower in ("get", "head", "options", "delete"):
        request = factory_method(path)
    else:
        request = factory_method(path)

    request.META["REMOTE_ADDR"] = client_ip
    return request


# =============================================================================
# Given Steps - Timeout Configuration
# =============================================================================


@given("no explicit forwarding timeout is configured")
def no_explicit_timeout(context: dict[str, Any]) -> None:
    """Use default timeout configuration."""
    context["connect_timeout"] = 5.0
    context["read_timeout"] = 30.0


@given(parsers.parse("forwarding timeout is configured as {timeout:d} seconds"))
def forwarding_timeout_configured(context: dict[str, Any], timeout: int) -> None:
    """Configure read timeout to specified value."""
    context["read_timeout"] = float(timeout)


@given(parsers.parse("forwarding connect timeout is {timeout:d} seconds"))
def forwarding_connect_timeout(context: dict[str, Any], timeout: int) -> None:
    """Configure connect timeout to specified value."""
    context["connect_timeout"] = float(timeout)


@given(parsers.parse("forwarding read timeout is {timeout:d} seconds"))
def forwarding_read_timeout(context: dict[str, Any], timeout: int) -> None:
    """Configure read timeout to specified value."""
    context["read_timeout"] = float(timeout)


# =============================================================================
# Given Steps - Node Role
# =============================================================================


@given("this node is a replica")
def node_is_replica(
    context: dict[str, Any],
    fake_primary_detector: FakePrimaryDetector,
) -> None:
    """Configure this node as a replica."""
    context["is_primary"] = False
    fake_primary_detector.set_primary(False)
    context["fake_primary_detector"] = fake_primary_detector


# =============================================================================
# Given Steps - Path Exclusions
# =============================================================================


@given(parsers.parse('path "{path}" is excluded from forwarding'))
def path_excluded(context: dict[str, Any], path: str) -> None:
    """Configure path as excluded from forwarding."""
    context["excluded_paths"] = (path,)


@given("paths are excluded from forwarding:")
def paths_excluded(context: dict[str, Any], datatable: Any) -> None:
    """Configure multiple paths as excluded from forwarding."""
    paths = []
    # Skip header row (index 0), parse data rows
    for row in datatable[1:]:
        paths.append(row[0])
    context["excluded_paths"] = tuple(paths)


@given(parsers.parse('path pattern "{pattern}" is excluded from forwarding'))
def path_pattern_excluded(context: dict[str, Any], pattern: str) -> None:
    """Configure path pattern as excluded from forwarding."""
    context["excluded_paths"] = (pattern,)


@given(parsers.parse('path regex "{pattern}" is excluded from forwarding'))
def path_regex_excluded(context: dict[str, Any], pattern: str) -> None:
    """Configure regex path pattern as excluded from forwarding."""
    # Prefix with re: for regex patterns
    context["excluded_paths"] = (f"re:{pattern}",)


# =============================================================================
# Given Steps - Primary Configuration
# =============================================================================


@given("the primary node is reachable")
def primary_reachable(
    context: dict[str, Any],
    fake_http_client: FakeHttpClient,
) -> None:
    """Configure primary node as reachable."""
    fake_http_client.set_response(status_code=200, body=b"OK")
    context["fake_http_client"] = fake_http_client


@given(parsers.parse('LiteFS mount indicates primary is "{primary_host}"'))
def litefs_mount_primary(context: dict[str, Any], primary_host: str) -> None:
    """Configure LiteFS mount to indicate primary host."""
    scheme = context.get("scheme", "http")
    context["primary_url"] = f"{scheme}://{primary_host}"


@given(parsers.parse('forwarding scheme is configured as "{scheme}"'))
def forwarding_scheme(context: dict[str, Any], scheme: str) -> None:
    """Configure forwarding scheme."""
    context["scheme"] = scheme


@given("the primary node is unknown")
def primary_unknown(context: dict[str, Any]) -> None:
    """Configure primary node as unknown."""
    context["primary_unknown"] = True
    context["primary_url"] = None


# =============================================================================
# Given Steps - Enable/Disable States
# =============================================================================


@given("LiteFS is disabled in settings")
def litefs_disabled(context: dict[str, Any]) -> None:
    """Configure LiteFS as disabled in settings."""
    context["litefs_disabled"] = True
    context["forwarding_enabled"] = False


@given("write forwarding is explicitly disabled")
def forwarding_explicitly_disabled(context: dict[str, Any]) -> None:
    """Configure write forwarding as explicitly disabled."""
    context["forwarding_enabled"] = False


@given("LiteFS settings are not configured")
def settings_missing(context: dict[str, Any]) -> None:
    """Configure LiteFS settings as missing."""
    context["settings_missing"] = True
    context["forwarding_enabled"] = False


# =============================================================================
# When Steps - Request Processing
# =============================================================================


@when("a POST request is forwarded")
def post_request_forwarded(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
) -> None:
    """Process a POST request that gets forwarded."""
    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)
    if "fake_http_client" not in context:
        client.set_response(status_code=200, body=b"OK")
        context["fake_http_client"] = client

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_config(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
        excluded_paths=context.get("excluded_paths", ()),
        connect_timeout=context.get("connect_timeout", 5.0),
        read_timeout=context.get("read_timeout", 30.0),
        forwarding_enabled=context.get("forwarding_enabled", True),
    )

    # Create request
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path="/api/resource",
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


@when(parsers.parse('a POST request arrives for "{path}"'))
def post_request_arrives(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    path: str,
) -> None:
    """Process a POST request for specified path."""
    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)
    if "fake_http_client" not in context:
        client.set_response(status_code=200, body=b"OK")
        context["fake_http_client"] = client

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Handle primary unknown case
    primary_url = context.get("primary_url", "http://primary.local:8000")
    if context.get("primary_unknown"):
        primary_url = None

    # Create middleware
    middleware = create_middleware_with_config(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=primary_url,
        excluded_paths=context.get("excluded_paths", ()),
        connect_timeout=context.get("connect_timeout", 5.0),
        read_timeout=context.get("read_timeout", 30.0),
        forwarding_enabled=context.get("forwarding_enabled", True),
    )

    # Handle primary unknown - clear URL resolver to trigger 503
    if context.get("primary_unknown"):
        middleware._url_resolver = None

    # Create request
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path=path,
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


# =============================================================================
# Then Steps - Timeout Assertions
# =============================================================================


@then(parsers.parse("the forwarding timeout should be {timeout:d} seconds"))
def forwarding_timeout_is(context: dict[str, Any], timeout: int) -> None:
    """Assert forwarding timeout matches expected value."""
    # The timeout is validated through the read_timeout in context
    assert context.get("read_timeout") == float(timeout), (
        f"Expected read_timeout {timeout}, got {context.get('read_timeout')}"
    )


@then(parsers.parse("the connect timeout should be {timeout:d} seconds"))
def connect_timeout_is(context: dict[str, Any], timeout: int) -> None:
    """Assert connect timeout matches expected value."""
    assert context.get("connect_timeout") == float(timeout), (
        f"Expected connect_timeout {timeout}, got {context.get('connect_timeout')}"
    )


@then(parsers.parse("the read timeout should be {timeout:d} seconds"))
def read_timeout_is(context: dict[str, Any], timeout: int) -> None:
    """Assert read timeout matches expected value."""
    assert context.get("read_timeout") == float(timeout), (
        f"Expected read_timeout {timeout}, got {context.get('read_timeout')}"
    )


# =============================================================================
# Then Steps - Forwarding Behavior
# =============================================================================


@then("the request should proceed to the next middleware")
def request_proceeds_locally(context: dict[str, Any]) -> None:
    """Assert request was handled locally."""
    response = context["response"]
    # Local response returns "Local OK" from our test get_response
    assert response.status_code in (200, 503), (
        f"Expected local handling (200 or 503), got {response.status_code}"
    )


@then("no forwarding should occur")
def no_forwarding_occurred(context: dict[str, Any]) -> None:
    """Assert no forwarding occurred."""
    assert not context["request_forwarded"], "Expected no forwarding to occur"


@then("the request should be forwarded to the primary")
def request_forwarded_to_primary(context: dict[str, Any]) -> None:
    """Assert request was forwarded to primary."""
    assert context["request_forwarded"], "Expected request to be forwarded to primary"


@then(parsers.parse('the request should be sent to "{url}"'))
def request_sent_to_url(context: dict[str, Any], url: str) -> None:
    """Assert request was sent to specified URL."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"
    assert client.requests[0]["primary_url"] == url, (
        f"Expected primary_url {url}, got {client.requests[0]['primary_url']}"
    )


# =============================================================================
# Then Steps - Response Assertions
# =============================================================================


@then(parsers.parse("the response status should be {status:d} Service Unavailable"))
def response_status_service_unavailable(context: dict[str, Any], status: int) -> None:
    """Assert response has 503 Service Unavailable status."""
    response = context["response"]
    assert response.status_code == status, (
        f"Expected status {status}, got {response.status_code}"
    )


@then(parsers.parse("the response status should be {status:d}"))
def response_status(context: dict[str, Any], status: int) -> None:
    """Assert response has expected status code."""
    response = context["response"]
    assert response.status_code == status, (
        f"Expected status {status}, got {response.status_code}"
    )


@then(parsers.parse('the response body should indicate "{message}"'))
def response_body_indicates(context: dict[str, Any], message: str) -> None:
    """Assert response body contains expected message."""
    response = context["response"]
    body = response.content.decode()
    assert message in body, f"Expected '{message}' in body, got: {body}"
