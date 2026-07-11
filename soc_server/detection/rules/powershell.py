from models import Telemetry

from .base_rule import BaseRule, DetectionResult


class PowerShellRule(BaseRule):
    """Detect PowerShell process starts."""

    rule_id = "RULE-POWERSHELL"

    def evaluate(self, event: Telemetry) -> DetectionResult | None:
        if event.event_type != "process_started":
            return None

        process_name = str(event.raw_data.get("process_name", "")).lower()
        if process_name != "powershell.exe":
            return None

        return self.result(event, "PowerShell process execution observed.")
