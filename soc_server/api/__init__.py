from flask import Flask

from .alerts import alerts_api_bp
from .commands import commands_api_bp
from .dashboard import dashboard_api_bp
from .endpoints import endpoints_api_bp
from .health import health_api_bp
from .logs import logs_api_bp
from .search import search_api_bp
from .telemetry import telemetry_api_bp


def register_api_blueprints(app: Flask) -> None:
    """Register API blueprints separately from server-rendered pages."""

    app.register_blueprint(endpoints_api_bp, url_prefix="/api/v1/endpoints")
    app.register_blueprint(logs_api_bp, url_prefix="/api/v1/logs")
    app.register_blueprint(alerts_api_bp, url_prefix="/api/v1/alerts")
    app.register_blueprint(telemetry_api_bp, url_prefix="/api/v1/telemetry")
    app.register_blueprint(commands_api_bp, url_prefix="/api/v1/commands")
    app.register_blueprint(dashboard_api_bp, url_prefix="/api/v1/dashboard")
    app.register_blueprint(health_api_bp, url_prefix="/api/v1/health")
    app.register_blueprint(health_api_bp, url_prefix="/health", name="health_root")
    app.register_blueprint(search_api_bp, url_prefix="/api/v1/search")
