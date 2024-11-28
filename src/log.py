import logging
import os

import logfire

from src import settings
from src.conf import Env


def configure_logger(level: int = logging.INFO) -> logging.Logger:
    """Configure a custom logger."""

    # Create logfire handler
    environment = os.environ.get("ENVIRONMENT", None)
    logfire_token = settings.logfire_token if environment == Env.PROD else None
    send_to_logfire = bool(logfire_token)
    logfire.configure(
        token=logfire_token,
        service_name="acrobot",
        environment=environment,
        send_to_logfire=send_to_logfire,
    )

    logfire_handler = logfire.LogfireLoggingHandler()
    logfire_handler.setLevel(level)

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logfire_handler.setFormatter(formatter)

    # Configure httpx logger
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)

    if not httpx_logger.hasHandlers():
        httpx_logger.addHandler(logfire_handler)
    httpx_logger.propagate = False

    # Configure acrobot logger
    logger = logging.getLogger("acrobot")
    logger.setLevel(level)
    if not logger.hasHandlers():
        logger.addHandler(logfire_handler)
    logger.propagate = False

    return logger
