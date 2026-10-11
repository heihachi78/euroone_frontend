"""Tests for the page, driven by NiceGUI's simulated user against a fake backend."""

import asyncio
import logging
from collections.abc import AsyncIterator

import pytest
from nicegui import ui
from nicegui.testing import (
    User,
    user_simulation,  # pyright: ignore[reportUnknownVariableType]
)

from app.clients.backend_client import BackendClient, BackendError
from app.models.ip import EMPTY_IP_MESSAGE, Ip
from app.models.ip_analysis import IpAnalysis
from app.pages.page import ERROR_MESSAGE, build_page


class FakeBackendClient(BackendClient):
    """Stand-in for `BackendClient` that records requests and returns a set result.

    Attributes:
        calls: The IP addresses requested so far.
        error: If set, raised instead of returning an analysis.
        release: If set, each request waits until this event is set.
        summary: If set, returned as the summary instead of `"Summary for <ip>"`.
    """

    def __init__(self) -> None:  # no super().__init__: no HTTP client is needed
        """Create a fake that immediately returns `"Summary for <ip>"`."""
        self.calls: list[Ip] = []
        self.error: Exception | None = None
        self.release: asyncio.Event | None = None
        self.summary: str | None = None

    async def get_ip_address_report(self, ip: Ip) -> IpAnalysis:
        """Record the request, then return an analysis or raise `error`."""
        self.calls.append(ip)
        if self.release is not None:
            await self.release.wait()
        if self.error is not None:
            raise self.error
        return IpAnalysis(ip=ip.ip, summary=self.summary or f"Summary for {ip.ip}")


@pytest.fixture
def backend() -> FakeBackendClient:
    """Return a new fake backend client."""
    return FakeBackendClient()


@pytest.fixture
async def user(backend: FakeBackendClient) -> AsyncIterator[User]:
    """Open the page for a simulated user, with requests going to the fake backend."""
    async with user_simulation(root=lambda: build_page(backend)) as user:
        await user.open("/")
        yield user


def summarize_button(user: User) -> ui.button:
    """Return the Summarize button of the page."""
    return user.find(kind=ui.button, content="Summarize").elements.pop()


@pytest.mark.parametrize(
    ("value", "sent"),
    [
        ("8.8.8.8", "8.8.8.8"),
        ("2001:4860:4860::8888", "2001:4860:4860::8888"),
        ("  8.8.8.8 ", "8.8.8.8"),
    ],
)
async def test_valid_ip_shows_summary(
    user: User, backend: FakeBackendClient, value: str, sent: str
) -> None:
    """A valid IP address is sent, trimmed, to the backend and its summary is shown."""
    user.find(ui.input).type(value)
    user.find("Summarize").click()

    await user.should_see(f"Summary for {sent}")
    assert [str(ip.ip) for ip in backend.calls] == [sent]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("1.2.3", "value is not a valid IPv4 or IPv6 address"),
        ("192.168.1.1", "IP address must be a public unicast address"),
    ],
)
async def test_invalid_ip_shows_error_and_disables_summarize(
    user: User, backend: FakeBackendClient, value: str, message: str
) -> None:
    """An invalid IP address shows its validation error while typing.

    Summarize is disabled, so no request can be sent.
    """
    user.find(ui.input).type(value)

    await user.should_see(message)
    assert not summarize_button(user).enabled
    user.find("Summarize").click()  # ignored, the button is disabled
    assert backend.calls == []


@pytest.mark.parametrize("value", ["", "   "])
async def test_empty_input_disables_summarize_without_an_error(
    user: User, backend: FakeBackendClient, value: str
) -> None:
    """Summarize is disabled while the input is empty or blank, with no error shown."""
    user.find(ui.input).type(value)

    assert not summarize_button(user).enabled
    user.find("Summarize").click()  # ignored, the button is disabled
    await user.should_not_see(EMPTY_IP_MESSAGE)
    assert backend.calls == []


async def test_summarize_is_enabled_only_while_the_ip_is_valid(user: User) -> None:
    """Summarize follows the validity of the input as the user types."""
    ip_input = user.find(ui.input)

    ip_input.type("8.8.8")
    assert not summarize_button(user).enabled
    ip_input.type(".8")
    assert summarize_button(user).enabled
    ip_input.type(".8")
    assert not summarize_button(user).enabled


