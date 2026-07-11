from flask import Blueprint, jsonify, request

from services.telemetry_service import list_events, serialize_event, store_events


telemetry_api_bp = Blueprint("telemetry_api", __name__)


@telemetry_api_bp.post("")
def create():
    """Receive telemetry batches from agents."""

    payload = request.get_json(silent=True) or {}
    success, message, count = store_events(payload)
    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message, "stored": count}), 201


@telemetry_api_bp.get("")
def index():
    """Return telemetry events with optional filters."""

    filters = {
        "endpoint": request.args.get("endpoint", "").strip(),
        "collector": request.args.get("collector", "").strip().lower(),
        "severity": request.args.get("severity", "").strip().lower(),
    }
    events = [serialize_event(event) for event in list_events(filters)]
    return jsonify({"events": events}), 200
