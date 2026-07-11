import logging


def get_logger(name: str) -> logging.Logger:
    """Return a project logger with standard formatting."""

    return logging.getLogger(name)
