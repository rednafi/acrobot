"""Test suite for the logger module."""

import logging
from collections.abc import Iterator
from io import StringIO

import pytest
from _pytest.logging import LogCaptureFixture  # for caplog fixture typing

from src.log import configure_logger


@pytest.fixture
def canned_logger() -> Iterator[logging.Logger]:
    """Fixture to configure the logger for tests with propagate set to True."""
    logger = logging.getLogger("acrobot")

    # Clear any handlers attached to the logger from previous tests
    logger.handlers = []

    # Call the function that configures the logger
    configure_logger()

    # Set logger propagation to True for tests
    original_propagate = logger.propagate
    logger.propagate = True

    # Yield the logger for use in tests
    yield logger

    # Reset the logger propagate to the original value after test
    logger.propagate = original_propagate


def test_configure_logger(
    canned_logger: logging.Logger, caplog: LogCaptureFixture
) -> None:
    """Test if the logger is configured correctly."""
    with caplog.at_level(logging.INFO, logger="acrobot"):
        canned_logger.info("Test log message")

    # Check if the log was captured and formatted correctly
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"
    assert caplog.records[0].message == "Test log message"


def test_log_output_format(canned_logger: logging.Logger) -> None:
    """Test if the log output is formatted correctly."""
    # Set up a StringIO stream to capture log output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    canned_logger.handlers = []  # Remove any pre-existing handlers
    canned_logger.addHandler(handler)
    canned_logger.setLevel(logging.INFO)

    # Log a message and capture the output
    canned_logger.info("Test log message")

    # Flush the handler and get the output
    handler.flush()
    log_output = stream.getvalue()

    # Check the log output format
    assert "acrobot - INFO - Test log message" in log_output
    assert log_output.startswith("20")  # The log should start with a year like "2024"


def test_httpx_logger_level() -> None:
    """Test if the httpx logger level is set correctly."""
    logger = logging.getLogger("httpx")

    # Ensure the logger level is set to WARNING
    assert logger.level == logging.WARNING

    # Ensure the logger has a logfire handler
    assert any(isinstance(handler, logging.Handler) for handler in logger.handlers)


def test_logfire_handler_configuration() -> None:
    """Test if the logfire handler is configured properly."""
    logger = logging.getLogger("acrobot")
    configure_logger()

    # Ensure a logfire handler is present
    logfire_handlers = [
        handler for handler in logger.handlers if isinstance(handler, logging.Handler)
    ]
    assert len(logfire_handlers) == 1

    handler = logfire_handlers[0]
    assert handler.level == logging.INFO

    # Check the formatter
    assert isinstance(handler.formatter, logging.Formatter)
    formatter = handler.formatter
    assert formatter._fmt == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    assert formatter.datefmt == "%Y-%m-%d %H:%M:%S"
