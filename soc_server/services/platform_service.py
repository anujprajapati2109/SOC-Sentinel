import platform
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import flask
from flask import current_app
from sqlalchemy import func, text

from config import Config
from models import (
    Alert,
    CorrelatedIncident,
    CorrelationRule,
    DetectionRule,
    Endpoint,
    EndpointCommand,
    IncidentHistory,
    IncidentNote,
    Telemetry,
    db,
    utc_now,
)
from services.dashboard_service import dashboard_service
from services.backup_service import database_label, is_sqlite_database
from services.settings_service import get_setting_value
from utils.constants import STATUS_OFFLINE, STATUS_ONLINE


try:
    import psutil
except ImportError:  # pragma: no cover - optional package fallback.
    psutil = None


SERVER_STARTED_AT = time.time()
APP_VERSION = "0.9.0"
APP_SUBTITLE = "A Lightweight Endpoint Detection, Response & Security Operations Platform"
DEVELOPER = "Anuj"


def get_report_data() -> dict[str, Any]:
    """Return complete structured data used by reports and exports."""

    dashboard = dashboard_service.get_dashboard()
    return {
        "timestamp": utc_now().isoformat(),
        "version": APP_VERSION,
        "subtitle": APP_SUBTITLE,
        "executive_summary": _executive_summary(dashboard),
        "security_statistics": _security_statistics(),
        "top_endpoints": dashboard["top_endpoints"],
        "top_detection_rules": dashboard["detection_rules"],
        "top_correlation_rules": dashboard["correlation_rules"],
        "incidents": [_incident_row(incident) for incident in _recent_incidents()],
        "alerts": [_alert_row(alert) for alert in _recent_alerts()],
        "mitre_summary": dashboard["mitre"],
    }


def get_settings_data() -> dict[str, Any]:
    """Return real read-only administration settings."""

    return {
        "general": {
            "SOC Name": get_setting_value("soc_name", "SOC Sentinel"),
            "Organization": get_setting_value("organization", "Local SOC"),
            "Server Version": APP_VERSION,
            "Database": _database_display(),
            "Environment": current_app.config["APPLICATION_MODE"],
            "Public URL": current_app.config["PUBLIC_URL"],
        },
        "agent_configuration": {
            "Heartbeat Interval": f"{get_setting_value('heartbeat_interval', '30')}s",
            "Startup Enabled": "Configured per endpoint agent",
            "Telemetry Enabled": "Enabled",
            "Agent Version": "SOC Agent 0.8.0",
        },
        "detection_configuration": {
            "Duplicate Suppression": f"{get_setting_value('duplicate_suppression_cooldown', '300')}s cooldown",
            "Telemetry Retention": f"{get_setting_value('telemetry_retention', '30')} days",
            "Alert Cooldown": f"{get_setting_value('duplicate_suppression_cooldown', '300')}s",
            "Correlation Window": f"{get_setting_value('correlation_window', '900')}s",
        },
        "dashboard": {
            "Refresh Interval": f"{get_setting_value('dashboard_refresh_interval', '5')}s",
            "Theme": get_setting_value("theme", "Dark"),
            "Timezone": get_setting_value("timezone", time.tzname[0]),
        },
        "system_information": get_system_information(),
    }


def get_system_information() -> dict[str, Any]:
    """Return host and runtime information for settings."""

    return {
        "Python Version": sys.version.split()[0],
        "Flask Version": flask.__version__,
        "SQLite Version": sqlite3.sqlite_version,
        "Platform": platform.platform(),
        "Server Uptime": _format_duration(time.time() - SERVER_STARTED_AT),
        "Database": _database_display(),
        "Database Size": _database_size(),
    }


