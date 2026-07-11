import logging
from typing import Any

from agent_state import AgentState
from api_client import APIClient
from commands import collect_diagnostics, download_logs, heartbeat_now, restart_agent
from commands import sync_telemetry
from telemetry_queue import TelemetryQueue


class CommandExecutor:
    """Dispatch safe endpoint response commands to reusable handlers."""

    def __init__(
        self,
        client: APIClient,
        telemetry_queue: TelemetryQueue,
        logger: logging.Logger,
        state: AgentState | None = None,
    ) -> None:
        self.client = client
        self.telemetry_queue = telemetry_queue
        self.logger = logger
        self.state = state

    def execute(self, command: dict[str, Any]) -> tuple[str, dict[str, Any], str | None]:
        """Execute one command and return status, response, and optional error."""

        command_type = str(command.get("command_type", ""))
        try:
            if command_type == "heartbeat_now":
                return "COMPLETED", heartbeat_now.execute(self.client, self.state), None
            if command_type == "sync_telemetry":
                return "COMPLETED", sync_telemetry.execute(self.telemetry_queue), None
            if command_type == "collect_diagnostics":
                return (
                    "COMPLETED",
                    collect_diagnostics.execute(self.telemetry_queue, self.state),
                    None,
                )
            if command_type == "restart_agent":
                return "COMPLETED", restart_agent.execute(), None
            if command_type == "download_logs":
                return "COMPLETED", download_logs.execute(), None
            return "FAILED", {}, f"Unsupported command type: {command_type}"
        except Exception as exc:  # pragma: no cover - defensive endpoint boundary.
            self.logger.exception("Command execution failed: %s", command_type)
            return "FAILED", {}, str(exc)
