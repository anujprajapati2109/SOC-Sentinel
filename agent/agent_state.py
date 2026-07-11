from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from config import AgentConfig


@dataclass
class AgentSnapshot:
    """Read-only snapshot of current agent status."""

    endpoint_id: str
    server_url: str
    connection_status: str
    last_heartbeat: str


class AgentState:
    """Thread-safe runtime state shown in the tray UI."""

    def __init__(self, config: AgentConfig) -> None:
        self._lock = Lock()
        self._config = config
        self._connection_status = "Starting"
        self._last_heartbeat: datetime | None = None

    def set_connection_status(self, status: str) -> None:
        """Update connection status."""

        with self._lock:
            self._connection_status = status

    def record_heartbeat(self) -> None:
        """Record a successful heartbeat timestamp."""

        with self._lock:
            self._connection_status = "Connected"
            self._last_heartbeat = datetime.now(timezone.utc)

    def snapshot(self) -> AgentSnapshot:
        """Return current state without exposing mutable internals."""

        with self._lock:
            last_heartbeat = (
                self._last_heartbeat.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                if self._last_heartbeat
                else "Never"
            )
            return AgentSnapshot(
                endpoint_id=self._config.endpoint_id or "Not registered",
                server_url=self._config.server_url,
                connection_status=self._connection_status,
                last_heartbeat=last_heartbeat,
            )
