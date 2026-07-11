import csv
import io
import json
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_json_report(data: dict[str, Any]) -> str:
    """Serialize report data as stable JSON."""

    return json.dumps(data, indent=2, sort_keys=True)


def build_csv_report(data: dict[str, Any]) -> str:
    """Serialize report sections as standards-compliant CSV."""

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Section", "Key", "Value"])

    for section in ["executive_summary", "security_statistics"]:
        for key, value in data[section].items():
            writer.writerow([section, key, value])

    writer.writerow([])
    writer.writerow(["Top Endpoints", "Hostname", "Telemetry", "Alerts", "Incidents"])
    for row in data["top_endpoints"]:
        writer.writerow(
            [
                "Top Endpoints",
                row.get("hostname"),
                row.get("telemetry"),
                row.get("alerts"),
                row.get("incidents"),
            ]
        )

    writer.writerow([])
    writer.writerow(["Top Detection Rules", "Rule", "Triggered"])
    for row in data["top_detection_rules"]:
        writer.writerow(["Top Detection Rules", row.get("name"), row.get("triggered")])

    writer.writerow([])
    writer.writerow(["Top Correlation Rules", "Rule", "Incidents"])
    for row in data["top_correlation_rules"]:
        writer.writerow(["Top Correlation Rules", row.get("name"), row.get("incidents")])

    writer.writerow([])
    writer.writerow(["MITRE Summary", "Tactic", "Count"])
    for row in data["mitre_summary"]:
        writer.writerow(["MITRE Summary", row.get("tactic"), row.get("count")])

    writer.writerow([])
    writer.writerow(
        [
            "Incident Investigations",
            "Incident",
            "Title",
            "Status",
            "Priority",
            "Assigned To",
            "Notes",
            "History",
        ]
    )
    for incident in data.get("incidents", []):
        writer.writerow(
            [
                "Incident Investigations",
                incident.get("incident_id"),
                incident.get("title"),
                incident.get("status"),
                incident.get("priority"),
                incident.get("assigned_to") or "Unassigned",
                _join_notes(incident.get("notes", [])),
                _join_history(incident.get("history", [])),
            ]
        )

    return output.getvalue()


def build_pdf_report(data: dict[str, Any]) -> bytes:
    """Build a professional PDF report using ReportLab."""

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("SOC Sentinel Security Report", styles["Title"]),
        Paragraph(data["subtitle"], styles["Normal"]),
        Paragraph(f"Generated: {data['timestamp']}", styles["Normal"]),
        Paragraph(f"Version: {data['version']}", styles["Normal"]),
        Spacer(1, 14),
    ]

    _append_key_value_table(story, "Executive Summary", data["executive_summary"])
    _append_key_value_table(story, "Security Statistics", data["security_statistics"])
    _append_rows_table(
        story,
        "Top Endpoints",
        ["Hostname", "Telemetry", "Alerts", "Incidents"],
        [
            [
                row.get("hostname"),
                row.get("telemetry"),
                row.get("alerts"),
                row.get("incidents"),
            ]
            for row in data["top_endpoints"]
        ],
    )
    _append_rows_table(
        story,
        "Top Detection Rules",
        ["Rule", "Triggered"],
        [[row.get("name"), row.get("triggered")] for row in data["top_detection_rules"]],
    )
    _append_rows_table(
        story,
        "Top Correlation Rules",
        ["Rule", "Incidents"],
        [[row.get("name"), row.get("incidents")] for row in data["top_correlation_rules"]],
    )
    _append_rows_table(
        story,
        "MITRE Summary",
        ["Tactic", "Count"],
        [[row.get("tactic"), row.get("count")] for row in data["mitre_summary"]],
    )
    _append_rows_table(
        story,
        "Incident Investigations",
        ["Incident", "Status", "Priority", "Assigned", "Notes", "History"],
        [
            [
                incident.get("incident_id"),
                incident.get("status"),
                incident.get("priority"),
                incident.get("assigned_to") or "Unassigned",
                _join_notes(incident.get("notes", [])),
                _join_history(incident.get("history", [])),
            ]
            for incident in data.get("incidents", [])
        ],
    )

    document.build(story)
    buffer.seek(0)
    return buffer.read()


def _append_key_value_table(story: list, title: str, rows: dict[str, Any]) -> None:
    story.append(Paragraph(title, getSampleStyleSheet()["Heading2"]))
    table = Table([["Metric", "Value"], *[[key, value] for key, value in rows.items()]])
    _style_table(table)
    story.extend([table, Spacer(1, 12)])


def _append_rows_table(
    story: list,
    title: str,
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    story.append(Paragraph(title, getSampleStyleSheet()["Heading2"]))
    empty_row = ["No data", *["" for _ in headers[1:]]]
    table = Table([headers, *(rows or [empty_row])])
    _style_table(table)
    story.extend([table, Spacer(1, 12)])


def _style_table(table: Table) -> None:
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )


def _join_notes(notes: list[dict[str, Any]]) -> str:
    """Return compact note text for tabular exports."""

    if not notes:
        return "No notes"
    return " | ".join(
        f"{note.get('created_at') or 'Unknown'} {note.get('author')}: {note.get('note')}"
        for note in notes
    )


def _join_history(history: list[dict[str, Any]]) -> str:
    """Return compact history text for tabular exports."""

    if not history:
        return "No history"
    return " | ".join(
        f"{item.get('timestamp') or 'Unknown'} {item.get('actor')}: {item.get('action')}"
        for item in history
    )
