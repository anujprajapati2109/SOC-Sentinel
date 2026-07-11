import hashlib
import json
import logging
from datetime import timedelta
from typing import Any

from correlation.correlation_result import CorrelationResult
from models import Alert, CorrelatedIncident, CorrelationRule, db, utc_now


logger = logging.getLogger(__name__)

INCIDENT_STATUS_OPEN = "OPEN"
INCIDENT_STATUS_INVESTIGATING = "INVESTIGATING"
INCIDENT_STATUS_RESOLVED = "RESOLVED"
INCIDENT_STATUS_FALSE_POSITIVE = "FALSE_POSITIVE"

ACTIVE_INCIDENT_STATUSES = {
    INCIDENT_STATUS_OPEN,
    INCIDENT_STATUS_INVESTIGATING,
}
DEFAULT_DUPLICATE_COOLDOWN_SECONDS = 300


DEFAULT_CORRELATION_RULES = [
    {
        "rule_id": "CRULE-0001",
        "name": "Brute Force Followed by PowerShell",
        "description": "Placeholder for correlating repeated failed logins followed by PowerShell execution.",
        "enabled": True,
        "severity": "critical",
        "time_window": 120,
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110 Brute Force",
        "version": "1.0",
    },
    {
        "rule_id": "CRULE-0002",
        "name": "PowerShell Followed by User Creation",
        "description": "Placeholder for correlating PowerShell execution followed by local user creation.",
        "enabled": True,
        "severity": "critical",
        "time_window": 300,
        "mitre_tactic": "Persistence",
        "mitre_technique": "T1136 Create Account",
        "version": "1.0",
    },
    {
        "rule_id": "CRULE-0003",
        "name": "Possible Ransomware",
        "description": "Placeholder for correlating destructive file activity and related execution signals.",
        "enabled": True,
        "severity": "critical",
        "time_window": 60,
        "mitre_tactic": "Impact",
        "mitre_technique": "T1486 Data Encrypted for Impact",
        "version": "1.0",
    },
    {
        "rule_id": "CRULE-0004",
        "name": "Credential Theft Chain",
        "description": "Placeholder for correlating credential access alerts into a single incident.",
        "enabled": True,
        "severity": "critical",
        "time_window": 300,
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1003 OS Credential Dumping",
        "version": "1.0",
    },
    {
        "rule_id": "CRULE-0005",
        "name": "Recon Activity",
        "description": "Placeholder for correlating discovery and reconnaissance alerts over time.",
        "enabled": True,
        "severity": "medium",
        "time_window": 300,
        "mitre_tactic": "Discovery",
        "mitre_technique": "T1087 Account Discovery",
        "version": "1.0",
    },
]


