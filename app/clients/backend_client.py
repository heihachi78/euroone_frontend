"""Async HTTP client for the backend's IP address report endpoint.

Every failure is raised as a `BackendError` whose message and cause describe it for
the log.
"""

import logging
from http import HTTPStatus

import httpx

from app.config.backend_config import BackendConfig
from app.models.ip import Ip
from app.models.ip_analysis import IpAnalysis

logger = logging.getLogger(__name__)


class BackendError(Exception):
    """A backend request failed; the message is meant for the log, not for the user."""


class BackendClient:
    """Client for the backend's IP address report endpoint.

    Call `aclose` when the client is no longer needed, to close its connections.
    """

    def __init__(
        self, config: BackendConfig, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        """Create the HTTP client from the URL and timeout in `config`.

        Pass `transport` to replace the network, as the tests do with a mock transport.
        """
        self._base_url = config.base_url
        self._timeout_seconds = config.timeout_seconds
        self._ip_address_report_endpoint = config.ip_address_report_endpoint
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            transport=transport,
        )

    async def get_ip_address_report(self, ip: Ip) -> IpAnalysis:
        """Ask the backend to analyze an IP address.

        Args:
            ip: The IP address to analyze.

        Returns:
            The backend's analysis, with a Markdown summary of the IP address.

        Raises:
            BackendError: If the backend does not respond in time, the request fails
                otherwise, the status is not 200 OK, or the body is not an
                `IpAnalysis`. The underlying error, if any, is its cause.
        """
        try:
            response = await self._client.post(
                self._ip_address_report_endpoint, json=ip.model_dump(mode="json")
            )
        except httpx.TimeoutException as error:
            raise BackendError(
                f"The backend at {self._base_url} did not respond within "
                f"{self._timeout_seconds} s"
            ) from error
        except httpx.RequestError as error:
            raise BackendError(
                f"Request to the backend at {self._base_url} failed"
            ) from error
        logger.info("Backend responded %d for ip=%s", response.status_code, ip.ip)
        if response.status_code != HTTPStatus.OK:
            raise BackendError(
                f"Backend answered HTTP {response.status_code}: {response.text}"
            )
        try:
            return IpAnalysis.model_validate(response.json())
        except ValueError as error:
            raise BackendError(
                f"Backend answered HTTP 200 with an unusable body: {response.text}"
            ) from error

    async def aclose(self) -> None:
        """Close the underlying HTTP client and its connections."""
        await self._client.aclose()
