import time

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from models import db
from services.platform_service import APP_VERSION, SERVER_STARTED_AT, _format_duration


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

    return (
        jsonify(
            {
                "status": status,
                "version": APP_VERSION,
                "database": database_status,
                "uptime": _format_duration(time.time() - SERVER_STARTED_AT),
                "mode": current_app.config["APPLICATION_MODE"],
                "public_url": current_app.config["PUBLIC_URL"],
            }
        ),
        status_code,
    )
