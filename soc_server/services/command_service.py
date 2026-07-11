import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from models import Endpoint, EndpointCommand, db, utc_now
from utils.constants import IDENTITY_CHANGED


COMMAND_PENDING = "PENDING"
COMMAND_RUNNING = "RUNNING"
COMMAND_COMPLETED = "COMPLETED"
COMMAND_FAILED = "FAILED"
COMMAND_EXPIRED = "EXPIRED"

COMMAND_STATUSES = [
    COMMAND_PENDING,
    COMMAND_RUNNING,
    COMMAND_COMPLETED,
    COMMAND_FAILED,
    COMMAND_EXPIRED,
]

SAFE_COMMANDS: dict[str, str] = {
    "heartbeat_now": "Force Heartbeat",
    "sync_telemetry": "Sync Telemetry",
    "collect_diagnostics": "Run Diagnostics",
    "restart_agent": "Restart Agent",
    "download_logs": "Collect Logs",
}

COMMAND_EXPIRY_SECONDS = 300

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandResult:
    """Result returned by command service operations."""

    success: bool
    message: str
    command: EndpointCommand | None = None
    commands: list[EndpointCommand] | None = None
    status_code: int = 200


def queue_command(
    endpoint_id: str,
    command_type: str,
    requested_by: str,
    payload: dict[str, Any] | None = None,
) -> CommandResult:
    """Queue a safe manual endpoint response command."""

    endpoint = Endpoint.query.filter_by(endpoint_id=endpoint_id).first()
    if endpoint is None:
        return CommandResult(False, "Endpoint not found.", status_code=404)

    if endpoint.identity_status == IDENTITY_CHANGED:
        return CommandResult(
            False,
            "Endpoint identity mismatch. Command rejected.",
            status_code=409,
        )

    if command_type not in SAFE_COMMANDS:
        return CommandResult(False, "Unsupported command type.", status_code=400)

    command = EndpointCommand(
        command_id=_generate_command_id(),
        endpoint_id=endpoint.endpoint_id,
        command_type=command_type,
        command_payload=payload or {},
        requested_by=(requested_by.strip() or "Analyst"),
    )
    db.session.add(command)
    db.session.commit()
    logger.info(
        "Endpoint command queued | command=%s endpoint=%s type=%s requested_by=%s",
        command.command_id,
        command.endpoint_id,
        command.command_type,
        command.requested_by,
    )
    return CommandResult(True, "Command queued.", command, status_code=201)


def get_pending_commands(
    endpoint_id: str,
    api_key: str,
    device_fingerprint: str,
) -> CommandResult:
    """Return pending commands for an authenticated healthy endpoint."""

    auth_result = _validate_endpoint_identity(endpoint_id, api_key, device_fingerprint)
    if not auth_result.success:
        return auth_result

    expire_stale_commands()
    commands = (
        EndpointCommand.query.filter_by(endpoint_id=endpoint_id, status=COMMAND_PENDING)
        .order_by(EndpointCommand.created_at.asc())
        .limit(10)
        .all()
    )
    for command in commands:
        command.status = COMMAND_RUNNING
        command.started_at = utc_now()
    db.session.commit()

    if commands:
        logger.info(
            "Endpoint command poll | endpoint=%s commands=%s",
            endpoint_id,
            len(commands),
        )
    return CommandResult(True, "Pending commands returned.", commands=commands, status_code=200)


def list_running_for_endpoint(endpoint_id: str) -> list[EndpointCommand]:
    """Return commands currently assigned to an endpoint but not completed."""

    return (
        EndpointCommand.query.filter(
            EndpointCommand.endpoint_id == endpoint_id,
            EndpointCommand.status.in_([COMMAND_PENDING, COMMAND_RUNNING]),
        )
        .order_by(EndpointCommand.created_at.desc())
        .all()
    )


