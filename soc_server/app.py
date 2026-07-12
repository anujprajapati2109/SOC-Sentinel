from datetime import timezone
from urllib.parse import urlencode

from flask import Flask, render_template, url_for
from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config_by_name, resolve_config_name
from models import db
from api import register_api_blueprints
from routes import register_blueprints
from correlation.registry import configure_correlation_engine
from correlation.services.correlation_service import seed_correlation_rules
from services.detection_rule_service import seed_detection_rules
from services.platform_service import APP_SUBTITLE, APP_VERSION
from services.settings_service import seed_settings
from models import utc_now
from utils.deployment_status import effective_public_url
from utils.logging_config import ERROR_LOGGER, configure_logging
import logging


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""

    selected_config = config_by_name.get(
        resolve_config_name(config_name),
        config_by_name["default"],
    )

    app = Flask(__name__)
    app.config.from_object(selected_config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    configure_logging(app)

    initialize_extensions(app)
    register_template_context(app)
    register_blueprints(app)
    register_api_blueprints(app)
    register_error_handlers(app)
    create_database(app)

    return app


def initialize_extensions(app: Flask) -> None:
    """Bind Flask extensions to the app instance."""

    db.init_app(app)


def register_template_context(app: Flask) -> None:
    """Provide product metadata to every template."""

    @app.context_processor
    def inject_product_context() -> dict:
        from services.settings_service import get_setting_value

        return {
            "app_version": APP_VERSION,
            "app_subtitle": APP_SUBTITLE,
            "soc_name": get_setting_value("soc_name", "SOC Sentinel"),
            "theme": get_setting_value("theme", "Dark").lower(),
            "dashboard_refresh_interval": get_setting_value(
                "dashboard_refresh_interval",
                "5",
            ),
            "public_url": effective_public_url(),
            "application_mode": app.config["APPLICATION_MODE"],
            "server_time": utc_now(),
        }

    @app.template_global()
    def url_with_query(route_name: str, **query_params: object) -> str:
        """Build a route URL with query parameters.

        Flask's url_for uses "endpoint" as its first argument name, so templates
        cannot safely call url_for("dashboard.telemetry", endpoint="EP-000001").
        This helper keeps endpoint filters usable without colliding with Flask's
        internal parameter name.
        """

        clean_params = {
            key: value
            for key, value in query_params.items()
            if value is not None and value != ""
        }
        if not clean_params:
            return url_for(route_name)
        return f"{url_for(route_name)}?{urlencode(clean_params)}"

    @app.template_global()
    def time_ago(value) -> str:
        """Return a compact relative time label for SOC tables."""

        if value is None:
            return "Never"
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        delta = utc_now() - value
        seconds = max(int(delta.total_seconds()), 0)
        if seconds < 60:
            return f"{seconds} sec ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hr ago"
        return f"{hours // 24} day ago"


def register_error_handlers(app: Flask) -> None:
    """Render professional error pages instead of raw Flask errors."""

    @app.errorhandler(404)
    def not_found(error):
        return (
            render_template(
                "error.html",
                code=404,
                title="Page Not Found",
                message="The requested SOC Sentinel page does not exist.",
            ),
            404,
        )

    @app.errorhandler(500)
    def server_error(error):
        logging.getLogger(ERROR_LOGGER).exception("Unhandled server error: %s", error)
        return (
            render_template(
                "error.html",
                code=500,
                title="Server Error",
                message="SOC Sentinel encountered an internal server error.",
            ),
            500,
        )


def create_database(app: Flask) -> None:
    """Create the SQLite database and tables on first startup."""

    app.config["DATABASE_DIR"].mkdir(parents=True, exist_ok=True)

    with app.app_context():
        db.create_all()
        ensure_endpoint_schema()
        ensure_detection_schema()
        ensure_alert_schema()
        ensure_correlation_rule_schema()
        ensure_correlated_incident_schema()
        ensure_incident_workflow_schema()
        ensure_endpoint_command_schema()
        ensure_settings_schema()
        seed_detection_rules()
        seed_correlation_rules()
        seed_settings()
        configure_correlation_engine(
            retention_seconds=app.config["CORRELATION_RETENTION_SECONDS"],
            duplicate_cooldown_seconds=app.config[
                "CORRELATION_DUPLICATE_COOLDOWN_SECONDS"
            ],
        ).start()


def ensure_endpoint_schema() -> None:
    """Add v0.2 endpoint columns when upgrading an existing SQLite database."""

    inspector = inspect(db.engine)
    if not inspector.has_table("endpoints"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("endpoints")}
    column_definitions = {
        "username": "VARCHAR(120)",
        "operating_system": "VARCHAR(120)",
        "mac_address": "VARCHAR(64)",
        "api_key": "VARCHAR(128)",
        "registered_at": "DATETIME",
        "last_seen": "DATETIME",
        "python_version": "VARCHAR(40)",
        "architecture": "VARCHAR(80)",
        "processor": "VARCHAR(160)",
        "cpu_count": "VARCHAR(20)",
        "total_memory_mb": "VARCHAR(30)",
        "system_drive": "VARCHAR(20)",
        "device_fingerprint": "VARCHAR(64)",
        "identity_status": "VARCHAR(30) DEFAULT 'Unknown'",
        "identity_previous_fingerprint": "VARCHAR(64)",
        "identity_observed_fingerprint": "VARCHAR(64)",
        "identity_last_changed": "DATETIME",
    }

    for column_name, column_type in column_definitions.items():
        if column_name not in existing_columns:
            try:
                db.session.execute(
                    text(f"ALTER TABLE endpoints ADD COLUMN {column_name} {column_type}")
                )
                db.session.commit()
            except OperationalError as exc:
                db.session.rollback()
                if "duplicate column name" not in str(exc).lower():
                    raise


def ensure_detection_schema() -> None:
    """Add v0.5 detection rule columns when upgrading SQLite."""

    add_missing_columns(
        "detection_rules",
        {
            "rule_id": "VARCHAR(80)",
            "name": "VARCHAR(160)",
            "description": "TEXT",
            "severity": "VARCHAR(30)",
            "enabled": "BOOLEAN DEFAULT 1",
            "threshold": "INTEGER DEFAULT 1",
            "time_window": "INTEGER DEFAULT 0",
            "mitre_tactic": "VARCHAR(120)",
            "mitre_technique": "VARCHAR(120)",
        },
    )


def ensure_alert_schema() -> None:
    """Add v0.5 alert columns when upgrading the placeholder alerts table."""

    add_missing_columns(
        "alerts",
        {
            "alert_id": "VARCHAR(24)",
            "endpoint_id": "VARCHAR(20)",
            "rule_id": "VARCHAR(80)",
            "description": "TEXT",
            "timestamp": "DATETIME",
        },
    )


def ensure_correlation_rule_schema() -> None:
    """Add v0.6.1 correlation rule columns when upgrading SQLite."""

    add_missing_columns(
        "correlation_rules",
        {
            "rule_id": "VARCHAR(80)",
            "name": "VARCHAR(160)",
            "description": "TEXT",
            "enabled": "BOOLEAN DEFAULT 1",
            "severity": "VARCHAR(30)",
            "time_window": "INTEGER DEFAULT 0",
            "mitre_tactic": "VARCHAR(120)",
            "mitre_technique": "VARCHAR(120)",
            "version": "VARCHAR(20) DEFAULT '1.0'",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
    )


def ensure_correlated_incident_schema() -> None:
    """Add v0.6.1 correlated incident columns when upgrading SQLite."""

    add_missing_columns(
        "correlated_incidents",
        {
            "incident_id": "VARCHAR(24)",
            "endpoint_id": "VARCHAR(20)",
            "correlation_rule_id": "VARCHAR(80)",
            "severity": "VARCHAR(30)",
            "status": "VARCHAR(30) DEFAULT 'OPEN'",
            "title": "VARCHAR(200) DEFAULT 'Correlated Incident'",
            "summary": "TEXT",
            "confidence": "INTEGER DEFAULT 0",
            "risk_score": "INTEGER DEFAULT 0",
            "assigned_to": "VARCHAR(120)",
            "priority": "VARCHAR(30) DEFAULT 'Medium'",
            "mitre_tactic": "VARCHAR(120)",
            "mitre_technique": "VARCHAR(120)",
            "timeline": "JSON DEFAULT '[]'",
            "matched_alert_ids": "JSON DEFAULT '[]'",
            "evidence": "JSON DEFAULT '[]'",
            "evidence_hash": "VARCHAR(64) DEFAULT ''",
            "created_at": "DATETIME",
            "resolved_at": "DATETIME",
            "closed_at": "DATETIME",
            "updated_at": "DATETIME",
        },
    )


def ensure_incident_workflow_schema() -> None:
    """Add v0.7 incident notes and history schema when upgrading SQLite."""

    add_missing_columns(
        "incident_notes",
        {
            "incident_id": "VARCHAR(24)",
            "author": "VARCHAR(120) DEFAULT 'Analyst'",
            "note": "TEXT",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
    )
    add_missing_columns(
        "incident_history",
        {
            "incident_id": "VARCHAR(24)",
            "action": "VARCHAR(120)",
            "previous_status": "VARCHAR(30)",
            "new_status": "VARCHAR(30)",
            "actor": "VARCHAR(120) DEFAULT 'Analyst'",
            "timestamp": "DATETIME",
        },
    )


def ensure_endpoint_command_schema() -> None:
    """Add v0.8 endpoint command queue schema when upgrading SQLite."""

    add_missing_columns(
        "endpoint_commands",
        {
            "command_id": "VARCHAR(24)",
            "endpoint_id": "VARCHAR(20)",
            "command_type": "VARCHAR(80)",
            "command_payload": "JSON DEFAULT '{}'",
            "status": "VARCHAR(30) DEFAULT 'PENDING'",
            "created_at": "DATETIME",
            "started_at": "DATETIME",
            "completed_at": "DATETIME",
            "requested_by": "VARCHAR(120) DEFAULT 'Analyst'",
            "response": "JSON",
            "error_message": "TEXT",
        },
    )


def ensure_settings_schema() -> None:
    """Add v0.6.4 settings table columns when upgrading SQLite."""

    add_missing_columns(
        "settings",
        {
            "key": "VARCHAR(120)",
            "value": "VARCHAR(500)",
            "label": "VARCHAR(160)",
            "category": "VARCHAR(80)",
            "value_type": "VARCHAR(30) DEFAULT 'text'",
            "description": "TEXT",
            "updated_at": "DATETIME",
        },
    )


def add_missing_columns(table_name: str, column_definitions: dict[str, str]) -> None:
    """Add missing SQLite columns with duplicate-column race tolerance."""

    inspector = inspect(db.engine)
    if not inspector.has_table(table_name):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, column_type in column_definitions.items():
        if column_name not in existing_columns:
            try:
                db.session.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                )
                db.session.commit()
            except OperationalError as exc:
                db.session.rollback()
                if "duplicate column name" not in str(exc).lower():
                    raise


app = create_app()


if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"])
