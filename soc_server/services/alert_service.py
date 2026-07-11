import logging
from datetime import timedelta

from correlation.registry import get_correlation_engine
from detection.rules.base_rule import DetectionResult
from models import Alert, DetectionRule, Telemetry, db, utc_now


logger = logging.getLogger(__name__)


class AlertService:
    """Creates alerts and suppresses duplicates."""

    def create_alert(self, result: DetectionResult) -> Alert | None:
        """Create an alert unless an equivalent open alert already exists."""

        if self._is_duplicate(result):
            return None

        alert = Alert(
            alert_id=self._generate_alert_id(),
            endpoint_id=result.endpoint_id,
            rule_id=result.rule_id,
            severity=result.severity,
            title=result.title,
            description=result.description,
            timestamp=result.timestamp or utc_now(),
            status="Open",
        )
        db.session.add(alert)
        db.session.commit()
        self._send_to_correlation_engine(alert)
        return alert

    def _is_duplicate(self, result: DetectionResult) -> bool:
        """Suppress duplicate open alerts for the same endpoint and rule."""

        return (
            Alert.query.filter_by(
                endpoint_id=result.endpoint_id,
                rule_id=result.rule_id,
                status="Open",
            ).first()
            is not None
        )

    def _generate_alert_id(self) -> str:
        """Generate a human-readable alert identifier."""

        last_alert = Alert.query.order_by(Alert.id.desc()).first()
        next_number = 1 if last_alert is None else last_alert.id + 1
        return f"ALRT-{next_number:06d}"

    def _send_to_correlation_engine(self, alert: Alert) -> None:
        """Send a committed alert to the correlation engine."""

        try:
            get_correlation_engine().handle_alert(alert)
        except Exception:
            logger.exception(
                "Correlation engine failed while handling alert %s",
                alert.alert_id,
            )


def list_alerts() -> list[Alert]:
    """Return newest alerts first."""

    return Alert.query.order_by(Alert.timestamp.desc()).all()


def count_critical_alerts() -> int:
    """Return open critical alert count."""

    return Alert.query.filter_by(severity="critical", status="Open").count()


def get_alert(alert_id: str) -> Alert | None:
    """Return one alert by public alert ID."""

    return Alert.query.filter_by(alert_id=alert_id).first()


def get_alert_rule(alert: Alert) -> DetectionRule | None:
    """Return the detection rule config for an alert."""

    return DetectionRule.query.filter_by(rule_id=alert.rule_id).first()


def get_related_telemetry(alert: Alert, limit: int = 25) -> list[Telemetry]:
    """Return telemetry likely responsible for the alert."""

    rule = get_alert_rule(alert)
    if rule is None:
        return []

    start = alert.timestamp - timedelta(seconds=max(rule.time_window, 5))
    return (
        Telemetry.query.filter(
            Telemetry.endpoint_id == alert.endpoint_id,
            Telemetry.timestamp >= start,
            Telemetry.timestamp <= alert.timestamp + timedelta(seconds=5),
        )
        .order_by(Telemetry.timestamp.desc())
        .limit(limit)
        .all()
    )
