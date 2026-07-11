from dataclasses import dataclass

from models import CorrelatedIncident, IncidentHistory, IncidentNote, db, utc_now


INCIDENT_STATUSES = [
    "OPEN",
    "ASSIGNED",
    "INVESTIGATING",
    "CONTAINED",
    "RESOLVED",
    "CLOSED",
    "FALSE_POSITIVE",
]

INCIDENT_PRIORITIES = ["Low", "Medium", "High", "Critical"]
DEFAULT_ACTOR = "Analyst"


@dataclass(frozen=True)
class WorkflowResult:
    """Result object returned by incident workflow operations."""

    success: bool
    message: str
    incident: CorrelatedIncident | None = None


def get_incident(incident_id: str) -> CorrelatedIncident | None:
    """Return one incident by public incident ID."""

    return CorrelatedIncident.query.filter_by(incident_id=incident_id).first()


def list_notes(incident_id: str) -> list[IncidentNote]:
    """Return investigation notes oldest first."""

    return (
        IncidentNote.query.filter_by(incident_id=incident_id)
        .order_by(IncidentNote.created_at.asc(), IncidentNote.id.asc())
        .all()
    )


def list_history(incident_id: str) -> list[IncidentHistory]:
    """Return auditable workflow history oldest first."""

    return (
        IncidentHistory.query.filter_by(incident_id=incident_id)
        .order_by(IncidentHistory.timestamp.asc(), IncidentHistory.id.asc())
        .all()
    )


def add_note(incident_id: str, author: str, note: str) -> WorkflowResult:
    """Add an analyst note and append an investigation history entry."""

    incident = get_incident(incident_id)
    if incident is None:
        return WorkflowResult(False, "Incident not found.")

    clean_note = note.strip()
    if not clean_note:
        return WorkflowResult(False, "Note cannot be empty.", incident)

    note_row = IncidentNote(
        incident_id=incident.incident_id,
        author=_clean_actor(author),
        note=clean_note,
    )
    db.session.add(note_row)
    _append_history(
        incident,
        action=f"Note added by {note_row.author}",
        actor=note_row.author,
    )
    db.session.commit()
    return WorkflowResult(True, "Investigation note added.", incident)


def edit_note(
    incident_id: str,
    note_id: int,
    author: str,
    note: str,
) -> WorkflowResult:
    """Edit an investigation note and record the edit in history."""

    incident = get_incident(incident_id)
    note_row = _get_note_for_incident(incident_id, note_id)
    if incident is None or note_row is None:
        return WorkflowResult(False, "Note not found.", incident)

    clean_note = note.strip()
    if not clean_note:
        return WorkflowResult(False, "Note cannot be empty.", incident)

    note_row.note = clean_note
    note_row.author = _clean_actor(author)
    _append_history(
        incident,
        action=f"Note #{note_row.id} edited by {note_row.author}",
        actor=note_row.author,
    )
    db.session.commit()
    return WorkflowResult(True, "Investigation note updated.", incident)


def delete_note(incident_id: str, note_id: int, actor: str) -> WorkflowResult:
    """Delete an investigation note and record a destructive action."""

    incident = get_incident(incident_id)
    note_row = _get_note_for_incident(incident_id, note_id)
    clean_actor = _clean_actor(actor)
    if incident is None or note_row is None:
        return WorkflowResult(False, "Note not found.", incident)

    db.session.delete(note_row)
    _append_history(
        incident,
        action=f"Note #{note_id} deleted by {clean_actor}",
        actor=clean_actor,
    )
    db.session.commit()
    return WorkflowResult(True, "Investigation note deleted.", incident)


