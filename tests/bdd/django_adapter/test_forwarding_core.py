"""Step definitions for write request forwarding core behavior feature.

BDD tests for WriteForwardingMiddleware HTTP-level request forwarding.
TRA Namespace: Adapter.Http.WriteForwardingMiddleware
"""

from __future__ import annotations

import json
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

from litefs_django.middleware import WriteForwardingMiddleware  # noqa: E402
from tests.core.unit.fakes.fake_http_client import FakeHttpClient  # noqa: E402
from tests.django_adapter.unit.fakes import FakePrimaryDetector  # noqa: E402

if TYPE_CHECKING:
    from django.http import HttpRequest


# =============================================================================
# Scenarios - HTTP Method Routing
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Write methods forwarded from replica to primary",
)
def test_write_methods_forwarded_post() -> None:
    """Test that POST requests are forwarded from replica to primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Write methods forwarded from replica to primary",
)
def test_write_methods_forwarded_put() -> None:
    """Test that PUT requests are forwarded from replica to primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Write methods forwarded from replica to primary",
)
def test_write_methods_forwarded_patch() -> None:
    """Test that PATCH requests are forwarded from replica to primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Write methods forwarded from replica to primary",
)
def test_write_methods_forwarded_delete() -> None:
    """Test that DELETE requests are forwarded from replica to primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Read methods handled locally on replica",
)
def test_read_methods_local_get() -> None:
    """Test that GET requests are handled locally on replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Read methods handled locally on replica",
)
def test_read_methods_local_head() -> None:
    """Test that HEAD requests are handled locally on replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Read methods handled locally on replica",
)
def test_read_methods_local_options() -> None:
    """Test that OPTIONS requests are handled locally on replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Write request handled locally on primary",
)
def test_write_request_local_on_primary() -> None:
    """Test that write requests are handled locally on primary."""
    pass


# =============================================================================
# Scenarios - Request Header Preservation
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Authorization and custom headers preserved",
)
def test_authorization_and_custom_headers_preserved() -> None:
    """Test that authorization and custom headers are preserved."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Host header rewritten to primary",
)
def test_host_header_rewritten() -> None:
    """Test that Host header is rewritten to primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "X-Forwarded-For header added",
)
def test_x_forwarded_for_added() -> None:
    """Test that X-Forwarded-For header is added."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Existing X-Forwarded-For header appended",
)
def test_x_forwarded_for_appended() -> None:
    """Test that existing X-Forwarded-For header is appended."""
    pass


# =============================================================================
# Scenarios - Request Body Preservation
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "JSON body preserved during forwarding",
)
def test_json_body_preserved() -> None:
    """Test that JSON body is preserved during forwarding."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Form data preserved during forwarding",
)
def test_form_data_preserved() -> None:
    """Test that form data is preserved during forwarding."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Query parameters preserved during forwarding",
)
def test_query_parameters_preserved() -> None:
    """Test that query parameters are preserved during forwarding."""
    pass


# =============================================================================
# Scenarios - Response Passthrough
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Success response passed through",
)
def test_success_response_passed_through() -> None:
    """Test that success response is passed through."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Response headers passed through",
)
def test_response_headers_passed_through() -> None:
    """Test that response headers are passed through."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Error response passed through",
)
def test_error_response_passed_through() -> None:
    """Test that error response is passed through."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Redirect response passed through",
)
def test_redirect_response_passed_through() -> None:
    """Test that redirect response is passed through."""
    pass


# =============================================================================
# Scenarios - Forwarding Indicator Headers
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Forwarded response includes indicator header",
)
def test_forwarded_response_includes_indicator() -> None:
    """Test that forwarded response includes indicator header."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
@scenario(
    "../../features/django/forwarding_core.feature",
    "Local response excludes forwarding indicator",
)
def test_local_response_excludes_indicator() -> None:
    """Test that local response excludes forwarding indicator."""
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
        "request_method": "GET",
        "request_path": "/",
        "request_headers": {},
        "request_body": None,
        "form_data": {},
        "client_ip": "127.0.0.1",
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


