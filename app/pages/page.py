"""The page where the user enters an IP address and reads the backend's summary."""

import logging

from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from app.clients.backend_client import BackendClient
from app.models.ip import Ip, ip_error

logger = logging.getLogger(__name__)

ERROR_MESSAGE = "Unfortunately, something went wrong and no summary could be created."


def build_page(client: BackendClient) -> None:
    """Build the IP address summary page for one visitor.

    Summarize is enabled only while the input holds a valid IP address. It shows the
    backend's summary, or if anything fails, `ERROR_MESSAGE` below the buttons. The
    failure itself is only logged. The input and buttons are disabled while the
    request runs.

    Args:
        client: The backend client that fetches the IP address reports.
    """

    async def summarize() -> None:
        """Show the backend's summary of the entered IP address or `ERROR_MESSAGE`.

        Does nothing while Summarize is disabled, so a double click sends one request.
        """
        if not summarize_button.enabled:
            return
        value = (ip_input.value or "").strip()
        set_busy(True)
        result.clear()
        result_card.set_visibility(True)
        with result:
            ui.spinner()
        try:
            analysis = await client.get_ip_address_report(Ip(ip=value))  # pyright: ignore[reportArgumentType]
        except Exception:
            logger.exception("Could not get the summary of ip=%s", value)
            result.clear()
            with result:
                ui.label(ERROR_MESSAGE).classes("text-negative")
        else:
            result.clear()
            with result:
                ui.markdown(analysis.summary.strip())
        finally:
            set_busy(False)

    def clear() -> None:
        """Empty the input, and remove its validation error and the result."""
        ip_input.value = ""
        ip_input.error = None
        result.clear()
        result_card.set_visibility(False)

    def set_busy(busy: bool) -> None:
        """Disable the input and buttons if `busy`, otherwise enable them.

        Enabling Summarize is safe: the input cannot change while the request runs,
        so it still holds the valid IP address that was sent.
        """
        for element in (ip_input, summarize_button, clear_button):
            element.set_enabled(not busy)

    def update_summarize_button(event: ValueChangeEventArguments[str | None]) -> None:
        """Enable Summarize only if the new input value is a valid IP address."""
        summarize_button.set_enabled(ip_error(event.value or "") is None)

    with ui.column().classes("w-full max-w-2xl mx-auto p-4"):
        with ui.card().classes("w-full bg-grey-2"):
            ui.label("IP address summary").classes("text-2xl")
            ip_input = ui.input(
                "IP address",
                on_change=update_summarize_button,
                validation=lambda value: ip_error(value) if value.strip() else None,
            ).classes("w-full")
            with ui.row():
                summarize_button = ui.button("Summarize", on_click=summarize).disable()
                clear_button = ui.button("Clear", on_click=clear).props("outline")
        with ui.card().classes("w-full bg-grey-2").mark("result") as result_card:
            ui.label("Summary").classes("text-2xl")
            result = ui.column().classes("w-full")
        result_card.set_visibility(False)