def list_commands(
    endpoint_id: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[EndpointCommand]:
    """Return endpoint commands newest first with optional filters."""

    expire_stale_commands()
    query = EndpointCommand.query
    if endpoint_id:
        query = query.filter_by(endpoint_id=endpoint_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(EndpointCommand.created_at.desc()).limit(limit).all()


def get_endpoint_command_context(endpoint_id: str) -> dict[str, Any]:
    """Return compact command health context for endpoint tables."""

    pending = EndpointCommand.query.filter_by(
        endpoint_id=endpoint_id,
        status=COMMAND_PENDING,
    ).count()
    last_command = (
        EndpointCommand.query.filter_by(endpoint_id=endpoint_id)
        .order_by(EndpointCommand.created_at.desc())
        .first()
    )
    return {
        "pending_commands": pending,
        "last_command": last_command,
    }


def update_command_result(
    endpoint_id: str,
    api_key: str,
    device_fingerprint: str,
    command_id: str,
    status: str,
    response: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> CommandResult:
    """Persist command execution result from an authenticated endpoint."""

    auth_result = _validate_endpoint_identity(endpoint_id, api_key, device_fingerprint)
    if not auth_result.success:
        return auth_result

    command = EndpointCommand.query.filter_by(
        command_id=command_id,
        endpoint_id=endpoint_id,
    ).first()
    if command is None:
        return CommandResult(False, "Command not found.", status_code=404)

    new_status = status.strip().upper()
    if new_status not in {COMMAND_RUNNING, COMMAND_COMPLETED, COMMAND_FAILED}:
        return CommandResult(
            False,
            "Unsupported command status.",
            command,
            status_code=400,
        )

    command.status = new_status
    if new_status == COMMAND_RUNNING and command.started_at is None:
        command.started_at = utc_now()
    if new_status in {COMMAND_COMPLETED, COMMAND_FAILED}:
        command.completed_at = utc_now()
    command.response = response or {}
    command.error_message = error_message
    db.session.commit()
    logger.info(
        "Endpoint command result | command=%s endpoint=%s status=%s error=%s",
        command.command_id,
        command.endpoint_id,
        command.status,
        command.error_message or "",
    )
    return CommandResult(True, "Command result stored.", command, status_code=200)


def expire_stale_commands() -> int:
    """Mark old unclaimed commands as expired."""

    cutoff = utc_now() - timedelta(seconds=COMMAND_EXPIRY_SECONDS)
    commands = EndpointCommand.query.filter(
        EndpointCommand.status == COMMAND_PENDING,
        EndpointCommand.created_at < cutoff,
    ).all()
    for command in commands:
        command.status = COMMAND_EXPIRED
        command.completed_at = utc_now()
        command.error_message = "Command expired before endpoint pickup."
    if commands:
        db.session.commit()
    return len(commands)


def serialize_command(command: EndpointCommand) -> dict[str, Any]:
    """Serialize an endpoint command for APIs and templates."""

    duration = None
    if command.started_at and command.completed_at:
        duration = round((command.completed_at - command.started_at).total_seconds(), 2)

    return {
        "id": command.id,
        "command_id": command.command_id,
        "endpoint_id": command.endpoint_id,
        "command_type": command.command_type,
        "command_label": SAFE_COMMANDS.get(command.command_type, command.command_type),
        "command_payload": command.command_payload or {},
        "status": command.status,
        "created_at": _isoformat(command.created_at),
        "started_at": _isoformat(command.started_at),
        "completed_at": _isoformat(command.completed_at),
        "duration_seconds": duration,
        "requested_by": command.requested_by,
        "response": command.response or {},
        "error_message": command.error_message,
    }


def _validate_endpoint_identity(
    endpoint_id: str,
    api_key: str,
    device_fingerprint: str,
) -> CommandResult:
    endpoint = Endpoint.query.filter_by(endpoint_id=endpoint_id).first()
    if endpoint is None or endpoint.api_key != api_key:
        return CommandResult(
            False,
            "Endpoint not found or API key invalid.",
            status_code=404,
        )

    if endpoint.identity_status == IDENTITY_CHANGED:
        return CommandResult(False, "Endpoint identity mismatch.", status_code=409)

    if endpoint.device_fingerprint and endpoint.device_fingerprint != device_fingerprint:
        endpoint.identity_status = IDENTITY_CHANGED
        endpoint.identity_previous_fingerprint = endpoint.device_fingerprint
        endpoint.identity_observed_fingerprint = device_fingerprint
        endpoint.identity_last_changed = utc_now()
        db.session.commit()
        logger.warning(
            "Endpoint command rejected due to fingerprint mismatch | endpoint=%s",
            endpoint_id,
        )
        return CommandResult(False, "Endpoint fingerprint mismatch.", status_code=409)

    return CommandResult(True, "Endpoint authenticated.")


def _generate_command_id() -> str:
    last_command = EndpointCommand.query.order_by(EndpointCommand.id.desc()).first()
    next_number = 1 if last_command is None else last_command.id + 1
    return f"CMD-{next_number:06d}"


def _isoformat(value) -> str | None:
    return value.isoformat() if value else None