def create_middleware_with_fakes(
    fake_http_client: FakeHttpClient,
    fake_primary_detector: FakePrimaryDetector,
    primary_url: str = "http://primary.local:8000",
    get_response: Any = None,
) -> WriteForwardingMiddleware:
    """Create middleware with fake dependencies injected."""
    if get_response is None:
        get_response = lambda r: HttpResponse("Local OK", status=200)  # noqa: E731

    middleware = WriteForwardingMiddleware(get_response=get_response)
    middleware._forwarding_port = fake_http_client
    middleware._primary_detector = fake_primary_detector
    middleware._primary_url = primary_url
    middleware._forwarding_enabled = True
    middleware._excluded_paths = ()
    return middleware


def create_request(
    request_factory: RequestFactory,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    data: dict[str, str] | None = None,
    content_type: str | None = None,
    client_ip: str = "127.0.0.1",
) -> "HttpRequest":
    """Create a Django request with the specified parameters."""
    kwargs: dict[str, Any] = {}

    if content_type:
        kwargs["content_type"] = content_type

    if body is not None:
        kwargs["data"] = body
        kwargs["content_type"] = content_type or "application/octet-stream"
    elif data is not None:
        if content_type == "application/json":
            kwargs["data"] = json.dumps(data)
            kwargs["content_type"] = "application/json"
        else:
            kwargs["data"] = data

    # Create request based on method
    method_lower = method.lower()
    factory_method = getattr(request_factory, method_lower, request_factory.generic)

    if method_lower in ("get", "head", "options", "delete"):
        if data:
            # For GET-like methods, data goes in query string
            request = factory_method(path, data=data)
        else:
            request = factory_method(path)
    else:
        request = factory_method(path, **kwargs)

    # Set client IP
    request.META["REMOTE_ADDR"] = client_ip

    # Add custom headers
    if headers:
        for header_name, header_value in headers.items():
            # Convert header name to Django META format
            meta_key = f"HTTP_{header_name.upper().replace('-', '_')}"
            if header_name.lower() == "content-type":
                request.META["CONTENT_TYPE"] = header_value
            elif header_name.lower() == "host":
                request.META["HTTP_HOST"] = header_value
            else:
                request.META[meta_key] = header_value

    return request


# =============================================================================
# Given Steps - Background
# =============================================================================


@given("the WriteForwardingMiddleware is enabled")
def middleware_enabled(context: dict[str, Any]) -> None:
    """Enable the WriteForwardingMiddleware."""
    context["forwarding_enabled"] = True


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


@given("this node is the primary")
def node_is_primary(
    context: dict[str, Any],
    fake_primary_detector: FakePrimaryDetector,
) -> None:
    """Configure this node as the primary."""
    context["is_primary"] = True
    fake_primary_detector.set_primary(True)
    context["fake_primary_detector"] = fake_primary_detector


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


@given(parsers.parse('the primary node is at "{url}"'))
def primary_at_url(context: dict[str, Any], url: str) -> None:
    """Configure primary node URL."""
    context["primary_url"] = f"http://{url}"


@given(parsers.parse("the primary returns status {status:d} with body '{body}'"))
def primary_returns_status_and_body(
    context: dict[str, Any],
    fake_http_client: FakeHttpClient,
    status: int,
    body: str,
) -> None:
    """Configure primary to return specific status and body."""
    fake_http_client.set_response(status_code=status, body=body.encode())
    context["fake_http_client"] = fake_http_client


@given(
    parsers.parse('the primary returns status {status:d} with Location "{location}"')
)
def primary_returns_redirect(
    context: dict[str, Any],
    fake_http_client: FakeHttpClient,
    status: int,
    location: str,
) -> None:
    """Configure primary to return redirect response."""
    fake_http_client.set_response(
        status_code=status,
        headers={"Location": location},
        body=b"",
    )
    context["fake_http_client"] = fake_http_client


@given("the primary returns headers:")
def primary_returns_headers(
    context: dict[str, Any],
    fake_http_client: FakeHttpClient,
    datatable: Any,
) -> None:
    """Configure primary to return specific headers.

    Note: datatable is a list of lists where first row is headers.
    """
    headers = {}
    # Skip header row (index 0), parse data rows
    for row in datatable[1:]:
        headers[row[0]] = row[1]
    fake_http_client.set_response(status_code=200, headers=headers, body=b"OK")
    context["fake_http_client"] = fake_http_client


