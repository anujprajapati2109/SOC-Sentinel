import logging
import threading
from collections.abc import Callable

import requests

from agent_state import AgentState
from api_client import APIClient
from command_client import start_command_polling_thread
from command_executor import CommandExecutor
from collectors.event_logs import start_windows_event_collector
from collectors.file_monitor import start_file_collector
from collectors.process_monitor import start_process_collector
from config import AgentConfig
from heartbeat import run_heartbeat_loop
from registration import ensure_registered
from telemetry_queue import TelemetryQueue, start_sender_thread


ThreadStarter = Callable[[], threading.Thread]


class RuntimeManager:
    """Owns worker threads and coordinates clean shutdown."""

    def __init__(
        self,
        config: AgentConfig,
        client: APIClient,
        logger: logging.Logger,
        state: AgentState,
    ) -> None:
        self.config = config
        self.client = client
        self.logger = logger
        self.state = state
        self.stop_event = threading.Event()
        self.telemetry_queue = TelemetryQueue()
        self.command_executor = CommandExecutor(
            self.client,
            self.telemetry_queue,
            self.logger,
            self.state,
        )
        self.threads: dict[str, threading.Thread] = {}
        self.starters: dict[str, ThreadStarter] = {}
        self.restart_counts: dict[str, int] = {}
        self.max_restarts = 3

    def start(self) -> None:
        """Start all background workers."""

        self.starters = {
            "telemetry-sender": self._start_sender,
            "heartbeat": self._start_heartbeat,
            "command-poller": self._start_command_poller,
            "process-collector": self._start_process_collector,
            "file-collector": self._start_file_collector,
            "windows-event-collector": self._start_windows_event_collector,
        }
        for name, starter in self.starters.items():
            self.threads[name] = starter()

        self.threads["health-monitor"] = self._start_health_monitor()
        self.logger.info("Telemetry collection engine started.")

    def stop(self) -> None:
        """Stop workers and flush queued telemetry best-effort."""

        self.logger.info("Stopping SOC Sentinel agent.")
        self.stop_event.set()
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join(timeout=10)
        self.logger.info("Agent stopped gracefully.")

    def reconnect(self) -> None:
        """Attempt immediate registration or heartbeat."""

        try:
            if not self.config.is_registered:
                ensure_registered(self.config, self.client, self.logger)
            response = self.client.heartbeat()
            self.state.record_heartbeat()
            self.logger.info("Manual reconnect succeeded: %s", response)
        except (KeyError, ValueError, requests.RequestException) as exc:
            self.state.set_connection_status("Disconnected")
            self.logger.warning("Manual reconnect failed: %s", exc)

    def reconnect_async(self) -> None:
        """Run reconnect without blocking the tray UI."""

        threading.Thread(target=self.reconnect, name="manual-reconnect", daemon=True).start()

    def _start_sender(self) -> threading.Thread:
        return start_sender_thread(
            self.telemetry_queue,
            self.client,
            self.logger,
            self.stop_event,
        )

    def _start_heartbeat(self) -> threading.Thread:
        thread = threading.Thread(
            target=run_heartbeat_loop,
            args=(
                self.client,
                self.config.heartbeat_interval,
                self.logger,
                self.stop_event,
                self.state,
            ),
            name="heartbeat",
            daemon=True,
        )
        thread.start()
        return thread

    def _start_command_poller(self) -> threading.Thread:
        return start_command_polling_thread(
            self.client,
            self.command_executor,
            self.logger,
            self.stop_event,
        )

    def _start_process_collector(self) -> threading.Thread:
        return start_process_collector(
            self.config.endpoint_id,
            self.telemetry_queue,
            self.logger,
            self.stop_event,
        )

    def _start_file_collector(self) -> threading.Thread:
        return start_file_collector(
            self.config.endpoint_id,
            self.telemetry_queue,
            self.logger,
            self.stop_event,
        )

    def _start_windows_event_collector(self) -> threading.Thread:
        return start_windows_event_collector(
            self.config.endpoint_id,
            self.telemetry_queue,
            self.logger,
            self.stop_event,
        )

    def _start_health_monitor(self) -> threading.Thread:
        thread = threading.Thread(
            target=self._health_monitor_loop,
            name="health-monitor",
            daemon=True,
        )
        thread.start()
        return thread

    def _health_monitor_loop(self) -> None:
        """Restart failed worker threads with a bounded restart count."""

        while not self.stop_event.wait(60):
            for name, starter in self.starters.items():
                thread = self.threads.get(name)
                if thread is not None and thread.is_alive():
                    continue

                restart_count = self.restart_counts.get(name, 0)
                if restart_count >= self.max_restarts:
                    self.logger.warning(
                        "Worker %s is down and exceeded restart limit.",
                        name,
                    )
                    continue

                self.restart_counts[name] = restart_count + 1
                self.logger.warning(
                    "Worker %s stopped unexpectedly. Restarting (%s/%s).",
                    name,
                    self.restart_counts[name],
                    self.max_restarts,
                )
                self.threads[name] = starter()
