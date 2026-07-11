from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from urllib.parse import urlencode

from correlation.services.correlation_service import (
    get_correlated_incident,
    get_correlation_rule,
    get_matched_alerts,
    list_correlation_rules,
)
from models import Alert, CorrelatedIncident, DetectionRule, Telemetry, utc_now
from services import platform_service
from services.backup_service import create_sqlite_backup
from services.alert_service import (
    get_alert,
    get_alert_rule,
    get_related_telemetry,
)
from services.endpoint_service import (
    get_endpoint,
    list_endpoints,
    mark_expired_endpoints_offline,
)
from services.command_service import (
    COMMAND_STATUSES,
    SAFE_COMMANDS,
    get_endpoint_command_context,
    list_commands,
    queue_command,
)
from services.incident_service import (
    INCIDENT_PRIORITIES,
    INCIDENT_STATUSES,
    add_note,
    assign_incident,
    change_priority,
    change_status,
    close_incident,
    delete_note,
    edit_note,
    list_history,
    list_notes,
    mark_false_positive,
    reopen_incident,
    resolve_incident,
)
from services.report_service import build_csv_report, build_json_report, build_pdf_report
from services.settings_service import (
    list_settings_grouped,
    reset_settings,
    update_settings,
)


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Render the SOC Intelligence Center."""

    mark_expired_endpoints_offline(
        current_app.config["ENDPOINT_HEARTBEAT_TIMEOUT_SECONDS"]
    )
    return render_template("dashboard.html")


@dashboard_bp.route("/endpoints")
def endpoints():
    """Render endpoint inventory with optional status filtering."""

    mark_expired_endpoints_offline(
        current_app.config["ENDPOINT_HEARTBEAT_TIMEOUT_SECONDS"]
    )
    status = request.args.get("status", "").strip().lower()
    endpoints_list = list_endpoints()
    if status:
        endpoints_list = [
            endpoint
            for endpoint in endpoints_list
            if endpoint.status.lower() == status
        ]
    command_context = {
        endpoint.endpoint_id: get_endpoint_command_context(endpoint.endpoint_id)
        for endpoint in endpoints_list
    }
    telemetry_context = {
        endpoint.endpoint_id: _last_telemetry(endpoint.endpoint_id)
        for endpoint in endpoints_list
    }
    return render_template(
        "endpoints.html",
        endpoints=endpoints_list,
        status=status,
        command_context=command_context,
        telemetry_context=telemetry_context,
    )


@dashboard_bp.route("/endpoints/<endpoint_id>")
def endpoint_details(endpoint_id: str):
    """Render endpoint investigation details."""

    mark_expired_endpoints_offline(
        current_app.config["ENDPOINT_HEARTBEAT_TIMEOUT_SECONDS"]
    )
    endpoint = get_endpoint(endpoint_id)
    status_code = 200 if endpoint is not None else 404
    telemetry_rows = _recent_telemetry(endpoint_id) if endpoint else []
    alert_rows = _recent_alerts(endpoint_id) if endpoint else []
    incident_rows = _recent_incidents(endpoint_id) if endpoint else []
    command_rows = list_commands(endpoint_id=endpoint_id, limit=25) if endpoint else []

    return (
        render_template(
            "endpoint_details.html",
            endpoint=endpoint,
            telemetry=telemetry_rows,
            alerts=alert_rows,
            incidents=incident_rows,
            telemetry_count=Telemetry.query.filter_by(endpoint_id=endpoint_id).count()
            if endpoint
            else 0,
            alert_count=Alert.query.filter_by(endpoint_id=endpoint_id).count()
            if endpoint
            else 0,
            incident_count=CorrelatedIncident.query.filter_by(endpoint_id=endpoint_id).count()
            if endpoint
            else 0,
            commands=command_rows,
            safe_commands=SAFE_COMMANDS,
        ),
        status_code,
    )


@dashboard_bp.route("/response")
def response_center():
    """Render endpoint response command queue and history."""

    filters = {
        "endpoint": request.args.get("endpoint", "").strip(),
        "status": request.args.get("status", "").strip().upper(),
    }
    commands = list_commands(
        endpoint_id=filters["endpoint"],
        status=filters["status"],
    )
    return render_template(
        "response.html",
        endpoints=list_endpoints(),
        commands=commands,
        filters=filters,
        statuses=COMMAND_STATUSES,
        safe_commands=SAFE_COMMANDS,
    )


@dashboard_bp.post("/response/commands")
def create_response_command():
    """Queue a safe endpoint response command from the dashboard."""

    result = queue_command(
        endpoint_id=request.form.get("endpoint_id", ""),
        command_type=request.form.get("command_type", ""),
        requested_by=request.form.get("requested_by", "Analyst"),
    )
    flash(result.message, "success" if result.success else "danger")
    endpoint_id = request.form.get("endpoint_id", "")
    query = urlencode({"endpoint": endpoint_id}) if endpoint_id else ""
    target = url_for("dashboard.response_center")
    return redirect(f"{target}?{query}" if query else target)


@dashboard_bp.route("/telemetry")
def telemetry():
    """Render filterable telemetry investigation table."""

    filters = {
        "endpoint": request.args.get("endpoint", "").strip(),
        "collector": request.args.get("collector", "").strip().lower(),
        "severity": request.args.get("severity", "").strip().lower(),
        "event_type": request.args.get("event_type", "").strip().lower(),
        "date": request.args.get("date", "").strip().lower(),
        "search": request.args.get("search", "").strip(),
    }
    return render_template(
        "telemetry.html",
        events=_filter_telemetry(filters),
        filters=filters,
        selected_id=request.args.get("telemetry_id", "").strip(),
    )


@dashboard_bp.route("/alerts")
def alerts():
    """Render filterable alerts."""

    filters = {
        "severity": request.args.get("severity", "").strip().lower(),
        "rule": request.args.get("rule", "").strip(),
        "endpoint": request.args.get("endpoint", "").strip(),
        "mitre": request.args.get("mitre", "").strip(),
        "status": request.args.get("status", "").strip(),
        "date": request.args.get("date", "").strip().lower(),
    }
    return render_template("alerts.html", alerts=_filter_alerts(filters), filters=filters)


@dashboard_bp.route("/alerts/<alert_id>")
def alert_details(alert_id: str):
    """Render alert investigation details."""

    alert = get_alert(alert_id)
    rule = get_alert_rule(alert) if alert is not None else None
    telemetry_rows = get_related_telemetry(alert) if alert is not None else []
    related_incident = _find_incident_for_alert(alert) if alert is not None else None
    status_code = 200 if alert is not None else 404
    return (
        render_template(
            "alert_details.html",
            alert=alert,
            rule=rule,
            telemetry=telemetry_rows,
            related_incident=related_incident,
        ),
        status_code,
    )


@dashboard_bp.route("/incidents")
def incidents():
    """Render filterable correlated incidents."""

    filters = {
        "severity": request.args.get("severity", "").strip().lower(),
        "endpoint": request.args.get("endpoint", "").strip(),
        "rule": request.args.get("rule", "").strip(),
        "mitre": request.args.get("mitre", "").strip(),
        "status": request.args.get("status", "").strip(),
        "date": request.args.get("date", "").strip().lower(),
    }
    return render_template(
        "incidents.html",
        incidents=_filter_incidents(filters),
        filters=filters,
    )


@dashboard_bp.route("/incidents/<incident_id>")
def incident_details(incident_id: str):
    """Render correlated incident details."""

    incident = get_correlated_incident(incident_id)
    rule = (
        get_correlation_rule(incident.correlation_rule_id)
        if incident is not None
        else None
    )
    matched_alerts = get_matched_alerts(incident) if incident is not None else []
    related_telemetry = []
    for alert in matched_alerts:
        related_telemetry.extend(get_related_telemetry(alert, limit=5))
    status_code = 200 if incident is not None else 404
    return (
        render_template(
            "incident_details.html",
            incident=incident,
            rule=rule,
            matched_alerts=matched_alerts,
            related_telemetry=related_telemetry[:20],
            notes=list_notes(incident_id) if incident is not None else [],
            history=list_history(incident_id) if incident is not None else [],
            statuses=INCIDENT_STATUSES,
            priorities=INCIDENT_PRIORITIES,
        ),
        status_code,
    )


@dashboard_bp.post("/incidents/<incident_id>/action")
def update_incident_action(incident_id: str):
    """Apply an incident workflow action through the service layer."""

    action = request.form.get("action", "").strip()
    actor = request.form.get("actor", "Analyst")

    if action == "assign":
        result = assign_incident(
            incident_id,
            request.form.get("assigned_to", ""),
            actor,
        )
    elif action == "status":
        result = change_status(incident_id, request.form.get("status", ""), actor)
    elif action == "priority":
        result = change_priority(incident_id, request.form.get("priority", ""), actor)
    elif action == "false_positive":
        result = mark_false_positive(incident_id, actor)
    elif action == "resolve":
        result = resolve_incident(incident_id, actor)
    elif action == "close":
        result = close_incident(incident_id, actor)
    elif action == "reopen":
        result = reopen_incident(incident_id, actor)
    else:
        flash("Unsupported incident action.", "danger")
        return redirect(url_for("dashboard.incident_details", incident_id=incident_id))

    flash(result.message, "success" if result.success else "danger")
    return redirect(url_for("dashboard.incident_details", incident_id=incident_id))


@dashboard_bp.post("/incidents/<incident_id>/notes")
def create_incident_note(incident_id: str):
    """Add a note to an incident investigation."""

    result = add_note(
        incident_id,
        request.form.get("author", "Analyst"),
        request.form.get("note", ""),
    )
    flash(result.message, "success" if result.success else "danger")
    return redirect(url_for("dashboard.incident_details", incident_id=incident_id))


@dashboard_bp.post("/incidents/<incident_id>/notes/<int:note_id>/edit")
def update_incident_note(incident_id: str, note_id: int):
    """Edit an incident investigation note."""

    result = edit_note(
        incident_id,
        note_id,
        request.form.get("author", "Analyst"),
        request.form.get("note", ""),
    )
    flash(result.message, "success" if result.success else "danger")
    return redirect(url_for("dashboard.incident_details", incident_id=incident_id))


@dashboard_bp.post("/incidents/<incident_id>/notes/<int:note_id>/delete")
def remove_incident_note(incident_id: str, note_id: int):
    """Delete an incident investigation note."""

    result = delete_note(
        incident_id,
        note_id,
        request.form.get("actor", "Analyst"),
    )
    flash(result.message, "success" if result.success else "danger")
    return redirect(url_for("dashboard.incident_details", incident_id=incident_id))


@dashboard_bp.route("/correlation-rules")
def correlation_rules():
    """Render read-only correlation rule metadata."""

    return render_template(
        "rule_catalog.html",
        page_title="Correlation Rules",
        icon="bi-diagram-3",
        rules=platform_service.list_correlation_rules_for_admin(),
        count_label="Incident Count",
        kind="correlation",
    )


@dashboard_bp.route("/detection-rules")
def detection_rules():
    """Render read-only detection rule metadata."""

    return render_template(
        "rule_catalog.html",
        page_title="Detection Rules",
        icon="bi-bullseye",
        rules=platform_service.list_detection_rules_for_admin(),
        count_label="Trigger Count",
        kind="detection",
    )


@dashboard_bp.route("/reports")
def reports():
    """Render the reporting dashboard."""

    return render_template("reports.html", report=platform_service.get_report_data())


@dashboard_bp.route("/reports/export/<format_name>")
def export_report(format_name: str):
    """Export reports as PDF, CSV, or JSON."""

    data = platform_service.get_report_data()
    filename = f"soc-sentinel-report-{data['timestamp'][:10]}"

    if format_name == "json":
        return Response(
            build_json_report(data),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )

    if format_name == "csv":
        return Response(
            build_csv_report(data),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )

    if format_name == "pdf":
        return Response(
            build_pdf_report(data),
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
        )

    return render_template("error.html", code=404, title="Export Not Found"), 404


@dashboard_bp.route("/settings")
def settings():
    """Render editable administration settings."""

    return render_template(
        "settings.html",
        settings=list_settings_grouped(),
        system=platform_service.get_settings_data()["system_information"],
    )


@dashboard_bp.post("/settings")
def save_settings():
    """Persist editable administration settings."""

    if request.form.get("action") == "reset":
        reset_settings()
        flash("Settings reset to defaults.", "success")
        return redirect(url_for("dashboard.settings"))

    success, message = update_settings(request.form.to_dict())
    flash(message, "success" if success else "danger")
    return redirect(url_for("dashboard.settings"))


@dashboard_bp.route("/system-health")
def system_health():
    """Render platform health."""

    return render_template(
        "system_health.html",
        health=platform_service.get_system_health(),
        cloud=platform_service.get_cloud_status(),
    )


@dashboard_bp.post("/system-health/backup")
def backup_database():
    """Create and download a SQLite backup when supported."""

    result = create_sqlite_backup()
    if not result.success or result.path is None:
        flash(result.message, "warning")
        return redirect(url_for("dashboard.system_health"))

    return send_file(
        result.path,
        as_attachment=True,
        download_name=result.path.name,
        mimetype="application/octet-stream",
    )


@dashboard_bp.route("/about")
def about():
    """Render product information."""

    return render_template("about.html", about=platform_service.get_about_data())


def _recent_telemetry(endpoint_id: str) -> list[Telemetry]:
    return (
        Telemetry.query.filter_by(endpoint_id=endpoint_id)
        .order_by(Telemetry.timestamp.desc())
        .limit(10)
        .all()
    )


def _last_telemetry(endpoint_id: str) -> Telemetry | None:
    return (
        Telemetry.query.filter_by(endpoint_id=endpoint_id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )


def _recent_alerts(endpoint_id: str) -> list[Alert]:
    return (
        Alert.query.filter_by(endpoint_id=endpoint_id)
        .order_by(Alert.timestamp.desc())
        .limit(10)
        .all()
    )


def _recent_incidents(endpoint_id: str) -> list[CorrelatedIncident]:
    return (
        CorrelatedIncident.query.filter_by(endpoint_id=endpoint_id)
        .order_by(CorrelatedIncident.created_at.desc())
        .limit(10)
        .all()
    )


def _filter_telemetry(filters: dict[str, str]) -> list[Telemetry]:
    query = Telemetry.query
    if filters["endpoint"]:
        query = query.filter(Telemetry.endpoint_id == filters["endpoint"])
    if filters["collector"]:
        query = query.filter(Telemetry.collector == filters["collector"])
    if filters["severity"]:
        query = query.filter(Telemetry.severity == filters["severity"])
    if filters["event_type"]:
        query = query.filter(Telemetry.event_type == filters["event_type"])
    if filters["date"] == "today":
        query = query.filter(Telemetry.timestamp >= _today_start())
    if filters["search"]:
        like = f"%{filters['search']}%"
        query = query.filter(
            (Telemetry.endpoint_id.ilike(like))
            | (Telemetry.collector.ilike(like))
            | (Telemetry.event_type.ilike(like))
            | (Telemetry.severity.ilike(like))
        )
    return query.order_by(Telemetry.timestamp.desc()).limit(1000).all()


def _filter_alerts(filters: dict[str, str]) -> list[Alert]:
    query = Alert.query
    if filters["severity"]:
        query = query.filter(Alert.severity == filters["severity"])
    if filters["rule"]:
        query = query.filter(Alert.rule_id == filters["rule"])
    if filters["endpoint"]:
        query = query.filter(Alert.endpoint_id == filters["endpoint"])
    if filters["status"]:
        query = query.filter(Alert.status == filters["status"])
    if filters["date"] == "today":
        query = query.filter(Alert.timestamp >= _today_start())
    if filters["mitre"]:
        like = f"%{filters['mitre']}%"
        query = query.join(DetectionRule, DetectionRule.rule_id == Alert.rule_id).filter(
            (DetectionRule.mitre_tactic.ilike(like))
            | (DetectionRule.mitre_technique.ilike(like))
        )
    return query.order_by(Alert.timestamp.desc()).limit(1000).all()


def _filter_incidents(filters: dict[str, str]) -> list[CorrelatedIncident]:
    query = CorrelatedIncident.query
    if filters["severity"]:
        query = query.filter(CorrelatedIncident.severity == filters["severity"])
    if filters["endpoint"]:
        query = query.filter(CorrelatedIncident.endpoint_id == filters["endpoint"])
    if filters["rule"]:
        query = query.filter(CorrelatedIncident.correlation_rule_id == filters["rule"])
    if filters["status"]:
        query = query.filter(CorrelatedIncident.status == filters["status"])
    if filters["date"] == "today":
        date_column = (
            CorrelatedIncident.resolved_at
            if filters["status"] == "RESOLVED"
            else CorrelatedIncident.created_at
        )
        query = query.filter(date_column >= _today_start())
    if filters["mitre"]:
        like = f"%{filters['mitre']}%"
        query = query.filter(
            (CorrelatedIncident.mitre_tactic.ilike(like))
            | (CorrelatedIncident.mitre_technique.ilike(like))
        )
    return query.order_by(CorrelatedIncident.created_at.desc()).limit(1000).all()


def _today_start():
    now = utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _find_incident_for_alert(alert: Alert) -> CorrelatedIncident | None:
    """Return the newest incident referencing an alert."""

    incidents = CorrelatedIncident.query.order_by(
        CorrelatedIncident.created_at.desc()
    ).limit(200).all()
    return next(
        (
            incident
            for incident in incidents
            if alert.alert_id in (incident.matched_alert_ids or [])
        ),
        None,
    )