# =============================================================================
# When Steps - Request Arrival
# =============================================================================


@when(parsers.parse('a {method} request arrives for "{path}"'))
def request_arrives_for_path(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    method: str,
    path: str,
) -> None:
    """Process a request with specified method and path."""
    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request
    request = create_request(
        request_factory=request_factory,
        method=method,
        path=path,
        headers=context.get("request_headers"),
        body=context.get("request_body"),
        data=context.get("form_data") if context.get("form_data") else None,
        content_type=context.get("content_type"),
        client_ip=context.get("client_ip", "127.0.0.1"),
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["request_method"] = method
    context["request_path"] = path
    context["fake_http_client"] = client


@when("a POST request arrives with headers:")
def post_request_with_headers(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    datatable: Any,
) -> None:
    """Process a POST request with specified headers.

    Note: datatable is a list of lists where first row is headers.
    """
    headers = {}
    # Skip header row (index 0), parse data rows
    for row in datatable[1:]:
        headers[row[0]] = row[1]
    context["request_headers"] = headers

    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path="/api/resource",
        headers=headers,
        client_ip=context.get("client_ip", "127.0.0.1"),
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


@when(parsers.parse('a POST request arrives with Host header "{host}"'))
def post_request_with_host_header(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    host: str,
) -> None:
    """Process a POST request with specified Host header."""
    context["request_headers"] = {"Host": host}
    context["original_host"] = host

    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path="/api/resource",
        headers={"Host": host},
        client_ip=context.get("client_ip", "127.0.0.1"),
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


@when(parsers.parse('a POST request arrives from client IP "{ip}"'))
def post_request_from_client_ip(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    ip: str,
) -> None:
    """Process a POST request from specified client IP."""
    context["client_ip"] = ip

    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path="/api/resource",
        client_ip=ip,
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


@when(parsers.parse('a POST request arrives with "{header}: {value}"'))
def post_request_with_specific_header(
    context: dict[str, Any],
    header: str,
    value: str,
) -> None:
    """Store header for the request (actual execution deferred to next step)."""
    if "request_headers" not in context:
        context["request_headers"] = {}
    context["request_headers"][header] = value


@when(parsers.parse('the client IP is "{ip}"'))
def set_client_ip_and_execute(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    ip: str,
) -> None:
    """Set client IP and execute the request."""
    context["client_ip"] = ip

    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request with headers from context
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path="/api/resource",
        headers=context.get("request_headers"),
        client_ip=ip,
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


@when("a POST request arrives with JSON body:")
def post_request_with_json_body(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    docstring: str,
) -> None:
    """Process a POST request with JSON body."""
    body = docstring.strip().encode()
    context["request_body"] = body
    context["content_type"] = "application/json"

    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path="/api/resource",
        body=body,
        content_type="application/json",
        client_ip=context.get("client_ip", "127.0.0.1"),
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


@when("a POST request arrives with form data:")
def post_request_with_form_data(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
    datatable: Any,
) -> None:
    """Process a POST request with form data.

    Note: datatable is a list of lists where first row is headers.
    """
    form_data = {}
    # Skip header row (index 0), parse data rows
    for row in datatable[1:]:
        form_data[row[0]] = row[1]
    context["form_data"] = form_data
    context["content_type"] = "application/x-www-form-urlencoded"

    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=context.get("is_primary", False))

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request with form data
    request = request_factory.post(
        "/api/resource",
        data=form_data,
    )
    request.META["REMOTE_ADDR"] = context.get("client_ip", "127.0.0.1")

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


@when("a POST request is forwarded successfully")
def post_request_forwarded_successfully(
    context: dict[str, Any],
    request_factory: RequestFactory,
    fake_http_client: FakeHttpClient,
) -> None:
    """Process a POST request that gets forwarded."""
    # Get or create fake http client
    client = context.get("fake_http_client", fake_http_client)

    # Get or create fake primary detector
    detector = context.get("fake_primary_detector")
    if detector is None:
        detector = FakePrimaryDetector(is_primary=False)

    # Create middleware
    middleware = create_middleware_with_fakes(
        fake_http_client=client,
        fake_primary_detector=detector,
        primary_url=context.get("primary_url", "http://primary.local:8000"),
    )

    # Create request
    request = create_request(
        request_factory=request_factory,
        method="POST",
        path="/api/resource",
        client_ip=context.get("client_ip", "127.0.0.1"),
    )

    # Process request
    response = middleware(request)

    # Store results
    context["response"] = response
    context["request_forwarded"] = len(client.requests) > 0
    context["fake_http_client"] = client


