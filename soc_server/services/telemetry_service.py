from datetime import datetime, timezone
from typing import Any

from models import Telemetry, db


VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}


def store_events(payload: dict[str, Any]) -> tuple[bool, str, int]:
    """Validate, normalize, and store telemetry events."""

    events = payload.get("events")
    if not isinstance(events, list) or not events:
        return False, "events must be a non-empty list.", 0

    telemetry_rows = []
    for event in events:
        valid, message = validate_event(event)
        if not valid:
            return False, message, 0
        telemetry_rows.append(normalize_event(event))

    db.session.add_all(telemetry_rows)
    db.session.commit()
    run_detection(telemetry_rows)
    return True, "telemetry stored.", len(telemetry_rows)


def validate_event(event: Any) -> tuple[bool, str]:
    """Validate one telemetry event payload."""

    if not isinstance(event, dict):
        return False, "each event must be an object."

    required_fields = ["endpoint_id", "collector", "event_type", "timestamp", "data"]
    for field in required_fields:
        if field not in event:
            return False, f"{field} is required."

    severity = str(event.get("severity", "info")).strip().lower()
    if severity not in VALID_SEVERITIES:
        return False, "severity is invalid."

    if not isinstance(event["data"], dict):
        return False, "data must be an object."

    return True, ""


def normalize_event(event: dict[str, Any]) -> Telemetry:
    """Normalize one incoming telemetry event into a database row."""

    return Telemetry(
        endpoint_id=str(event["endpoint_id"]).strip(),
        collector=str(event["collector"]).strip().lower(),
        event_type=str(event["event_type"]).strip().lower(),
        severity=str(event.get("severity", "info")).strip().lower(),
        timestamp=parse_timestamp(event["timestamp"]),
        raw_data=event["data"],
        processed=False,
    )


def list_events(filters: dict[str, str]) -> list[Telemetry]:
    """Return telemetry events newest first with optional filters."""

    query = Telemetry.query

    if filters.get("endpoint"):
        query = query.filter(Telemetry.endpoint_id == filters["endpoint"])
    if filters.get("collector"):
        query = query.filter(Telemetry.collector == filters["collector"])
    if filters.get("severity"):
        query = query.filter(Telemetry.severity == filters["severity"])

    return query.order_by(Telemetry.timestamp.desc()).limit(500).all()


def serialize_event(event: Telemetry) -> dict[str, Any]:
    """Convert telemetry model to JSON-safe API response."""

    return {
        "id": event.id,
        "endpoint_id": event.endpoint_id,
        "collector": event.collector,
        "event_type": event.event_type,
        "severity": event.severity,
        "timestamp": event.timestamp.isoformat(),
        "raw_data": event.raw_data,
        "processed": event.processed,
    }


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp and normalize naive values to UTC."""

    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def run_detection(events: list[Telemetry]) -> None:
    """Evaluate stored telemetry without embedding rule logic in this service."""

    from detection.engine import DetectionEngine

    DetectionEngine().evaluate(events)
