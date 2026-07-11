from models import Telemetry

from .base_rule import BaseRule, DetectionResult


class RansomwareRule(BaseRule):
    """Detect rapid file deletion bursts."""

    rule_id = "RULE-RANSOMWARE"

    def evaluate(self, event: Telemetry) -> DetectionResult | None:
        if event.event_type != "file_deleted":
            return None

        count = Telemetry.query.filter(
            Telemetry.endpoint_id == event.endpoint_id,
            Telemetry.event_type == "file_deleted",
            Telemetry.timestamp >= self.window_start(event),
            Telemetry.timestamp <= event.timestamp,
        ).count()

        if count < self.config.threshold:
            return None

        return self.result(
            event,
            f"{count} file deletion events observed within "
            f"{self.config.time_window} seconds.",
        )