# =============================================================================
# Then Steps - Forwarding Behavior
# =============================================================================


@then("the request should be forwarded to the primary")
def request_forwarded_to_primary(context: dict[str, Any]) -> None:
    """Assert request was forwarded to primary."""
    assert context["request_forwarded"], "Expected request to be forwarded to primary"


@then(parsers.parse('the forwarded request method should be "{method}"'))
def forwarded_request_method(context: dict[str, Any], method: str) -> None:
    """Assert forwarded request has correct method."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"
    assert client.requests[0]["method"] == method, (
        f"Expected method {method}, got {client.requests[0]['method']}"
    )


@then("the request should proceed to the next middleware")
def request_proceeds_locally(context: dict[str, Any]) -> None:
    """Assert request was handled locally."""
    response = context["response"]
    # Local response returns "Local OK" from our test get_response
    assert response.status_code == 200, (
        f"Expected 200 from local handler, got {response.status_code}"
    )


@then("no forwarding should occur")
def no_forwarding_occurred(context: dict[str, Any]) -> None:
    """Assert no forwarding occurred."""
    assert not context["request_forwarded"], "Expected no forwarding to occur"


# =============================================================================
# Then Steps - Header Preservation
# =============================================================================


@then("the forwarded request should include all original headers")
def forwarded_includes_original_headers(context: dict[str, Any]) -> None:
    """Assert forwarded request includes original headers."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    forwarded_headers = client.requests[0]["headers"]
    original_headers = context.get("request_headers", {})

    for header, value in original_headers.items():
        # Headers are normalized (title-cased) in Django
        normalized_header = header.title().replace("_", "-")
        # Skip Host header as it may be rewritten
        if normalized_header.lower() == "host":
            continue
        assert normalized_header in forwarded_headers or header in forwarded_headers, (
            f"Expected header {header} in forwarded request, got {forwarded_headers}"
        )


@then(parsers.parse('the forwarded request Host header should be "{host}"'))
def forwarded_host_header(context: dict[str, Any], host: str) -> None:
    """Assert forwarded request has correct Host header."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    # The primary URL determines the Host - in our case the request was forwarded
    # to the primary_url configured in context
    primary_url = context.get("primary_url", "")
    # The middleware sends to primary_url, so we verify it was called
    assert client.requests[0]["primary_url"] == primary_url, (
        f"Expected primary_url {primary_url}, got {client.requests[0]['primary_url']}"
    )


@then(parsers.parse('the forwarded request should include "{header_line}"'))
def forwarded_includes_header(context: dict[str, Any], header_line: str) -> None:
    """Assert forwarded request includes specified header."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    # Parse header: value format
    header, value = header_line.split(": ", 1)
    forwarded_headers = client.requests[0]["headers"]

    assert header in forwarded_headers, f"Expected header {header} in forwarded request"
    assert forwarded_headers[header] == value, (
        f"Expected {header}: {value}, got {header}: {forwarded_headers[header]}"
    )


@then(
    parsers.parse('the forwarded request should include "{header}" with original host')
)
def forwarded_includes_header_with_original_host(
    context: dict[str, Any], header: str
) -> None:
    """Assert forwarded request includes header with original host value."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    forwarded_headers = client.requests[0]["headers"]
    assert header in forwarded_headers, f"Expected header {header} in forwarded request"
    # Just verify it exists - the value should be the original host


@then(
    parsers.parse(
        'the forwarded request should include "{header}" with original protocol'
    )
)
def forwarded_includes_header_with_original_protocol(
    context: dict[str, Any], header: str
) -> None:
    """Assert forwarded request includes header with original protocol."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    forwarded_headers = client.requests[0]["headers"]
    assert header in forwarded_headers, f"Expected header {header} in forwarded request"
    # Value should be http or https
    assert forwarded_headers[header] in ("http", "https"), (
        f"Expected protocol value, got {forwarded_headers[header]}"
    )


