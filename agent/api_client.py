from typing import Any

import requests

from config import AgentConfig
from device_fingerprint import generate_device_fingerprint
from system_info import collect_system_info
from telemetry_event import TelemetryEvent


class APIClient:
    """Reusable HTTP client for SOC Sentinel server communication."""

    def __init__(self, config: AgentConfig, timeout: int = 10) -> None:
        self.config = config
        self.timeout = timeout

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Register the endpoint with the SOC Sentinel server."""

        return self.post("/api/v1/endpoints/register", payload)

    def heartbeat(self) -> dict[str, Any]:
        """Send a heartbeat using the stored endpoint credentials."""

        payload = collect_system_info()
        payload.update({
            "endpoint_id": self.config.endpoint_id,
            "api_key": self.config.api_key,
            "device_fingerprint": generate_device_fingerprint(),
        })
        return self.post("/api/v1/endpoints/heartbeat", payload)

    def send_telemetry(self, events: list[TelemetryEvent]) -> dict[str, Any]:
        """Send a batch of telemetry events to the SOC Sentinel server."""

        payload = {"events": [event.to_dict() for event in events]}
        return self.post("/api/v1/telemetry", payload)

    def get_pending_commands(self) -> list[dict[str, Any]]:
        """Poll the dedicated command API for queued endpoint commands."""

        path = f"/api/v1/commands/pending/{self.config.endpoint_id}"
        response = self.get(
            path,
            headers={
                "X-API-Key": self.config.api_key,
                "X-Device-Fingerprint": generate_device_fingerprint(),
            },
        )
        return list(response.get("commands", []))

    def send_command_result(
        self,
        command_id: str,
        status: str,
        response: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        """Send endpoint command execution result to the server."""

        payload = {
            "endpoint_id": self.config.endpoint_id,
            "api_key": self.config.api_key,
            "device_fingerprint": generate_device_fingerprint(),
            "command_id": command_id,
            "status": status,
            "response": response or {},
            "error_message": error_message,
        }
        return self.post("/api/v1/commands/result", payload)

    def get(
        self,
        path: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a JSON GET request and return the decoded response."""

        url = f"{self.config.server_url}{path}"
        response = requests.get(url, headers=headers or {}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON POST request and return the decoded response."""

        url = f"{self.config.server_url}{path}"
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
