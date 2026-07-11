import platform
import shutil
import socket

from agent_state import AgentState
from config import AGENT_VERSION
from telemetry_queue import TelemetryQueue


try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency fallback.
    psutil = None


def execute(
    telemetry_queue: TelemetryQueue,
    state: AgentState | None = None,
) -> dict:
    """Collect safe local diagnostic information."""

    disk = shutil.disk_usage("/")
    snapshot = state.snapshot() if state is not None else None
    return {
        "cpu_usage": _cpu_usage(),
        "memory_usage": _memory_usage(),
        "disk_usage": round((disk.used / disk.total) * 100, 1),
        "hostname": socket.gethostname(),
        "os_version": platform.platform(),
        "agent_version": AGENT_VERSION,
        "collector_status": "running",
        "telemetry_queue_length": telemetry_queue.size(),
        "heartbeat_status": snapshot.connection_status if snapshot else "Unknown",
        "last_heartbeat": snapshot.last_heartbeat if snapshot else "Unknown",
    }


def _cpu_usage() -> str:
    if psutil is None:
        return "N/A"
    return f"{round(float(psutil.cpu_percent(interval=0.1)), 1)}%"


def _memory_usage() -> str:
    if psutil is None:
        return "N/A"
    return f"{round(float(psutil.virtual_memory().percent), 1)}%"
