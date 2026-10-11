"""Tests for `BackendClient`, with the backend faked by `httpx.MockTransport`."""

import json
from collections.abc import Callable

import httpx
import pytest

from app.clients.backend_client import BackendClient, BackendError
from app.config.backend_config import BackendConfig
from app.models.ip import Ip

IP = Ip(ip="8.8.8.8")  # pyright: ignore[reportArgumentType]


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> BackendClient:
    """Create a client whose requests are answered by `handler` instead of the network."""
    config = BackendConfig(base_url="http://backend.test", timeout_seconds=5)
    return BackendClient(config, transport=httpx.MockTransport(handler))


async def test_returns_analysis_and_posts_ip_as_json() -> None:
    """The IP address is posted as JSON to the endpoint, and the analysis is parsed."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Record the request and answer with a valid analysis."""
        requests.append(request)
        return httpx.Response(200, json={"ip": "8.8.8.8", "summary": "**Google DNS**"})

    analysis = await make_client(handler).get_ip_address_report(IP)

    assert analysis.summary == "**Google DNS**"
    assert str(analysis.ip) == "8.8.8.8"
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "http://backend.test/api/v1/ip_address_report"
    assert json.loads(requests[0].content) == {"ip": "8.8.8.8"}


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            httpx.Response(
                502, content=b'{"detail":"An external service could not be reached"}'
            ),
            'Backend answered HTTP 502: {"detail":"An external service could not be reached"}',
        ),
        (
            httpx.Response(500, content=b"Internal Server Error"),
            "Backend answered HTTP 500: Internal Server Error",
        ),
        (
            httpx.Response(
                422,
                content=b'{"detail":[{"msg":"Value error, IP address must be a public unicast address"}]}',
            ),
            'Backend answered HTTP 422: {"detail":[{"msg":"Value error, IP address must be a public unicast address"}]}',
        ),
        (httpx.Response(404, content=b""), "Backend answered HTTP 404: "),
    ],
)
async def test_error_status_raises_backend_error_with_status_and_body(
    response: httpx.Response, expected: str
) -> None:
    """Any status other than 200 raises `BackendError` with the status and the body."""
    client = make_client(lambda request: response)

    with pytest.raises(BackendError) as excinfo:
        await client.get_ip_address_report(IP)

    assert str(excinfo.value) == expected


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (b"<html>", "Backend answered HTTP 200 with an unusable body: <html>"),
        (
            b'{"ip":"8.8.8.8"}',
            'Backend answered HTTP 200 with an unusable body: {"ip":"8.8.8.8"}',
        ),
    ],
)
async def test_unusable_body_raises_backend_error_with_body_and_cause(
    body: bytes, expected: str
) -> None:
    """A 200 body that is not an `IpAnalysis` raises `BackendError` with the body.

    The parsing error is kept as the cause, so it is logged with the error.
    """
    client = make_client(lambda request: httpx.Response(200, content=body))

    with pytest.raises(BackendError) as excinfo:
        await client.get_ip_address_report(IP)

    assert str(excinfo.value) == expected
    assert isinstance(excinfo.value.__cause__, ValueError)


async def test_timeout_raises_backend_error_with_url_timeout_and_cause() -> None:
    """A timeout raises `BackendError` with the URL and the timeout, caused by it."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Fail as if the backend did not respond in time."""
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(BackendError) as excinfo:
        await make_client(handler).get_ip_address_report(IP)

    assert str(excinfo.value) == (
        "The backend at http://backend.test did not respond within 5.0 s"
    )
    assert isinstance(excinfo.value.__cause__, httpx.ReadTimeout)


async def test_connection_error_raises_backend_error_with_url_and_cause() -> None:
    """A connection error raises `BackendError` with the URL, caused by the error."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Fail as if the backend refused the connection."""
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(BackendError) as excinfo:
        await make_client(handler).get_ip_address_report(IP)

    assert str(excinfo.value) == "Request to the backend at http://backend.test failed"
    assert isinstance(excinfo.value.__cause__, httpx.ConnectError)


async def test_undecodable_body_raises_backend_error_with_cause() -> None:
    """A body that cannot be decompressed raises `BackendError`, caused by the error."""
    client = make_client(
        lambda request: httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=b"not gzip"
        )
    )

    with pytest.raises(BackendError) as excinfo:
        await client.get_ip_address_report(IP)

    assert str(excinfo.value) == "Request to the backend at http://backend.test failed"
    assert isinstance(excinfo.value.__cause__, httpx.DecodingError)


class ClosableTransport(httpx.MockTransport):
    """Mock transport that records whether it was closed."""

    def __init__(self) -> None:
        """Create an open transport that answers every request with an empty 200."""
        super().__init__(lambda request: httpx.Response(200))
        self.closed = False

    async def aclose(self) -> None:
        """Mark the transport as closed."""
        self.closed = True


async def test_aclose_closes_the_transport() -> None:
    """`aclose` closes the transport that the client was created with."""
    transport = ClosableTransport()
    client = BackendClient(BackendConfig(base_url="http://backend.test"), transport)

    await client.aclose()

    assert transport.closed