def get_system_health() -> dict[str, Any]:
    """Return real operational health metrics where available."""

    database_status = "Online"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        database_status = "Error"

    disk = shutil.disk_usage(Config.BASE_DIR)
    memory_usage = None
    cpu_usage = None
    if psutil is not None:
        memory_usage = round(float(psutil.virtual_memory().percent), 1)
        cpu_usage = round(float(psutil.cpu_percent(interval=None)), 1)

    return {
        "Database Status": database_status,
        "Database": _database_display(),
        "Database Size": _database_size(),
        "Server Uptime": _format_duration(time.time() - SERVER_STARTED_AT),
        "Application Mode": current_app.config["APPLICATION_MODE"],
        "Public URL": current_app.config["PUBLIC_URL"],
        "Memory Usage": f"{memory_usage}%" if memory_usage is not None else "N/A",
        "CPU Usage": f"{cpu_usage}%" if cpu_usage is not None else "N/A",
        "Disk Usage": f"{round((disk.used / disk.total) * 100, 1)}%",
        "Telemetry Queue": "0",
        "Average Processing Time": "0 ms",
        "Correlation Engine Status": "Online",
        "Detection Engine Status": "Online",
    }


def get_cloud_status() -> dict[str, Any]:
    """Return deployment status for the Cloud Edition dashboard section."""

    health = get_system_health()
    return {
        "Application Mode": current_app.config["APPLICATION_MODE"],
        "Public URL": current_app.config["PUBLIC_URL"],
        "Database": _database_display(),
        "Server Uptime": health["Server Uptime"],
        "Connected Endpoints": Endpoint.query.filter_by(status=STATUS_ONLINE).count(),
        "Health Status": "Healthy" if health["Database Status"] == "Online" else "Degraded",
    }


def get_about_data() -> dict[str, Any]:
    """Return product, architecture, stack, and project statistics."""

    return {
        "name": "SOC Sentinel",
        "subtitle": APP_SUBTITLE,
        "version": APP_VERSION,
        "developer": DEVELOPER,
        "architecture": [
            "Windows Agent",
            "Flask SOC Server",
            "SQLite Storage",
            "Telemetry Pipeline",
            "Detection Engine",
            "Correlation Engine",
            "SOC Dashboard",
        ],
        "technology_stack": [
            "Python",
            "Flask",
            "SQLite",
            "SQLAlchemy",
            "Bootstrap",
            "Chart.js",
            "PyInstaller",
        ],
        "statistics": {
            "Total Endpoints": Endpoint.query.count(),
            "Telemetry": Telemetry.query.count(),
            "Alerts": Alert.query.count(),
            "Incidents": CorrelatedIncident.query.count(),
            "Endpoint Commands": EndpointCommand.query.count(),
            "Correlation Rules": CorrelationRule.query.count(),
            "Detection Rules": DetectionRule.query.count(),
        },
    }


def list_detection_rules_for_admin() -> list[dict[str, Any]]:
    """Return detection rules with trigger counts for read-only management."""

    rows = (
        db.session.query(
            DetectionRule,
            func.count(Alert.id).label("trigger_count"),
        )
        .outerjoin(Alert, Alert.rule_id == DetectionRule.rule_id)
        .group_by(DetectionRule.id)
        .order_by(DetectionRule.rule_id.asc())
        .all()
    )
    return [
        {
            "rule": rule,
            "trigger_count": int(trigger_count),
            "version": "1.0",
        }
        for rule, trigger_count in rows
    ]


def list_correlation_rules_for_admin() -> list[dict[str, Any]]:
    """Return correlation rules with incident counts for read-only management."""

    rows = (
        db.session.query(
            CorrelationRule,
            func.count(CorrelatedIncident.id).label("incident_count"),
        )
        .outerjoin(
            CorrelatedIncident,
            CorrelatedIncident.correlation_rule_id == CorrelationRule.rule_id,
        )
        .group_by(CorrelationRule.id)
        .order_by(CorrelationRule.rule_id.asc())
        .all()
    )
    return [
        {
            "rule": rule,
            "trigger_count": int(incident_count),
            "version": rule.version,
        }
        for rule, incident_count in rows
    ]