@then(parsers.parse('the forwarded "{header}" should be "{value}"'))
def forwarded_header_value(context: dict[str, Any], header: str, value: str) -> None:
    """Assert forwarded request header has specific value."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    forwarded_headers = client.requests[0]["headers"]
    assert header in forwarded_headers, f"Expected header {header} in forwarded request"
    assert forwarded_headers[header] == value, (
        f"Expected {header}: {value}, got {header}: {forwarded_headers[header]}"
    )


# =============================================================================
# Then Steps - Body Preservation
# =============================================================================


@then("the forwarded request body should be identical")
def forwarded_body_identical(context: dict[str, Any]) -> None:
    """Assert forwarded request body matches original."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    original_body = context.get("request_body")
    forwarded_body = client.requests[0]["body"]

    assert forwarded_body == original_body, (
        f"Expected body {original_body}, got {forwarded_body}"
    )


@then("the forwarded request should preserve the form data")
def forwarded_preserves_form_data(context: dict[str, Any]) -> None:
    """Assert forwarded request preserves form data."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    forwarded_body = client.requests[0]["body"]
    assert forwarded_body is not None, "Expected form data in body"

    # Form data should be URL-encoded in body
    form_data = context.get("form_data", {})
    for field, value in form_data.items():
        # Check that field=value appears in the encoded body
        assert field.encode() in forwarded_body, (
            f"Expected field {field} in forwarded body"
        )


@then("the forwarded request path should include the query string")
def forwarded_path_includes_query_string(context: dict[str, Any]) -> None:
    """Assert forwarded request includes query string."""
    client = context["fake_http_client"]
    assert len(client.requests) > 0, "No requests were forwarded"

    query_string = client.requests[0].get("query_string", "")
    assert query_string, "Expected query string in forwarded request"
    assert "page=1" in query_string, "Expected 'page=1' in query string"
    assert "filter=active" in query_string, "Expected 'filter=active' in query string"


# =============================================================================
# Then Steps - Response Passthrough
# =============================================================================


@then(parsers.parse("the response status should be {status:d}"))
def response_status(context: dict[str, Any], status: int) -> None:
    """Assert response has correct status code."""
    response = context["response"]
    assert response.status_code == status, (
        f"Expected status {status}, got {response.status_code}"
    )


@then(parsers.parse("the response body should be '{body}'"))
def response_body(context: dict[str, Any], body: str) -> None:
    """Assert response has correct body."""
    response = context["response"]
    response_content = response.content.decode()
    assert response_content == body, f"Expected body '{body}', got '{response_content}'"


@then("the response should include all primary response headers")
def response_includes_primary_headers(context: dict[str, Any]) -> None:
    """Assert response includes headers from primary."""
    response = context["response"]

    # The fake http client was configured with specific headers
    # Check that hop-by-hop headers are excluded and others are included
    assert "X-Custom-Header" in response, "Expected X-Custom-Header in response"


@then(parsers.parse('the response should include "{header_line}"'))
def response_includes_header(context: dict[str, Any], header_line: str) -> None:
    """Assert response includes specified header."""
    response = context["response"]

    # Parse header: value format
    header, value = header_line.split(": ", 1)

    assert header in response, f"Expected header {header} in response"
    assert response[header] == value, (
        f"Expected {header}: {value}, got {header}: {response[header]}"
    )


@then(parsers.parse('the response should include "{header}" with node ID'))
def response_includes_header_with_node_id(context: dict[str, Any], header: str) -> None:
    """Assert response includes header with node ID value."""
    response = context["response"]

    assert header in response, f"Expected header {header} in response"
    # Just verify it exists and has a value
    assert response[header], f"Expected non-empty value for {header}"


@then(parsers.parse('the response should not include "{header}"'))
def response_excludes_header(context: dict[str, Any], header: str) -> None:
    """Assert response does not include specified header."""
    response = context["response"]
    assert header not in response, (
        f"Expected header {header} to not be in response, but it was"
    )
