from typing import Any

from models import (
    Alert,
    CorrelatedIncident,
    CorrelationRule,
    DetectionRule,
    Endpoint,
    Telemetry,
)


def global_search(query: str, limit: int = 6) -> dict[str, list[dict[str, Any]]]:
    """Search major SOC objects and return grouped navigation results."""

    term = query.strip()
    if not term:
        return {
            "endpoints": [],
            "telemetry": [],
            "alerts": [],
            "incidents": [],
            "rules": [],
        }

    like = f"%{term}%"
    return {
        "endpoints": [
            {
                "label": f"{endpoint.endpoint_id} - {endpoint.hostname}",
                "meta": endpoint.ip_address or endpoint.status,
                "url": f"/endpoints/{endpoint.endpoint_id}",
            }
            for endpoint in Endpoint.query.filter(
                (Endpoint.endpoint_id.ilike(like))
                | (Endpoint.hostname.ilike(like))
                | (Endpoint.ip_address.ilike(like))
            ).limit(limit)
        ],
        "telemetry": [
            {
                "label": f"Telemetry #{event.id}",
                "meta": f"{event.collector} / {event.event_type}",
                "url": f"/telemetry?telemetry_id={event.id}",
            }
            for event in _search_telemetry(term, limit)
        ],
        "alerts": [
            {
                "label": alert.alert_id,
                "meta": f"{alert.severity} / {alert.rule_id}",
                "url": f"/alerts/{alert.alert_id}",
            }
            for alert in Alert.query.filter(
                (Alert.alert_id.ilike(like))
                | (Alert.rule_id.ilike(like))
                | (Alert.title.ilike(like))
                | (Alert.endpoint_id.ilike(like))
            ).limit(limit)
        ],
        "incidents": [
            {
                "label": incident.incident_id,
                "meta": f"{incident.severity} / {incident.status}",
                "url": f"/incidents/{incident.incident_id}",
            }
            for incident in CorrelatedIncident.query.filter(
                (CorrelatedIncident.incident_id.ilike(like))
                | (CorrelatedIncident.endpoint_id.ilike(like))
                | (CorrelatedIncident.correlation_rule_id.ilike(like))
            ).limit(limit)
        ],
        "rules": _search_rules(like, limit),
    }


def _search_telemetry(term: str, limit: int) -> list[Telemetry]:
    """Search telemetry by ID or common text fields."""

    if term.isdigit():
        event = Telemetry.query.get(int(term))
        return [] if event is None else [event]

    like = f"%{term}%"
    return (
        Telemetry.query.filter(
            (Telemetry.endpoint_id.ilike(like))
            | (Telemetry.collector.ilike(like))
            | (Telemetry.event_type.ilike(like))
            | (Telemetry.severity.ilike(like))
        )
        .order_by(Telemetry.timestamp.desc())
        .limit(limit)
        .all()
    )


def _search_rules(like: str, limit: int) -> list[dict[str, Any]]:
    """Search detection and correlation rule catalogs."""

    detection = [
        {
            "label": rule.rule_id,
            "meta": rule.name,
            "url": "/detection-rules",
        }
        for rule in DetectionRule.query.filter(
            (DetectionRule.rule_id.ilike(like)) | (DetectionRule.name.ilike(like))
        ).limit(limit)
    ]
    remaining = max(limit - len(detection), 0)
    correlation = [
        {
            "label": rule.rule_id,
            "meta": rule.name,
            "url": "/correlation-rules",
        }
        for rule in CorrelationRule.query.filter(
            (CorrelationRule.rule_id.ilike(like)) | (CorrelationRule.name.ilike(like))
        ).limit(remaining)
    ]
    return detection + correlation
