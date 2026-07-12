import time

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from models import db
from services.platform_service import (
    APP_VERSION,
    SERVER_STARTED_AT,
    _format_duration,
    get_system_health,
)
from utils.deployment_status import effective_public_url


health_api_bp = Blueprint("health_api", __name__)


@health_api_bp.get("")
def health():
    """Return deployment health for load balancers and uptime checks."""

    database_status = "online"
    status = "ok"
    status_code = 200
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"
        status = "degraded"
        status_code = 503
    health = get_system_health()

    return (
        jsonify(
            {
                "status": status,
                "application_version": APP_VERSION,
                "version": APP_VERSION,
                "application_mode": current_app.config["APPLICATION_MODE"],
                "mode": current_app.config["APPLICATION_MODE"],
                "database": database_status,
                "database_status": database_status,
                "gunicorn_running": health["Gunicorn Status"],
                "nginx_reachable": health["Nginx Status"],
                "disk_usage": health["Disk Usage"],
                "memory_usage": health["Memory Usage"],
                "cpu_usage": health["CPU Usage"],
                "uptime": _format_duration(time.time() - SERVER_STARTED_AT),
                "server_uptime": _format_duration(time.time() - SERVER_STARTED_AT),
                "public_url": effective_public_url(),
            }
        ),
        status_code,
    )