async def test_clear_resets_input_and_summary(user: User) -> None:
    """Clear empties the input and removes the summary."""
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    await user.should_see("Summary for 8.8.8.8")

    user.find("Clear").click()

    await user.should_not_see("Summary for 8.8.8.8")
    ip_input = user.find(ui.input).elements.pop()
    assert ip_input.value == ""
    assert ip_input.error is None


async def test_clear_disables_summarize(user: User) -> None:
    """Clear disables Summarize again, also after a finished request enabled it."""
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    await user.should_see("Summary for 8.8.8.8")
    assert summarize_button(user).enabled

    user.find("Clear").click()

    assert not summarize_button(user).enabled


async def test_result_card_is_shown_only_with_a_result(user: User) -> None:
    """The result card is hidden until Summarize is clicked and again after Clear."""
    await user.should_not_see(marker="result")

    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    await user.should_see("Summary for 8.8.8.8")
    await user.should_see(marker="result")

    user.find("Clear").click()
    await user.should_not_see(marker="result")


async def test_clear_removes_validation_error(user: User) -> None:
    """Clear removes the validation error of an invalid IP address."""
    user.find(ui.input).type("1.2.3")
    await user.should_see("value is not a valid IPv4 or IPv6 address")

    user.find("Clear").click()

    await user.should_not_see("value is not a valid IPv4 or IPv6 address")
    assert user.find(ui.input).elements.pop().error is None


BACKEND_ERROR = BackendError(
    'Backend answered HTTP 502: {"detail":"An external service could not be reached"}'
)


async def test_backend_error_shows_only_a_generic_message_and_retry_works(
    user: User, backend: FakeBackendClient
) -> None:
    """A backend error shows a generic message instead of its details.

    A successful retry replaces the message with the summary.
    """
    backend.error = BACKEND_ERROR
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    await user.should_see(ERROR_MESSAGE)
    await user.should_not_see("Backend answered")

    backend.error = None
    user.find("Summarize").click()

    await user.should_see("Summary for 8.8.8.8")
    await user.should_not_see(ERROR_MESSAGE)
    assert len(backend.calls) == 2


async def test_unexpected_error_shows_the_generic_message_and_enables_controls(
    user: User, backend: FakeBackendClient
) -> None:
    """An error that is not a `BackendError` also ends the request with the message."""
    backend.error = RuntimeError("unexpected")
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()

    await user.should_see(ERROR_MESSAGE)
    await user.should_not_see(ui.spinner)
    assert summarize_button(user).enabled


@pytest.mark.parametrize("error", [BACKEND_ERROR, RuntimeError("unexpected")])
async def test_failure_is_logged_with_the_ip_address_and_the_error(
    user: User,
    backend: FakeBackendClient,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    """A failed request is logged at ERROR level with the IP address and the error."""
    backend.error = error
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    await user.should_see(ERROR_MESSAGE)

    [record] = [record for record in caplog.records if record.name == "app.pages.page"]
    assert record.levelno == logging.ERROR
    assert record.getMessage() == "Could not get the summary of ip=8.8.8.8"
    assert record.exc_info is not None
    assert record.exc_info[1] is error


async def test_controls_are_disabled_while_request_is_running(
    user: User, backend: FakeBackendClient
) -> None:
    """Summarize is disabled until the request finishes, so extra clicks are ignored."""
    backend.release = asyncio.Event()
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    await user.should_see(ui.spinner)

    assert not summarize_button(user).enabled
    user.find("Summarize").click()  # ignored, the button is disabled
    backend.release.set()

    await user.should_see("Summary for 8.8.8.8")
    assert summarize_button(user).enabled
    assert len(backend.calls) == 1


async def test_double_click_sends_one_request(
    user: User, backend: FakeBackendClient
) -> None:
    """A double click on Summarize sends only one request."""
    backend.release = asyncio.Event()
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    user.find("Summarize").click()
    await user.should_see(ui.spinner)
    backend.release.set()

    await user.should_see("Summary for 8.8.8.8")
    assert len(backend.calls) == 1


async def test_indented_summary_is_not_clipped(
    user: User, backend: FakeBackendClient
) -> None:
    """A summary whose first line is indented is shown in full.

    `ui.markdown` removes the first line's indentation from every line, so without
    stripping the summary it would cut off the start of the less indented lines.
    """
    backend.summary = "  **8.8.8.8** is Google DNS.\nIt is harmless."
    user.find(ui.input).type("8.8.8.8")
    user.find("Summarize").click()
    await user.should_see(ui.markdown)

    markdown = user.find(ui.markdown).elements.pop()
    assert "It is harmless." in markdown.props["innerHTML"]
