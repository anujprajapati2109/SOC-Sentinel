from models import Telemetry

from .base_rule import BaseRule, DetectionResult


class SuspiciousProcessRule(BaseRule):
    """Detect known suspicious process names."""

    rule_id = "RULE-SUSPICIOUS-PROCESS"

    def evaluate(self, event: Telemetry) -> DetectionResult | None:
        if event.event_type != "process_started":
            return None

        process_name = str(event.raw_data.get("process_name", "")).lower()
        if process_name != "mimikatz.exe":
            return None

        return self.result(event, "Known credential dumping tool process observed.")
