from models import Telemetry

from .base_rule import BaseRule, DetectionResult


class ProcessSpikeRule(BaseRule):
    """Detect a burst of process starts on one endpoint."""

    rule_id = "RULE-PROCESS-SPIKE"

    def evaluate(self, event: Telemetry) -> DetectionResult | None:
        if event.event_type != "process_started":
            return None

        count = Telemetry.query.filter(
            Telemetry.endpoint_id == event.endpoint_id,
            Telemetry.event_type == "process_started",
            Telemetry.timestamp >= self.window_start(event),
            Telemetry.timestamp <= event.timestamp,
        ).count()

        if count < self.config.threshold:
            return None

        return self.result(
            event,
            f"{count} process start events observed within "
            f"{self.config.time_window} seconds.",
        )
