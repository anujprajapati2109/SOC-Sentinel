from flask import Blueprint, jsonify

from services.dashboard_service import dashboard_service


dashboard_api_bp = Blueprint("dashboard_api", __name__)


@dashboard_api_bp.get("")
def index():
    """Return cached SOC command center statistics."""

    return jsonify(dashboard_service.get_dashboard()), 200
