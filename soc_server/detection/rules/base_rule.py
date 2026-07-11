from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from models import DetectionRule, Telemetry


@dataclass(frozen=True)
class DetectionResult:
    """Rule match result passed to AlertService."""

    endpoint_id: str
    rule_id: str
    severity: str
    title: str
    description: str
    timestamp: Any
    telemetry: Telemetry


class BaseRule:
    """Base class for all detection rules."""

    rule_id = ""

    def __init__(self, config: DetectionRule) -> None:
        self.config = config

    def evaluate(self, event: Telemetry) -> DetectionResult | None:
        """Return a DetectionResult when the event triggers the rule."""

        raise NotImplementedError

    def window_start(self, event: Telemetry) -> Any:
        """Return the start timestamp for this rule's time window."""

        return event.timestamp - timedelta(seconds=self.config.time_window)

    def result(self, event: Telemetry, description: str | None = None) -> DetectionResult:
        """Build a standard detection result from this rule."""

        return DetectionResult(
            endpoint_id=event.endpoint_id,
            rule_id=self.config.rule_id,
            severity=self.config.severity,
            title=self.config.name,
            description=description or self.config.description,
            timestamp=event.timestamp,
            telemetry=event,
        )
