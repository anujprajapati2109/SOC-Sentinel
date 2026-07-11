from correlation.correlation_result import CorrelationResult
from correlation.rules.base_rule import BaseCorrelationRule
from models import Alert


class BruteForceFollowedByPowerShellRule(BaseCorrelationRule):
    """Placeholder rule for future brute force to PowerShell correlation."""

    rule_id = "CRULE-0001"
    name = "Brute Force Followed by PowerShell"
    description = "Correlates repeated failed logins followed by PowerShell activity."
    version = "1.0"
    enabled = True
    severity = "critical"
    time_window = 120
    mitre_tactic = "Credential Access"
    mitre_technique = "T1110 Brute Force"

    def evaluate(self, alerts: list[Alert]) -> list[CorrelationResult]:
        """Match failed-login activity followed by PowerShell execution."""

        failed_login_alerts = self.alerts_by_rule(alerts, "RULE-FAILED-LOGIN")
        powershell_alerts = self.alerts_by_rule(alerts, "RULE-POWERSHELL")
        matches: list[CorrelationResult] = []

        for powershell_alert in powershell_alerts:
            preceding_failures = [
                alert
                for alert in failed_login_alerts
                if self.within_window(alert, powershell_alert, self.time_window)
            ]
            if not preceding_failures:
                continue

            matched_alerts = [*preceding_failures[-5:], powershell_alert]
            matches.append(
                CorrelationResult(
                    incident_title=self.name,
                    severity=self.severity,
                    summary=(
                        "Failed login activity was followed by PowerShell "
                        "execution on the same endpoint."
                    ),
                    confidence=85,
                    risk_score=90,
                    timeline=self.timeline(matched_alerts),
                    evidence=self.evidence_summary(matched_alerts),
                    mitre_tactic=self.mitre_tactic,
                    mitre_technique=self.mitre_technique,
                    matched_alerts=matched_alerts,
                )
            )

        return matches
