from correlation.correlation_result import CorrelationResult
from correlation.rules.base_rule import BaseCorrelationRule
from models import Alert


class ReconActivityRule(BaseCorrelationRule):
    """Placeholder rule for future reconnaissance correlation."""

    rule_id = "CRULE-0005"
    name = "Recon Activity"
    description = "Correlates discovery and reconnaissance alerts over time."
    version = "1.0"
    enabled = True
    severity = "medium"
    time_window = 300
    mitre_tactic = "Discovery"
    mitre_technique = "T1087 Account Discovery"

    def evaluate(self, alerts: list[Alert]) -> list[CorrelationResult]:
        """Match process spike activity with failed login activity."""

        process_alerts = self.alerts_by_rule(alerts, "RULE-PROCESS-SPIKE")
        failed_login_alerts = self.alerts_by_rule(alerts, "RULE-FAILED-LOGIN")
        matches: list[CorrelationResult] = []

        for process_alert in process_alerts:
            related_failures = [
                alert
                for alert in failed_login_alerts
                if abs(
                    (
                        self.alert_time(process_alert)
                        - self.alert_time(alert)
                    ).total_seconds()
                )
                <= self.time_window
            ]
            if not related_failures:
                continue

            matched_alerts = [*related_failures, process_alert]
            matches.append(
                CorrelationResult(
                    incident_title=self.name,
                    severity=self.severity,
                    summary=(
                        "Process spike activity appeared alongside failed "
                        "login activity on the same endpoint."
                    ),
                    confidence=70,
                    risk_score=65,
                    timeline=self.timeline(matched_alerts),
                    evidence=self.evidence_summary(matched_alerts),
                    mitre_tactic=self.mitre_tactic,
                    mitre_technique=self.mitre_technique,
                    matched_alerts=matched_alerts,
                )
            )

        return matches
