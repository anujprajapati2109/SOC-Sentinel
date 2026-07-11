from correlation.correlation_result import CorrelationResult
from correlation.rules.base_rule import BaseCorrelationRule
from models import Alert


class PossibleRansomwareRule(BaseCorrelationRule):
    """Placeholder rule for future ransomware chain correlation."""

    rule_id = "CRULE-0003"
    name = "Possible Ransomware"
    description = "Correlates destructive file activity and related execution signals."
    version = "1.0"
    enabled = True
    severity = "critical"
    time_window = 60
    mitre_tactic = "Impact"
    mitre_technique = "T1486 Data Encrypted for Impact"

    def evaluate(self, alerts: list[Alert]) -> list[CorrelationResult]:
        """Match destructive file activity with process spike behavior."""

        deletion_alerts = self.alerts_by_rule(alerts, "RULE-RANSOMWARE")
        process_spike_alerts = self.alerts_by_rule(alerts, "RULE-PROCESS-SPIKE")
        matches: list[CorrelationResult] = []

        for process_alert in process_spike_alerts:
            related_deletions = [
                alert
                for alert in deletion_alerts
                if abs(
                    (
                        self.alert_time(process_alert)
                        - self.alert_time(alert)
                    ).total_seconds()
                )
                <= self.time_window
            ]
            if not related_deletions:
                continue

            matched_alerts = [*related_deletions, process_alert]
            matches.append(
                CorrelationResult(
                    incident_title=self.name,
                    severity=self.severity,
                    summary=(
                        "Ransomware-like file deletion activity occurred near "
                        "a process execution spike."
                    ),
                    confidence=90,
                    risk_score=96,
                    timeline=self.timeline(matched_alerts),
                    evidence=self.evidence_summary(matched_alerts),
                    mitre_tactic=self.mitre_tactic,
                    mitre_technique=self.mitre_technique,
                    matched_alerts=matched_alerts,
                )
            )

        return matches
