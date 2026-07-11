# Changelog

All notable changes to SOC Sentinel are documented in this file.

## v0.9.0 - Cloud Edition

- Added environment-based configuration for development and production.
- Added support for localhost, LAN, and public cloud deployments through configuration.
- Added health API with application status, version, database connectivity, uptime, and mode.
- Added optional PostgreSQL support while preserving SQLite compatibility.
- Added production deployment guidance for Waitress, Gunicorn, Nginx, and Oracle Cloud.
- Added structured application, access, and error logging guidance.
- Added SQLite database backup action and PostgreSQL backup guidance.
- Added cloud status information to the dashboard.

## v0.8.0 - Endpoint Response Framework

- Added endpoint command queue and command lifecycle tracking.
- Added command polling support for the Windows agent.
- Added safe response actions such as diagnostics, log download, heartbeat, telemetry sync, and restart placeholder behavior.
- Added endpoint response UI and command history.

## v0.7.0 - Incident Response and Investigation

- Added incident notes and incident history models.
- Added assignment, priority, status transitions, resolution, closure, false-positive handling, and reopen workflow.
- Added investigation workspace with evidence, timeline, matched alerts, related telemetry, notes, and history.
- Added incident export support for investigation records.

## v0.6.3 - SOC Intelligence Center

- Reworked the homepage into a SOC command center.
- Added cached dashboard statistics through DashboardService.
- Added live refresh API for endpoint, telemetry, alert, incident, MITRE, rule, and system health data.
- Added Chart.js-ready attack timeline and operational health sections.

## v0.6.2 - Stateful Correlation Rules

- Added in-memory per-endpoint correlation context.
- Added alert-sequence correlation rules.
- Added duplicate suppression with configurable cooldown.
- Added correlated incident generation with confidence, risk score, matched alerts, evidence, and timeline.

## v0.6.1 - Correlation Foundation

- Added correlation engine structure and incident data flow.
- Added correlation rule registry and service boundaries.

## v0.5.5 - Endpoint Identity Enhancement

- Added hardware-based device fingerprint generation in the agent.
- Added endpoint identity status tracking on the server.
- Added audit logging for fingerprint changes.
- Added endpoint detail visibility for device fingerprint and identity status.

## v0.5.0 - Detection Engine

- Added detection rule and alert models.
- Added modular detection engine.
- Added rules for failed logins, PowerShell execution, ransomware-like file deletion, suspicious process names, and process spikes.
- Added AlertService and duplicate alert handling.
- Added alert list and alert detail dashboard pages.

## v0.4.0 - Telemetry Collection Engine

- Added telemetry model, service, and API.
- Added process collector for newly started processes.
- Added Documents folder file activity collector.
- Added Windows Security Event Log collector for selected event types.
- Added shared telemetry event class and queue-based telemetry sender.
- Added telemetry dashboard page.

## v0.3.0 - Windows Agent

- Added standalone Windows agent structure.
- Added automatic registration, heartbeat loop, system information collection, and structured logging.
- Added retry and exponential backoff behavior.
- Added placeholder collector modules.
- Added PyInstaller build preparation.

## v0.2.0 - Endpoint Registration and Management

- Added endpoint model with endpoint ID, hostname, OS, IP, MAC, agent version, API key, status, registration time, and last seen.
- Added endpoint registration and heartbeat APIs.
- Added endpoint listing and endpoint details dashboard pages.
- Added endpoint service layer.

## v0.1.0 - Foundation

- Added Flask application factory.
- Added SQLite and SQLAlchemy setup.
- Added automatic database creation on startup.
- Added dark Bootstrap dashboard foundation.
- Added project structure for server, agent, docs, screenshots, templates, static assets, and database files.