def assign_incident(
    incident_id: str,
    assigned_to: str,
    actor: str,
) -> WorkflowResult:
    """Assign an incident to an analyst and move open incidents to ASSIGNED."""

    incident = get_incident(incident_id)
    if incident is None:
        return WorkflowResult(False, "Incident not found.")

    clean_assignee = assigned_to.strip()
    if not clean_assignee:
        return WorkflowResult(False, "Assigned analyst cannot be empty.", incident)

    previous_assignee = incident.assigned_to or "Unassigned"
    previous_status = incident.status
    incident.assigned_to = clean_assignee
    if incident.status == "OPEN":
        incident.status = "ASSIGNED"
    _append_history(
        incident,
        action=f"Assignment changed from {previous_assignee} to {clean_assignee}",
        actor=_clean_actor(actor),
        previous_status=previous_status,
        new_status=incident.status,
    )
    db.session.commit()
    return WorkflowResult(True, "Incident assignment updated.", incident)


def change_status(incident_id: str, status: str, actor: str) -> WorkflowResult:
    """Change incident status and update lifecycle timestamps."""

    incident = get_incident(incident_id)
    if incident is None:
        return WorkflowResult(False, "Incident not found.")

    new_status = status.strip().upper()
    if new_status not in INCIDENT_STATUSES:
        return WorkflowResult(False, "Unsupported incident status.", incident)

    previous_status = incident.status
    if previous_status == new_status:
        return WorkflowResult(True, "Incident status unchanged.", incident)

    incident.status = new_status
    now = utc_now()
    if new_status == "RESOLVED":
        incident.resolved_at = now
    elif new_status == "CLOSED":
        incident.closed_at = now
        if incident.resolved_at is None:
            incident.resolved_at = now
    elif new_status in {"OPEN", "ASSIGNED", "INVESTIGATING", "CONTAINED"}:
        incident.closed_at = None

    _append_history(
        incident,
        action=f"Status changed from {previous_status} to {new_status}",
        actor=_clean_actor(actor),
        previous_status=previous_status,
        new_status=new_status,
    )
    db.session.commit()
    return WorkflowResult(True, "Incident status updated.", incident)


def change_priority(incident_id: str, priority: str, actor: str) -> WorkflowResult:
    """Change incident analyst priority."""

    incident = get_incident(incident_id)
    if incident is None:
        return WorkflowResult(False, "Incident not found.")

    new_priority = priority.strip().title()
    if new_priority not in INCIDENT_PRIORITIES:
        return WorkflowResult(False, "Unsupported incident priority.", incident)

    previous_priority = incident.priority or "Medium"
    incident.priority = new_priority
    _append_history(
        incident,
        action=f"Priority changed from {previous_priority} to {new_priority}",
        actor=_clean_actor(actor),
    )
    db.session.commit()
    return WorkflowResult(True, "Incident priority updated.", incident)


def mark_false_positive(incident_id: str, actor: str) -> WorkflowResult:
    """Mark an incident as a false positive."""

    return change_status(incident_id, "FALSE_POSITIVE", actor)


def resolve_incident(incident_id: str, actor: str) -> WorkflowResult:
    """Resolve an incident."""

    return change_status(incident_id, "RESOLVED", actor)


def close_incident(incident_id: str, actor: str) -> WorkflowResult:
    """Close an incident after investigation."""

    return change_status(incident_id, "CLOSED", actor)


def reopen_incident(incident_id: str, actor: str) -> WorkflowResult:
    """Reopen a resolved, closed, or false-positive incident."""

    return change_status(incident_id, "OPEN", actor)


def _append_history(
    incident: CorrelatedIncident,
    action: str,
    actor: str,
    previous_status: str | None = None,
    new_status: str | None = None,
) -> None:
    """Append an incident workflow history record."""

    db.session.add(
        IncidentHistory(
            incident_id=incident.incident_id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            actor=actor,
        )
    )


def _get_note_for_incident(incident_id: str, note_id: int) -> IncidentNote | None:
    return IncidentNote.query.filter_by(id=note_id, incident_id=incident_id).first()


def _clean_actor(actor: str) -> str:
    return actor.strip() or DEFAULT_ACTOR
