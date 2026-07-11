from flask import Blueprint, jsonify, request

from services.command_service import (
    get_pending_commands,
    list_commands,
    queue_command,
    serialize_command,
    update_command_result,
)


commands_api_bp = Blueprint("commands_api", __name__)


@commands_api_bp.post("")
def create_command():
    """Queue a safe endpoint response command from the dashboard."""

    payload = request.get_json(silent=True) or {}
    result = queue_command(
        endpoint_id=str(payload.get("endpoint_id", "")).strip(),
        command_type=str(payload.get("command_type", "")).strip(),
        requested_by=str(payload.get("requested_by", "Analyst")),
        payload=payload.get("command_payload") or {},
    )
    body = {"message": result.message}
    if result.command is not None:
        body["command"] = serialize_command(result.command)
    if not result.success:
        body["error"] = result.message
    return jsonify(body), result.status_code


@commands_api_bp.get("/pending/<endpoint_id>")
def pending_commands(endpoint_id: str):
    """Return pending commands for an authenticated endpoint agent."""

    result = get_pending_commands(
        endpoint_id=endpoint_id,
        api_key=request.headers.get("X-API-Key", ""),
        device_fingerprint=request.headers.get("X-Device-Fingerprint", ""),
    )
    if not result.success:
        return jsonify({"error": result.message}), result.status_code

    return (
        jsonify(
            {
                "commands": [
                    serialize_command(command)
                    for command in (result.commands or [])
                ]
            }
        ),
        200,
    )


@commands_api_bp.post("/result")
def command_result():
    """Receive execution results from an endpoint agent."""

    payload = request.get_json(silent=True) or {}
    result = update_command_result(
        endpoint_id=str(payload.get("endpoint_id", "")).strip(),
        api_key=str(payload.get("api_key", "")).strip(),
        device_fingerprint=str(payload.get("device_fingerprint", "")).strip(),
        command_id=str(payload.get("command_id", "")).strip(),
        status=str(payload.get("status", "")).strip(),
        response=payload.get("response") or {},
        error_message=payload.get("error_message"),
    )
    body = {"message": result.message}
    if result.command is not None:
        body["command"] = serialize_command(result.command)
    if not result.success:
        body["error"] = result.message
    return jsonify(body), result.status_code


@commands_api_bp.get("")
def index():
    """Return command history for dashboard views."""

    commands = list_commands(
        endpoint_id=request.args.get("endpoint", "").strip(),
        status=request.args.get("status", "").strip(),
    )
    return jsonify({"commands": [serialize_command(command) for command in commands]}), 200
