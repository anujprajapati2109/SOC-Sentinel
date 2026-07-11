import logging
import threading
import time

import requests

from api_client import APIClient
from agent_state import AgentState


def run_heartbeat_loop(
    client: APIClient,
    interval_seconds: int,
    logger: logging.Logger,
    stop_event: threading.Event | None = None,
    state: AgentState | None = None,
) -> None:
    """Send heartbeat messages forever with exponential backoff on failure."""

    backoff_seconds = 1
    max_backoff_seconds = 300

    while stop_event is None or not stop_event.is_set():
        try:
            response = client.heartbeat()
            endpoint = response.get("endpoint", {})
            logger.info(
                "Heartbeat accepted for %s. Status: %s",
                endpoint.get("endpoint_id", "unknown"),
                endpoint.get("status", "unknown"),
            )
            if state is not None:
                state.record_heartbeat()
            backoff_seconds = 1
            if stop_event is None:
                time.sleep(interval_seconds)
            else:
                stop_event.wait(interval_seconds)
        except requests.RequestException as exc:
            logger.warning(
                "Heartbeat failed: %s. Retrying in %s seconds.",
                exc,
                backoff_seconds,
            )
            if state is not None:
                state.set_connection_status("Disconnected")
            if stop_event is None:
                time.sleep(backoff_seconds)
            else:
                stop_event.wait(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
