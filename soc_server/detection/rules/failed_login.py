from models import Telemetry

from .base_rule import BaseRule, DetectionResult


class FailedLoginRule(BaseRule):
    """Detect repeated failed logins from one endpoint."""

    rule_id = "RULE-FAILED-LOGIN"

    def evaluate(self, event: Telemetry) -> DetectionResult | None:
        if event.event_type != "login_failure":
            return None

        count = Telemetry.query.filter(
            Telemetry.endpoint_id == event.endpoint_id,
            Telemetry.event_type == "login_failure",
            Telemetry.timestamp >= self.window_start(event),
            Telemetry.timestamp <= event.timestamp,
        ).count()

        if count < self.config.threshold:
            return None

        return self.result(
            event,
            f"{count} failed login events observed within "
            f"{self.config.time_window} seconds.",
        )
