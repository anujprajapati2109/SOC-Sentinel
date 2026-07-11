from correlation.correlation_result import CorrelationResult
from correlation.rules.base_rule import BaseCorrelationRule
from models import Alert


class CredentialTheftChainRule(BaseCorrelationRule):
    """Placeholder rule for future credential theft chain correlation."""

    rule_id = "CRULE-0004"
    name = "Credential Theft Chain"
    description = "Correlates credential access alerts into one investigation unit."
    version = "1.0"
    enabled = True
    severity = "critical"
    time_window = 300
    mitre_tactic = "Credential Access"
    mitre_technique = "T1003 OS Credential Dumping"

    def evaluate(self, alerts: list[Alert]) -> list[CorrelationResult]:
        """Match PowerShell followed by Mimikatz execution."""

        powershell_alerts = self.alerts_by_rule(alerts, "RULE-POWERSHELL")
        mimikatz_alerts = self.alerts_by_rule(alerts, "RULE-SUSPICIOUS-PROCESS")
        matches: list[CorrelationResult] = []

        for mimikatz_alert in mimikatz_alerts:
            for powershell_alert in powershell_alerts:
                if not self.within_window(
                    powershell_alert,
                    mimikatz_alert,
                    self.time_window,
                ):
                    continue

                matched_alerts = [powershell_alert, mimikatz_alert]
                matches.append(
                    CorrelationResult(
                        incident_title=self.name,
                        severity=self.severity,
                        summary=(
                            "PowerShell execution was followed by a known "
                            "credential dumping process."
                        ),
                        confidence=92,
                        risk_score=98,
                        timeline=self.timeline(matched_alerts),
                        evidence=self.evidence_summary(matched_alerts),
                        mitre_tactic=self.mitre_tactic,
                        mitre_technique=self.mitre_technique,
                        matched_alerts=matched_alerts,
                    )
                )

        return matches