class CorrelationService:
    """Creates and de-duplicates correlated incidents."""

    def __init__(self, duplicate_cooldown_seconds: int = 300) -> None:
        self.duplicate_cooldown = timedelta(seconds=duplicate_cooldown_seconds)

    def create_incident(
        self,
        correlation_rule_id: str,
        result: CorrelationResult,
    ) -> CorrelatedIncident | None:
        """Persist a correlation result unless an active duplicate exists."""

        endpoint_id = self._resolve_endpoint_id(result)
        evidence_hash = self._evidence_hash(result)
        if self._is_duplicate(correlation_rule_id, endpoint_id, evidence_hash):
            logger.info(
                "Duplicate suppressed | endpoint=%s correlation_rule=%s",
                endpoint_id,
                correlation_rule_id,
            )
            return None

        incident = CorrelatedIncident(
            incident_id=self._generate_incident_id(),
            endpoint_id=endpoint_id,
            correlation_rule_id=correlation_rule_id,
            severity=result.severity,
            status=INCIDENT_STATUS_OPEN,
            title=result.incident_title,
            summary=result.summary,
            confidence=result.confidence,
            risk_score=result.risk_score,
            mitre_tactic=result.mitre_tactic,
            mitre_technique=result.mitre_technique,
            timeline=result.timeline,
            matched_alert_ids=[
                alert.alert_id for alert in result.matched_alerts
            ],
            evidence=self._serialize_evidence(result),
            evidence_hash=evidence_hash,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.session.add(incident)
        db.session.commit()
        logger.info(
            "Incident created | incident=%s endpoint=%s correlation_rule=%s",
            incident.incident_id,
            incident.endpoint_id,
            incident.correlation_rule_id,
        )
        return incident

    def _is_duplicate(
        self,
        correlation_rule_id: str,
        endpoint_id: str,
        evidence_hash: str,
    ) -> bool:
        """Return whether an active incident already exists for this rule."""

        cutoff = utc_now() - self.duplicate_cooldown
        return (
            CorrelatedIncident.query.filter(
                CorrelatedIncident.correlation_rule_id == correlation_rule_id,
                CorrelatedIncident.endpoint_id == endpoint_id,
                CorrelatedIncident.evidence_hash == evidence_hash,
                CorrelatedIncident.created_at >= cutoff,
                CorrelatedIncident.status.in_(ACTIVE_INCIDENT_STATUSES),
            ).first()
            is not None
        )

    def _generate_incident_id(self) -> str:
        """Generate a human-readable correlated incident ID."""

        last_incident = CorrelatedIncident.query.order_by(
            CorrelatedIncident.id.desc()
        ).first()
        next_number = 1 if last_incident is None else last_incident.id + 1
        return f"COR-{next_number:06d}"

    def _resolve_endpoint_id(self, result: CorrelationResult) -> str:
        """Derive the incident endpoint from matched alerts."""

        endpoint_ids = {
            alert.endpoint_id
            for alert in result.matched_alerts
            if getattr(alert, "endpoint_id", None)
        }
        if len(endpoint_ids) == 1:
            return endpoint_ids.pop()

        return "MULTIPLE" if endpoint_ids else "UNKNOWN"

    def _serialize_evidence(self, result: CorrelationResult) -> list[dict[str, Any]]:
        """Store result evidence and matched alert IDs as JSON."""

        evidence = list(result.evidence)
        if result.matched_alerts:
            evidence.append(
                {
                    "matched_alerts": [
                        {
                            "alert_id": alert.alert_id,
                            "endpoint_id": alert.endpoint_id,
                            "rule_id": alert.rule_id,
                            "severity": alert.severity,
                            "timestamp": alert.timestamp.isoformat()
                            if alert.timestamp
                            else None,
                        }
                        for alert in result.matched_alerts
                    ]
                }
            )

        return evidence

    def _evidence_hash(self, result: CorrelationResult) -> str:
        """Return stable uniqueness hash for matched evidence."""

        payload = {
            "matched_alert_ids": sorted(
                alert.alert_id for alert in result.matched_alerts
            ),
            "timeline": result.timeline,
            "evidence": result.evidence,
        }
        encoded = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def seed_correlation_rules() -> None:
    """Create or update placeholder correlation rule metadata."""

    for rule_data in DEFAULT_CORRELATION_RULES:
        rule = CorrelationRule.query.filter_by(rule_id=rule_data["rule_id"]).first()
        if rule is None:
            db.session.add(CorrelationRule(**rule_data))
            continue

        for key, value in rule_data.items():
            setattr(rule, key, value)

    db.session.commit()


def list_correlation_rules() -> list[CorrelationRule]:
    """Return correlation rules ordered by public rule ID."""

    return CorrelationRule.query.order_by(CorrelationRule.rule_id.asc()).all()


def list_correlated_incidents() -> list[CorrelatedIncident]:
    """Return newest correlated incidents first."""

    return CorrelatedIncident.query.order_by(
        CorrelatedIncident.created_at.desc()
    ).all()


def get_correlated_incident(incident_id: str) -> CorrelatedIncident | None:
    """Return one correlated incident by public incident ID."""

    return CorrelatedIncident.query.filter_by(incident_id=incident_id).first()


def get_correlation_rule(rule_id: str) -> CorrelationRule | None:
    """Return one correlation rule by public rule ID."""

    return CorrelationRule.query.filter_by(rule_id=rule_id).first()


def get_matched_alerts(incident: CorrelatedIncident) -> list[Alert]:
    """Return matched alerts in incident order."""

    alert_ids = incident.matched_alert_ids or []
    if not alert_ids:
        return []

    alerts = Alert.query.filter(Alert.alert_id.in_(alert_ids)).all()
    alerts_by_id = {alert.alert_id: alert for alert in alerts}
    return [alerts_by_id[alert_id] for alert_id in alert_ids if alert_id in alerts_by_id]
