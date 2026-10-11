"""Logging setup of the application."""

import logging


def setup_logging() -> None:
    """Make the root logger log INFO and above with time, level and logger name.

    Does nothing if the root logger already has handlers.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
