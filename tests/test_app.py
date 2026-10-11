"""app/app.py runs via runpy, with NiceGUI's server and the backend client stubbed out."""

import runpy
from collections.abc import Callable
from typing import Any

import pytest
from nicegui import app as nicegui_app
from nicegui import ui

from app.config.backend_config import BackendConfig, backend_config


class FakeBackendClient:
    """Stand-in for `BackendClient` that records its config and whether it is closed."""

    def __init__(self, config: BackendConfig) -> None:
        """Create an open client that keeps the `config` it was created with."""
        self.config = config
        self.closed = False

    async def aclose(self) -> None:
        """Mark the client as closed."""
        self.closed = True


class Server:
    """Records what `app.app` asks of NiceGUI, instead of starting a real server.

    Attributes:
        clients: The backend clients created so far.
        logging_setups: How many times logging was set up.
        pages: The backend client passed to each `build_page` call.
        runs: The `root` function and keyword arguments of each `ui.run` call.
        shutdown_handlers: The functions registered with `app.on_shutdown`.
    """

    def __init__(self) -> None:
        """Create a server that has recorded nothing yet."""
        self.clients: list[FakeBackendClient] = []
        self.logging_setups = 0
        self.pages: list[FakeBackendClient] = []
        self.runs: list[tuple[Callable[[], None], dict[str, Any]]] = []
        self.shutdown_handlers: list[Callable[[], Any]] = []

    def setup_logging(self) -> None:
        """Record a logging setup instead of configuring the root logger."""
        self.logging_setups += 1

    def create_client(self, config: BackendConfig) -> FakeBackendClient:
        """Create a fake backend client and record it."""
        client = FakeBackendClient(config)
        self.clients.append(client)
        return client

    def run(self, root: Callable[[], None], **kwargs: Any) -> None:
        """Record a `ui.run` call instead of starting the server."""
        self.runs.append((root, kwargs))


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> Server:
    """Replace NiceGUI's server, the backend client and logging with a recording `Server`."""
    server = Server()
    monkeypatch.setattr("app.core.logging.setup_logging", server.setup_logging)
    monkeypatch.setattr(ui, "run", server.run)
    monkeypatch.setattr(nicegui_app, "on_shutdown", server.shutdown_handlers.append)
    monkeypatch.setattr(
        "app.clients.backend_client.BackendClient", server.create_client
    )
    monkeypatch.setattr("app.pages.page.build_page", server.pages.append)
    return server


def test_importing_does_not_start_the_server(server: Server) -> None:
    """Importing `app.app` neither sets up logging, nor creates a client or a server."""
    runpy.run_module("app.app")

    assert server.logging_setups == 0
    assert server.runs == []
    assert server.clients == []


@pytest.mark.parametrize("run_name", ["__main__", "__mp_main__"])
def test_running_as_main_starts_the_server(server: Server, run_name: str) -> None:
    """Running as a script or as the reload worker sets up logging once, then starts
    the server with one client.
    """
    runpy.run_module("app.app", run_name=run_name)

    assert server.logging_setups == 1
    [client] = server.clients
    assert client.config is backend_config
    [(root, options)] = server.runs
    assert options == {"title": "IP address summary"}
    assert server.pages == []  # NiceGUI calls root for each visitor

    root()

    assert server.pages == [client]


async def test_shutdown_closes_the_backend_client(server: Server) -> None:
    """The shutdown handler registered at startup closes the backend client."""
    runpy.run_module("app.app", run_name="__main__")
    [client] = server.clients
    [on_shutdown] = server.shutdown_handlers

    await on_shutdown()

    assert client.closed
