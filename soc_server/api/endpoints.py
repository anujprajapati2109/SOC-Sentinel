from flask import Blueprint, current_app, jsonify, request

from services.endpoint_service import (
    get_endpoint,
    list_endpoints,
    mark_expired_endpoints_offline,
    register_endpoint,
    serialize_endpoint,
    update_heartbeat,
)


endpoints_api_bp = Blueprint("endpoints_api", __name__)


@endpoints_api_bp.post("/register")
def register():
    """Register a new endpoint agent."""

    payload = request.get_json(silent=True) or {}

    try:
        endpoint = register_endpoint(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"endpoint": serialize_endpoint(endpoint, include_api_key=True)}), 201


@endpoints_api_bp.post("/heartbeat")
def heartbeat():
    """Receive endpoint heartbeat and update online status."""

    payload = request.get_json(silent=True) or {}
    endpoint_id = payload.get("endpoint_id")
    api_key = payload.get("api_key")

    if not endpoint_id:
        return jsonify({"error": "endpoint_id is required."}), 400

    endpoint = update_heartbeat(
        endpoint_id,
        api_key,
        payload.get("device_fingerprint"),
    )
    if endpoint is None:
        return jsonify({"error": "Endpoint not found or API key is invalid."}), 404

    return jsonify({"endpoint": serialize_endpoint(endpoint)}), 200


@endpoints_api_bp.get("")
def index():
    """Return all registered endpoints."""

    mark_expired_endpoints_offline(
        current_app.config["ENDPOINT_HEARTBEAT_TIMEOUT_SECONDS"]
    )
    endpoints = [serialize_endpoint(endpoint) for endpoint in list_endpoints()]
    return jsonify({"endpoints": endpoints}), 200


@endpoints_api_bp.get("/<endpoint_id>")
def show(endpoint_id: str):
    """Return one endpoint by public endpoint ID."""

    mark_expired_endpoints_offline(
        current_app.config["ENDPOINT_HEARTBEAT_TIMEOUT_SECONDS"]
    )
    endpoint = get_endpoint(endpoint_id)
    if endpoint is None:
        return jsonify({"error": "Endpoint not found."}), 404

    return jsonify({"endpoint": serialize_endpoint(endpoint)}), 200