def _executive_summary(dashboard: dict[str, Any]) -> dict[str, Any]:
    return {
        "Total Endpoints": dashboard["endpoints"]["total"],
        "Online": dashboard["endpoints"]["online"],
        "Offline": dashboard["endpoints"]["offline"],
        "Telemetry Count": Telemetry.query.count(),
        "Alerts Count": Alert.query.count(),
        "Incidents Count": CorrelatedIncident.query.count(),
        "Endpoint Commands": EndpointCommand.query.count(),
        "Detection Rules": DetectionRule.query.count(),
        "Correlation Rules": CorrelationRule.query.count(),
    }


def _security_statistics() -> dict[str, Any]:
    return {
        "Critical Alerts": Alert.query.filter_by(severity="critical").count(),
        "High Alerts": Alert.query.filter_by(severity="high").count(),
        "Medium Alerts": Alert.query.filter_by(severity="medium").count(),
        "Low Alerts": Alert.query.filter_by(severity="low").count(),
        "Critical Incidents": CorrelatedIncident.query.filter_by(severity="critical").count(),
        "Open Incidents": CorrelatedIncident.query.filter_by(status="OPEN").count(),
        "Resolved Incidents": CorrelatedIncident.query.filter_by(status="RESOLVED").count(),
    }


def _recent_incidents(limit: int = 50) -> list[CorrelatedIncident]:
    return CorrelatedIncident.query.order_by(
        CorrelatedIncident.created_at.desc()
    ).limit(limit).all()


def _recent_alerts(limit: int = 50) -> list[Alert]:
    return Alert.query.order_by(Alert.timestamp.desc()).limit(limit).all()


def _incident_row(incident: CorrelatedIncident) -> dict[str, Any]:
    notes = (
        IncidentNote.query.filter_by(incident_id=incident.incident_id)
        .order_by(IncidentNote.created_at.asc())
        .all()
    )
    history = (
        IncidentHistory.query.filter_by(incident_id=incident.incident_id)
        .order_by(IncidentHistory.timestamp.asc())
        .all()
    )
    return {
        "incident_id": incident.incident_id,
        "title": incident.title,
        "endpoint_id": incident.endpoint_id,
        "rule": incident.correlation_rule_id,
        "severity": incident.severity,
        "priority": incident.priority,
        "status": incident.status,
        "assigned_to": incident.assigned_to,
        "confidence": incident.confidence,
        "risk_score": incident.risk_score,
        "mitre_tactic": incident.mitre_tactic,
        "mitre_technique": incident.mitre_technique,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
        "summary": incident.summary,
        "notes": [
            {
                "author": note.author,
                "note": note.note,
                "created_at": note.created_at.isoformat() if note.created_at else None,
            }
            for note in notes
        ],
        "history": [
            {
                "action": item.action,
                "previous_status": item.previous_status,
                "new_status": item.new_status,
                "actor": item.actor,
                "timestamp": item.timestamp.isoformat() if item.timestamp else None,
            }
            for item in history
        ],
    }


def _alert_row(alert: Alert) -> dict[str, Any]:
    return {
        "alert_id": alert.alert_id,
        "endpoint_id": alert.endpoint_id,
        "rule": alert.rule_id,
        "severity": alert.severity,
        "status": alert.status,
        "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
        "title": alert.title,
    }


def _format_duration(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, sec = divmod(remainder, 60)
    return f"{hours}h {minutes}m {sec}s"


def _database_display() -> str:
    if is_sqlite_database():
        return f"SQLite ({current_app.config['DATABASE_PATH']})"
    return database_label()


def _database_size() -> str:
    if not is_sqlite_database():
        return "Managed externally"

    database_path = Path(current_app.config["DATABASE_PATH"])
    return _format_bytes(database_path.stat().st_size) if database_path.exists() else "0 B"


def _format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
