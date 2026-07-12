import logging
import sys
import threading

import requests

from agent_state import AgentState
from api_client import APIClient
from config import AgentConfig, load_config
from logger import setup_logger
from registration import ensure_registered
from runtime import RuntimeManager
from startup import install_startup
from tray import TrayApp
from utils import build_status_banner


def main() -> int:
    """Start the SOC Sentinel Windows background agent."""

    config = load_config()
    logger = setup_logger(config.log_level)
    client = APIClient(config)
    state = AgentState(config)

    logger.info(build_status_banner(config))

    if config.run_at_startup:
        install_startup_safely(logger)

    register_with_retry(config, client, logger)

    runtime = RuntimeManager(config, client, logger, state)
    runtime.start()

    try:
        if config.show_tray_icon:
            TrayApp(runtime, state).run()
        else:
            wait_until_stopped(runtime.stop_event)
    except KeyboardInterrupt:
        logger.info("Ctrl+C received. Stopping SOC Sentinel agent gracefully.")
        runtime.stop()
        return 0

    return 0


def install_startup_safely(logger: logging.Logger) -> None:
    """Install startup entry without breaking the agent if registry access fails."""

    try:
        install_startup()
        logger.info("Startup registration verified.")
    except OSError as exc:
        logger.warning("Startup registration failed: %s", exc)


def register_with_retry(
    config: AgentConfig,
    client: APIClient,
    logger: logging.Logger,
) -> None:
    """Register with exponential backoff until the server becomes available."""

    stop_event = threading.Event()
    backoff_seconds = 1
    max_backoff_seconds = 300

    while True:
        try:
            ensure_registered(config, client, logger)
            if config.is_registered:
                return
        except (KeyError, requests.RequestException, ValueError) as exc:
            logger.warning(
                "Registration failed: %s. Retrying in %s seconds.",
                exc,
                backoff_seconds,
            )
            stop_event.wait(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)


def wait_until_stopped(stop_event: threading.Event) -> None:
    """Block without a tray icon until the process is terminated."""

    while not stop_event.wait(1):
        pass


if __name__ == "__main__":
    sys.exit(main())
