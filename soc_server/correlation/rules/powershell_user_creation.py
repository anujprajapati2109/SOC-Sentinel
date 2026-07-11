from correlation.correlation_result import CorrelationResult
from correlation.rules.base_rule import BaseCorrelationRule
from models import Alert


class PowerShellFollowedByUserCreationRule(BaseCorrelationRule):
    """Placeholder rule for future PowerShell to user creation correlation."""

    rule_id = "CRULE-0002"
    name = "PowerShell Followed by User Creation"
    description = "Correlates PowerShell execution followed by local user creation."
    version = "1.0"
    enabled = True
    severity = "critical"
    time_window = 300
    mitre_tactic = "Persistence"
    mitre_technique = "T1136 Create Account"

    def evaluate(self, alerts: list[Alert]) -> list[CorrelationResult]:
        """Match PowerShell execution followed by user creation."""

        powershell_alerts = self.alerts_by_rule(alerts, "RULE-POWERSHELL")
        user_creation_alerts = [
            alert
            for alert in alerts
            if "user" in alert.title.lower()
            and "created" in alert.title.lower()
        ]
        matches: list[CorrelationResult] = []

        for user_alert in user_creation_alerts:
            for powershell_alert in powershell_alerts:
                if not self.within_window(powershell_alert, user_alert, self.time_window):
                    continue

                matched_alerts = [powershell_alert, user_alert]
                matches.append(
                    CorrelationResult(
                        incident_title=self.name,
                        severity=self.severity,
                        summary=(
                            "PowerShell execution was followed by user creation "
                            "on the same endpoint."
                        ),
                        confidence=88,
                        risk_score=92,
                        timeline=self.timeline(matched_alerts),
                        evidence=self.evidence_summary(matched_alerts),
                        mitre_tactic=self.mitre_tactic,
                        mitre_technique=self.mitre_technique,
                        matched_alerts=matched_alerts,
                    )
                )

        return matches
