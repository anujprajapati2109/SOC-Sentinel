from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Iterable

from correlation.correlation_result import CorrelationResult
from models import Alert


class BaseCorrelationRule(ABC):
    """Base contract for all alert correlation rules."""

    rule_id: str
    name: str
    description: str
    version: str
    enabled: bool = True
    severity: str
    time_window: int
    mitre_tactic: str | None = None
    mitre_technique: str | None = None

    @abstractmethod
    def evaluate(self, alerts: list[Alert]) -> list[CorrelationResult]:
        """Evaluate alerts and return correlation results without persistence."""

    def alerts_by_rule(self, alerts: Iterable[Alert], rule_id: str) -> list[Alert]:
        """Return alerts matching a detection rule ID."""

        return [alert for alert in alerts if alert.rule_id == rule_id]

    def within_window(
        self,
        first_alert: Alert,
        second_alert: Alert,
        seconds: int,
    ) -> bool:
        """Return whether second alert follows first within a time window."""

        delta = self.alert_time(second_alert) - self.alert_time(first_alert)
        return timedelta(0) <= delta <= timedelta(seconds=seconds)

    def alert_time(self, alert: Alert) -> datetime:
        """Return alert timestamp as timezone-aware UTC."""

        if alert.timestamp.tzinfo is None:
            return alert.timestamp.replace(tzinfo=timezone.utc)

        return alert.timestamp.astimezone(timezone.utc)

    def timeline(self, alerts: Iterable[Alert]) -> list[dict]:
        """Build a sorted incident timeline from matched alerts."""

        return [
            {
                "alert_id": alert.alert_id,
                "rule_id": alert.rule_id,
                "title": alert.title,
                "severity": alert.severity,
                "timestamp": self.alert_time(alert).isoformat(),
            }
            for alert in sorted(alerts, key=self.alert_time)
        ]

    def evidence_summary(self, alerts: Iterable[Alert]) -> list[dict]:
        """Build compact evidence entries for matched alerts."""

        return [
            {
                "alert_id": alert.alert_id,
                "rule_id": alert.rule_id,
                "description": alert.description,
                "timestamp": self.alert_time(alert).isoformat(),
            }
            for alert in sorted(alerts, key=self.alert_time)
        ]
