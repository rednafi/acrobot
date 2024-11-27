import logging


def configure_logger(level: int = logging.INFO) -> logging.Logger:
    """Configure a custom logger."""

    # First configure httpx logger; not configurable
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)

    # Create our own logger
    logger = logging.getLogger("acrobot")
    logger.setLevel(level)

    # Create a handler (console output in this case)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Create a formatter and set it to the handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    # Add the handler to the logger
    if not logger.hasHandlers():
        logger.addHandler(console_handler)

    # Disable propagation to avoid log duplication in some cases
    logger.propagate = False

    return logger
