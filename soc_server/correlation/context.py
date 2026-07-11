from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import RLock

from models import Alert


class CorrelationContext:
    """Thread-safe recent alert history grouped by endpoint."""

    def __init__(self, retention_seconds: int = 900) -> None:
        self.retention = timedelta(seconds=retention_seconds)
        self._alerts: dict[str, deque[Alert]] = defaultdict(deque)
        self._lock = RLock()

    def add_alert(self, alert: Alert) -> list[Alert]:
        """Add an alert and return current endpoint history."""

        with self._lock:
            endpoint_alerts = self._alerts[alert.endpoint_id]
            endpoint_alerts.append(alert)
            self._expire_endpoint(alert.endpoint_id, self._now())
            return list(endpoint_alerts)

    def get_alerts(self, endpoint_id: str) -> list[Alert]:
        """Return recent alert history for one endpoint."""

        with self._lock:
            self._expire_endpoint(endpoint_id, self._now())
            return list(self._alerts.get(endpoint_id, ()))

    def expire_old_alerts(self) -> None:
        """Expire stale alerts for every endpoint."""

        with self._lock:
            now = self._now()
            for endpoint_id in list(self._alerts):
                self._expire_endpoint(endpoint_id, now)
                if not self._alerts[endpoint_id]:
                    del self._alerts[endpoint_id]

    def _expire_endpoint(self, endpoint_id: str, now: datetime) -> None:
        """Remove alerts outside the retention window for one endpoint."""

        cutoff = now - self.retention
        endpoint_alerts = self._alerts.get(endpoint_id)
        if endpoint_alerts is None:
            return

        while endpoint_alerts and self._alert_time(endpoint_alerts[0]) < cutoff:
            endpoint_alerts.popleft()

    def _alert_time(self, alert: Alert) -> datetime:
        """Return alert timestamp as timezone-aware UTC."""

        timestamp = alert.timestamp
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)

        return timestamp.astimezone(timezone.utc)

    def _now(self) -> datetime:
        """Return current UTC timestamp."""

        return datetime.now(timezone.utc)
