import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, request


ACCESS_LOGGER = "soc_sentinel.access"
ERROR_LOGGER = "soc_sentinel.error"


def configure_logging(app: Flask) -> None:
    """Configure rotating application, access, and error logs."""

    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    app_handler = _rotating_handler(log_dir / "application.log", formatter)
    error_handler = _rotating_handler(log_dir / "error.log", formatter)
    access_handler = _rotating_handler(log_dir / "access.log", formatter)

    logging.getLogger().setLevel(level)
    app.logger.setLevel(level)
    app.logger.handlers.clear()
    app.logger.addHandler(app_handler)

    error_logger = logging.getLogger(ERROR_LOGGER)
    error_logger.setLevel(level)
    error_logger.handlers.clear()
    error_logger.addHandler(error_handler)
    error_logger.propagate = False

    access_logger = logging.getLogger(ACCESS_LOGGER)
    access_logger.setLevel(logging.INFO)
    access_logger.handlers.clear()
    access_logger.addHandler(access_handler)
    access_logger.propagate = False

    @app.after_request
    def write_access_log(response):
        access_logger.info(
            "%s %s %s %s %s",
            request.remote_addr or "-",
            request.method,
            request.full_path.rstrip("?"),
            response.status_code,
            request.user_agent.string,
        )
        return response


def _rotating_handler(path: Path, formatter: logging.Formatter) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler
