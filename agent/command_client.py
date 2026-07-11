import logging
import threading

import requests

from api_client import APIClient
from command_executor import CommandExecutor


def start_command_polling_thread(
    client: APIClient,
    executor: CommandExecutor,
    logger: logging.Logger,
    stop_event: threading.Event,
    interval_seconds: int = 10,
) -> threading.Thread:
    """Start the dedicated endpoint command polling loop."""

    thread = threading.Thread(
        target=_poll_loop,
        args=(client, executor, logger, stop_event, interval_seconds),
        name="command-poller",
        daemon=True,
    )
    thread.start()
    return thread


def _poll_loop(
    client: APIClient,
    executor: CommandExecutor,
    logger: logging.Logger,
    stop_event: threading.Event,
    interval_seconds: int,
) -> None:
    """Poll for commands and report execution results."""

    backoff_seconds = interval_seconds
    while not stop_event.is_set():
        try:
            commands = client.get_pending_commands()
            backoff_seconds = interval_seconds
            for command in commands:
                _execute_and_report(client, executor, logger, command)
        except requests.RequestException as exc:
            logger.warning("Command polling failed: %s", exc)
            stop_event.wait(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 300)
            continue

        stop_event.wait(interval_seconds)


def _execute_and_report(
    client: APIClient,
    executor: CommandExecutor,
    logger: logging.Logger,
    command: dict,
) -> None:
    command_id = str(command.get("command_id", ""))
    command_type = str(command.get("command_type", ""))
    logger.info("Executing endpoint command %s (%s).", command_id, command_type)
    client.send_command_result(command_id, "RUNNING")
    status, response, error_message = executor.execute(command)
    client.send_command_result(command_id, status, response, error_message)
