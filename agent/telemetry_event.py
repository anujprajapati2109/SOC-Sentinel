from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class TelemetryEvent:
    """Shared telemetry event object returned by every collector."""

    endpoint_id: str
    collector: str
    event_type: str
    severity: str
    timestamp: datetime
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the telemetry event for the server API."""

        return {
            "endpoint_id": self.endpoint_id,
            "collector": self.collector,
            "event_type": self.event_type,
            "severity": self.severity,
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat(),
            "data": self.data,
        }


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)
