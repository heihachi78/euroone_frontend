"""Entry point that sets up logging and starts the NiceGUI server of the summary page."""

from nicegui import app as nicegui_app
from nicegui import ui

from app.clients.backend_client import BackendClient
from app.config.backend_config import backend_config
from app.core.logging import setup_logging
from app.pages.page import build_page

if __name__ in {"__main__", "__mp_main__"}:
    setup_logging()
    client = BackendClient(backend_config)
    nicegui_app.on_shutdown(client.aclose)  # pyright: ignore[reportUnknownMemberType]
    ui.run(lambda: build_page(client), title="IP address summary")  # pyright: ignore[reportUnknownMemberType]
