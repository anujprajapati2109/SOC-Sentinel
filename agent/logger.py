import logging
from logging.handlers import RotatingFileHandler

from config import BASE_DIR


LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "agent.log"


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """Configure structured file and console logging for the agent."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("soc_sentinel_agent")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
