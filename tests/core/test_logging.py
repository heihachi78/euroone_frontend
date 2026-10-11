"""Tests for the logging setup."""

import logging
import re
from collections.abc import Generator
from contextlib import contextmanager

from app.core.logging import setup_logging


@contextmanager
def bare_root_logger() -> Generator[logging.Logger]:
    """Remove the root logger's handlers for the block, then restore handlers and level."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    root.handlers.clear()
    try:
        yield root
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def test_sets_root_level_to_info() -> None:
    """On an unconfigured root logger, the level is set to INFO."""
    with bare_root_logger() as root:
        root.setLevel(logging.WARNING)

        setup_logging()

        assert root.level == logging.INFO


def test_adds_one_stream_handler() -> None:
    """Exactly one stream handler is added to the root logger."""
    with bare_root_logger() as root:
        setup_logging()

        [handler] = root.handlers
        assert isinstance(handler, logging.StreamHandler)


def test_formats_timestamp_level_logger_name_and_message() -> None:
    """Records are formatted as timestamp, level, [logger name] and message."""
    with bare_root_logger() as root:
        setup_logging()

        [handler] = root.handlers
        record = logging.LogRecord(
            "app.test", logging.WARNING, __file__, 1, "hello %s", ("world",), None
        )
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} WARNING \[app\.test\] hello world",
            handler.format(record),
        )


def test_keeps_existing_logging_configuration() -> None:
    """A root logger that already has handlers is left unchanged, level included."""
    with bare_root_logger() as root:
        existing = logging.NullHandler()
        root.addHandler(existing)
        root.setLevel(logging.ERROR)

        setup_logging()

        assert root.handlers == [existing]
        assert root.level == logging.ERROR
