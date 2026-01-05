"""Unit tests for WriteForwardingMiddleware resilience (retry + circuit breaker)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from django.http import HttpRequest, HttpResponse

from litefs.adapters.ports import ForwardingResult
from litefs.domain.circuit_breaker import CircuitBreaker, CircuitBreakerState
from litefs.domain.retry import RetryPolicy

if TYPE_CHECKING:
    pass


# Mark all tests with tier and TRA markers
pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Resilience"),
]


class FakeTimeProvider:
    """Fake time provider for deterministic testing."""

    def __init__(self, initial_time: float = 0.0) -> None:
        self._time = initial_time

    def get_time_seconds(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds

    def set_time(self, time: float) -> None:
        self._time = time


class FakeSleeper:
    """Fake sleeper to avoid actual delays in tests."""

    def __init__(self) -> None:
        self.sleep_calls: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)


@dataclass
class FakeForwardingPort:
    """Fake forwarding port that can be configured to fail/succeed."""

    responses: list[ForwardingResult | Exception]
    call_count: int = 0

    def forward_request(
        self,
        primary_url: str,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None = None,
        query_string: str = "",
    ) -> ForwardingResult:
        if self.call_count >= len(self.responses):
            raise IndexError("No more configured responses")
        response = self.responses[self.call_count]
        self.call_count += 1
        if isinstance(response, Exception):
            raise response
        return response


def create_request(method: str = "POST", path: str = "/api/test") -> HttpRequest:
    """Create a mock Django request."""
    request = Mock(spec=HttpRequest)
    request.method = method
    request.path = path
    request.body = b'{"test": "data"}'
    request.META = {
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_HOST": "localhost:8000",
        "QUERY_STRING": "",
    }
    request.is_secure.return_value = False
    return request


def create_middleware_with_resilience(
    forwarding_port: FakeForwardingPort,
    retry_policy: RetryPolicy,
    circuit_breaker: CircuitBreaker,
    time_provider: FakeTimeProvider,
    sleeper: FakeSleeper,
    is_primary: bool = False,
) -> "WriteForwardingMiddleware":  # noqa: F821
    """Create middleware with injected resilience components."""
    from litefs_django.middleware import WriteForwardingMiddleware

    def get_response(request: HttpRequest) -> HttpResponse:
        return HttpResponse("Local response", status=200)

    middleware = WriteForwardingMiddleware(get_response)

    # Inject test dependencies
    middleware._forwarding_port = forwarding_port  # type: ignore[assignment]
    middleware._forwarding_enabled = True
    middleware._primary_url = "http://primary:8000"
    middleware._retry_policy = retry_policy
    middleware._circuit_breaker = circuit_breaker
    middleware._time_provider = time_provider
    middleware._sleeper = sleeper
    middleware._circuit_lock = threading.Lock()

    # Mock primary detector
    mock_detector = Mock()
    mock_detector.is_primary.return_value = is_primary
    middleware._primary_detector = mock_detector

    return middleware


# Gateway status codes to retry
GATEWAY_STATUS_CODES = [502, 503, 504]


class TestRetryOnTransientErrors:
    """Test retry behavior for transient errors."""

    def test_retries_on_connection_error(self) -> None:
        """Retry on ConnectionError and succeed on second attempt."""
        success_response = ForwardingResult(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"success": true}',
        )
        port = FakeForwardingPort(
            responses=[
                ConnectionError("Connection refused"),
                success_response,
            ]
        )
        retry_policy = RetryPolicy(max_retries=3, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(threshold=5, reset_timeout=30.0)
        time_provider = FakeTimeProvider()
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        assert response.status_code == 200
        assert port.call_count == 2
        assert len(sleeper.sleep_calls) == 1  # One backoff sleep

    def test_retries_on_timeout_error(self) -> None:
        """Retry on TimeoutError."""
        success_response = ForwardingResult(
            status_code=201, headers={}, body=b"Created"
        )
        port = FakeForwardingPort(
            responses=[
                TimeoutError("Read timed out"),
                success_response,
            ]
        )
        retry_policy = RetryPolicy(max_retries=3, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(threshold=5, reset_timeout=30.0)
        time_provider = FakeTimeProvider()
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        assert response.status_code == 201
        assert port.call_count == 2

    @pytest.mark.parametrize("status_code", GATEWAY_STATUS_CODES)
    def test_retries_on_gateway_status_codes(self, status_code: int) -> None:
        """Retry on gateway errors (502, 503, 504)."""
        gateway_error = ForwardingResult(
            status_code=status_code, headers={}, body=b"Gateway error"
        )
        success_response = ForwardingResult(
            status_code=200, headers={}, body=b"Success"
        )
        port = FakeForwardingPort(responses=[gateway_error, success_response])
        retry_policy = RetryPolicy(max_retries=3, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(threshold=5, reset_timeout=30.0)
        time_provider = FakeTimeProvider()
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        assert response.status_code == 200
        assert port.call_count == 2

    def test_exhausts_retries_then_fails(self) -> None:
        """Return error after exhausting all retries."""
        port = FakeForwardingPort(
            responses=[
                ConnectionError("fail 1"),
                ConnectionError("fail 2"),
                ConnectionError("fail 3"),
                ConnectionError("fail 4"),  # max_retries=3 means 4 total attempts
            ]
        )
        retry_policy = RetryPolicy(max_retries=3, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(
            threshold=10, reset_timeout=30.0
        )  # High threshold
        time_provider = FakeTimeProvider()
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        assert response.status_code == 503  # Service unavailable after retries
        assert port.call_count == 4  # Initial + 3 retries
        assert len(sleeper.sleep_calls) == 3


class TestNoRetryOnPermanentErrors:
    """Test that permanent errors are not retried."""

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 405, 422])
    def test_no_retry_on_4xx_client_errors(self, status_code: int) -> None:
        """Do not retry on client errors (4xx)."""
        client_error = ForwardingResult(
            status_code=status_code, headers={}, body=b"Client error"
        )
        port = FakeForwardingPort(responses=[client_error])
        retry_policy = RetryPolicy(max_retries=3, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(threshold=5, reset_timeout=30.0)
        time_provider = FakeTimeProvider()
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        assert response.status_code == status_code
        assert port.call_count == 1  # No retry
        assert len(sleeper.sleep_calls) == 0

    @pytest.mark.parametrize("status_code", [500, 501, 505, 507])
    def test_no_retry_on_non_gateway_5xx(self, status_code: int) -> None:
        """Do not retry on non-gateway server errors (500, 501, etc.)."""
        server_error = ForwardingResult(
            status_code=status_code, headers={}, body=b"Server error"
        )
        port = FakeForwardingPort(responses=[server_error])
        retry_policy = RetryPolicy(max_retries=3, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(threshold=5, reset_timeout=30.0)
        time_provider = FakeTimeProvider()
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        assert response.status_code == status_code
        assert port.call_count == 1  # No retry


class TestCircuitBreaker:
    """Test circuit breaker behavior."""

    def test_circuit_opens_after_threshold_failures(self) -> None:
        """Circuit opens after consecutive failures reach threshold."""
        port = FakeForwardingPort(
            responses=[
                ConnectionError("fail 1"),
                ConnectionError("fail 2"),
                ConnectionError("fail 3"),
            ]
        )
        retry_policy = RetryPolicy(max_retries=0, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(threshold=3, reset_timeout=30.0)
        time_provider = FakeTimeProvider(initial_time=100.0)
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )

        # Make 3 failing requests to trip the circuit
        for _ in range(3):
            request = create_request()
            middleware(request)

        # Circuit should now be open
        assert middleware._circuit_breaker.state == CircuitBreakerState.OPEN

    def test_returns_503_with_retry_after_when_circuit_open(self) -> None:
        """Return 503 with Retry-After when circuit is open."""
        port = FakeForwardingPort(responses=[])  # Won't be called
        retry_policy = RetryPolicy(max_retries=0, backoff_base=0.1, max_backoff=1.0)
        # Pre-open circuit
        circuit_breaker = CircuitBreaker(
            threshold=3,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
            failure_count=3,
        )
        time_provider = FakeTimeProvider(initial_time=110.0)  # Within timeout
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        assert response.status_code == 503
        assert "Retry-After" in response
        assert port.call_count == 0  # Request blocked

    def test_probe_allowed_after_timeout_elapsed(self) -> None:
        """Allow probe request after timeout elapses."""
        success_response = ForwardingResult(
            status_code=200, headers={}, body=b"Success"
        )
        port = FakeForwardingPort(responses=[success_response])
        retry_policy = RetryPolicy(max_retries=0, backoff_base=0.1, max_backoff=1.0)
        # Circuit open for 30s timeout
        circuit_breaker = CircuitBreaker(
            threshold=3,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
            failure_count=3,
        )
        # Time is past timeout
        time_provider = FakeTimeProvider(initial_time=135.0)
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        # Probe was allowed and succeeded
        assert response.status_code == 200
        assert port.call_count == 1

    def test_successful_probe_closes_circuit(self) -> None:
        """Successful probe request closes the circuit."""
        success_response = ForwardingResult(
            status_code=200, headers={}, body=b"Success"
        )
        port = FakeForwardingPort(responses=[success_response])
        retry_policy = RetryPolicy(max_retries=0, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(
            threshold=3,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
            failure_count=3,
        )
        time_provider = FakeTimeProvider(initial_time=135.0)  # Past timeout
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        middleware(request)

        assert middleware._circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_failed_probe_reopens_circuit(self) -> None:
        """Failed probe request reopens the circuit."""
        port = FakeForwardingPort(responses=[ConnectionError("fail")])
        retry_policy = RetryPolicy(max_retries=0, backoff_base=0.1, max_backoff=1.0)
        circuit_breaker = CircuitBreaker(
            threshold=3,
            reset_timeout=30.0,
            state=CircuitBreakerState.HALF_OPEN,  # Already transitioned
            opened_at=100.0,
            failure_count=0,
        )
        time_provider = FakeTimeProvider(initial_time=135.0)
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        middleware(request)

        assert middleware._circuit_breaker.state == CircuitBreakerState.OPEN

    def test_circuit_disabled_bypasses_all_logic(self) -> None:
        """Disabled circuit breaker allows all requests."""
        success_response = ForwardingResult(
            status_code=200, headers={}, body=b"Success"
        )
        port = FakeForwardingPort(responses=[success_response])
        retry_policy = RetryPolicy(max_retries=0, backoff_base=0.1, max_backoff=1.0)
        # Circuit is open but disabled
        circuit_breaker = CircuitBreaker(
            threshold=3,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
            failure_count=3,
            disabled=True,
        )
        time_provider = FakeTimeProvider(initial_time=105.0)  # Within timeout
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        response = middleware(request)

        # Request allowed despite circuit being "open"
        assert response.status_code == 200
        assert port.call_count == 1


class TestBackoffCalculation:
    """Test exponential backoff behavior."""

    def test_exponential_backoff_delays(self) -> None:
        """Verify exponential backoff is applied correctly."""
        port = FakeForwardingPort(
            responses=[
                ConnectionError("fail 1"),
                ConnectionError("fail 2"),
                ConnectionError("fail 3"),
                ForwardingResult(status_code=200, headers={}, body=b"Success"),
            ]
        )
        retry_policy = RetryPolicy(max_retries=3, backoff_base=1.0, max_backoff=30.0)
        circuit_breaker = CircuitBreaker(threshold=10, reset_timeout=30.0)
        time_provider = FakeTimeProvider()
        sleeper = FakeSleeper()

        middleware = create_middleware_with_resilience(
            port, retry_policy, circuit_breaker, time_provider, sleeper
        )
        request = create_request()

        middleware(request)

        # Expected: 1.0 * 2^0 = 1.0, 1.0 * 2^1 = 2.0, 1.0 * 2^2 = 4.0
        assert sleeper.sleep_calls == [1.0, 2.0, 4.0]


class TestSettingsIntegration:
    """Test that settings are properly read and applied."""

    def test_middleware_creates_retry_policy_from_settings(self) -> None:
        """Middleware creates RetryPolicy from ForwardingSettings."""
        from litefs_django.middleware import WriteForwardingMiddleware

        litefs_config = {
            "ENABLED": True,
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PRIMARY_HOSTNAME": "primary",
            "PROXY_ADDR": ":8080",
            "RETENTION": "24h",
            "FORWARDING": {
                "ENABLED": True,
                "PRIMARY_URL": "http://primary:8000",
                "RETRY_COUNT": 5,
                "RETRY_BACKOFF_BASE": 0.5,
                "CIRCUIT_BREAKER_THRESHOLD": 10,
                "CIRCUIT_BREAKER_RESET_TIMEOUT": 60.0,
                "CIRCUIT_BREAKER_ENABLED": True,
            },
        }

        with patch("litefs_django.middleware.django_settings") as mock_settings:
            mock_settings.LITEFS = litefs_config
            with patch(
                "litefs.usecases.primary_detector.PrimaryDetector"
            ) as mock_detector:
                mock_detector.return_value.is_primary.return_value = False

                def get_response(r: HttpRequest) -> HttpResponse:
                    return HttpResponse("OK")

                middleware = WriteForwardingMiddleware(get_response)

                assert middleware._retry_policy is not None
                assert middleware._retry_policy.max_retries == 5
                assert middleware._retry_policy.backoff_base == 0.5

                assert middleware._circuit_breaker is not None
                assert middleware._circuit_breaker.threshold == 10
                assert middleware._circuit_breaker.reset_timeout == 60.0

    def test_circuit_breaker_disabled_when_configured(self) -> None:
        """Circuit breaker is disabled when CIRCUIT_BREAKER_ENABLED=False."""
        from litefs_django.middleware import WriteForwardingMiddleware

        litefs_config = {
            "ENABLED": True,
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PRIMARY_HOSTNAME": "primary",
            "PROXY_ADDR": ":8080",
            "RETENTION": "24h",
            "FORWARDING": {
                "ENABLED": True,
                "PRIMARY_URL": "http://primary:8000",
                "CIRCUIT_BREAKER_ENABLED": False,
            },
        }

        with patch("litefs_django.middleware.django_settings") as mock_settings:
            mock_settings.LITEFS = litefs_config
            with patch(
                "litefs.usecases.primary_detector.PrimaryDetector"
            ) as mock_detector:
                mock_detector.return_value.is_primary.return_value = False

                def get_response(r: HttpRequest) -> HttpResponse:
                    return HttpResponse("OK")

                middleware = WriteForwardingMiddleware(get_response)

                assert middleware._circuit_breaker is not None
                assert middleware._circuit_breaker.disabled is True
