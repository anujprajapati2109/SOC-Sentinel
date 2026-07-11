from flask import Flask

from .dashboard import dashboard_bp


def register_blueprints(app: Flask) -> None:
    """Register all route blueprints in one place."""

    app.register_blueprint(dashboard_bp)
