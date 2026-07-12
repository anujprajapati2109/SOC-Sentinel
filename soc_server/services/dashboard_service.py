import time
from datetime import datetime, timedelta, timezone
import platform
from threading import RLock
from typing import Any

from flask import current_app
from sqlalchemy import func, text

from correlation.services.correlation_service import list_correlated_incidents
from models import (
    Alert,
    CorrelatedIncident,
    CorrelationRule,
    DetectionRule,
    Endpoint,
    Telemetry,
    db,
    utc_now,
)
from utils.constants import STATUS_OFFLINE, STATUS_ONLINE
from utils.deployment_status import (
    effective_public_url,
    gunicorn_status,
    hostname,
    process_status,
    server_ip,
)


try:
    import psutil
except ImportError:  # pragma: no cover - optional runtime dependency.
    psutil = None


DASHBOARD_STARTED_AT = time.time()


class DashboardService:
    """Aggregates SOC dashboard statistics with short-lived caching."""

    def __init__(self, cache_ttl_seconds: int = 5) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, Any] | None = None
        self._cache_time = 0.0
        self._lock = RLock()

    def get_dashboard(self) -> dict[str, Any]:
        """Return cached dashboard data or rebuild it when stale."""

        with self._lock:
            now = time.monotonic()
            if self._cache and now - self._cache_time < self.cache_ttl_seconds:
                return self._cache

            data = self._build_dashboard()
            self._cache = data
            self._cache_time = now
            return data

    def _build_dashboard(self) -> dict[str, Any]:
        """Build all dashboard sections from lightweight aggregate queries."""

        now = utc_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        one_minute_ago = now - timedelta(seconds=60)

        return {
            "generated_at": now.isoformat(),
            "endpoints": self._endpoint_stats(today_start),
            "telemetry": self._telemetry_stats(today_start, one_minute_ago),
            "alerts": self._alert_stats(today_start, one_minute_ago),
            "incidents": self._incident_stats(today_start, one_minute_ago),
            "mitre": self._mitre_stats(),
            "detection_rules": self._detection_rule_stats(),
            "correlation_rules": self._correlation_rule_stats(),
            "top_endpoints": self._top_endpoints(),
            "endpoint_health": self._endpoint_health(today_start),
            "attack_timeline": self._attack_timeline(now),
            "system_health": self._system_health(),
            "cloud_status": self._cloud_status(),
        }

    def _endpoint_stats(self, today_start: datetime) -> dict[str, int]:
        """Return endpoint totals and online state."""

        online = Endpoint.query.filter_by(status=STATUS_ONLINE).count()
        offline = Endpoint.query.filter_by(status=STATUS_OFFLINE).count()
        total = Endpoint.query.count()
        unknown = max(total - online - offline, 0)
        return {
            "total": total,
            "online": online,
            "offline": offline + unknown,
        }

    def _telemetry_stats(
        self,
        today_start: datetime,
        one_minute_ago: datetime,
    ) -> dict[str, Any]:
        """Return telemetry counts and intake rate."""

        today_count = Telemetry.query.filter(Telemetry.timestamp >= today_start).count()
        last_minute = Telemetry.query.filter(
            Telemetry.timestamp >= one_minute_ago
        ).count()
        return {
            "today": today_count,
            "per_second": round(last_minute / 60, 2),
            "queue_size": 0,
        }

    def _alert_stats(
        self,
        today_start: datetime,
        one_minute_ago: datetime,
    ) -> dict[str, Any]:
        """Return alert counts and rate."""

        today_count = Alert.query.filter(Alert.timestamp >= today_start).count()
        last_minute = Alert.query.filter(Alert.timestamp >= one_minute_ago).count()
        return {
            "today": today_count,
            "per_second": round(last_minute / 60, 2),
            "open": Alert.query.filter_by(status="Open").count(),
            "critical": Alert.query.filter_by(severity="critical").count(),
        }

    def _incident_stats(
        self,
        today_start: datetime,
        one_minute_ago: datetime,
    ) -> dict[str, Any]:
        """Return correlated incident counts and rate."""

        today_count = CorrelatedIncident.query.filter(
            CorrelatedIncident.created_at >= today_start
        ).count()
        critical = CorrelatedIncident.query.filter_by(
            severity="critical",
            status="OPEN",
        ).count()
        resolved_today = CorrelatedIncident.query.filter(
            CorrelatedIncident.status == "RESOLVED",
            CorrelatedIncident.resolved_at >= today_start,
        ).count()
        last_minute = CorrelatedIncident.query.filter(
            CorrelatedIncident.created_at >= one_minute_ago
        ).count()
        return {
            "today": today_count,
            "critical": critical,
            "per_second": round(last_minute / 60, 2),
            "total": CorrelatedIncident.query.count(),
            "open": CorrelatedIncident.query.filter_by(status="OPEN").count(),
            "assigned": CorrelatedIncident.query.filter_by(status="ASSIGNED").count(),
            "investigating": CorrelatedIncident.query.filter_by(
                status="INVESTIGATING"
            ).count(),
            "resolved_today": resolved_today,
            "false_positives": CorrelatedIncident.query.filter_by(
                status="FALSE_POSITIVE"
            ).count(),
        }

    def _mitre_stats(self) -> list[dict[str, Any]]:
        """Return MITRE tactic distribution from rules that produced outcomes."""

        alert_rows = (
            db.session.query(DetectionRule.mitre_tactic, func.count(Alert.id))
            .join(Alert, Alert.rule_id == DetectionRule.rule_id)
            .group_by(DetectionRule.mitre_tactic)
            .all()
        )
        incident_rows = (
            db.session.query(CorrelatedIncident.mitre_tactic, func.count(CorrelatedIncident.id))
            .group_by(CorrelatedIncident.mitre_tactic)
            .all()
        )

        totals: dict[str, int] = {}
        for tactic, count in [*alert_rows, *incident_rows]:
            label = tactic or "Unmapped"
            totals[label] = totals.get(label, 0) + int(count)

        if not totals:
            for tactic in [
                "Execution",
                "Persistence",
                "Discovery",
                "Credential Access",
                "Impact",
                "Collection",
            ]:
                totals[tactic] = 0

        return [
            {"tactic": tactic, "count": count}
            for tactic, count in sorted(totals.items(), key=lambda item: item[0])
        ]

    def _detection_rule_stats(self) -> list[dict[str, Any]]:
        """Return top detection rules by alert count."""

        rows = (
            db.session.query(
                DetectionRule.rule_id,
                DetectionRule.name,
                func.count(Alert.id).label("triggered"),
            )
            .outerjoin(Alert, Alert.rule_id == DetectionRule.rule_id)
            .group_by(DetectionRule.rule_id, DetectionRule.name)
            .order_by(func.count(Alert.id).desc(), DetectionRule.rule_id.asc())
            .limit(10)
            .all()
        )
        return [
            {
                "rule_id": rule_id,
                "name": name,
                "triggered": int(triggered),
                "suppressed": 0,
                "average_evaluation_time_ms": 0,
            }
            for rule_id, name, triggered in rows
        ]

    def _correlation_rule_stats(self) -> list[dict[str, Any]]:
        """Return top correlation rules by incident count."""

        rows = (
            db.session.query(
                CorrelationRule.rule_id,
                CorrelationRule.name,
                func.count(CorrelatedIncident.id).label("incidents"),
            )
            .outerjoin(
                CorrelatedIncident,
                CorrelatedIncident.correlation_rule_id == CorrelationRule.rule_id,
            )
            .group_by(CorrelationRule.rule_id, CorrelationRule.name)
            .order_by(func.count(CorrelatedIncident.id).desc(), CorrelationRule.rule_id.asc())
            .limit(10)
            .all()
        )
        return [
            {
                "rule_id": rule_id,
                "name": name,
                "incidents": int(incidents),
                "average_correlation_time_ms": 0,
            }
            for rule_id, name, incidents in rows
        ]

    def _top_endpoints(self) -> list[dict[str, Any]]:
        """Return endpoints ranked by telemetry volume."""

        telemetry_counts = dict(
            db.session.query(Telemetry.endpoint_id, func.count(Telemetry.id))
            .group_by(Telemetry.endpoint_id)
            .all()
        )
        alert_counts = dict(
            db.session.query(Alert.endpoint_id, func.count(Alert.id))
            .group_by(Alert.endpoint_id)
            .all()
        )
        incident_counts = dict(
            db.session.query(
                CorrelatedIncident.endpoint_id,
                func.count(CorrelatedIncident.id),
            )
            .group_by(CorrelatedIncident.endpoint_id)
            .all()
        )

        endpoints = Endpoint.query.all()
        rows = [
            {
                "endpoint_id": endpoint.endpoint_id,
                "hostname": endpoint.hostname,
                "telemetry": int(telemetry_counts.get(endpoint.endpoint_id, 0)),
                "alerts": int(alert_counts.get(endpoint.endpoint_id, 0)),
                "incidents": int(incident_counts.get(endpoint.endpoint_id, 0)),
            }
            for endpoint in endpoints
        ]
        return sorted(rows, key=lambda row: row["telemetry"], reverse=True)[:10]

    def _endpoint_health(self, today_start: datetime) -> list[dict[str, Any]]:
        """Return endpoint status and telemetry count for the health table."""

        telemetry_today = dict(
            db.session.query(Telemetry.endpoint_id, func.count(Telemetry.id))
            .filter(Telemetry.timestamp >= today_start)
            .group_by(Telemetry.endpoint_id)
            .all()
        )
        return [
            {
                "endpoint_id": endpoint.endpoint_id,
                "hostname": endpoint.hostname,
                "status": endpoint.status,
                "cpu": None,
                "ram": None,
                "telemetry_count": int(telemetry_today.get(endpoint.endpoint_id, 0)),
                "last_heartbeat": endpoint.last_seen.isoformat()
                if endpoint.last_seen
                else None,
            }
            for endpoint in Endpoint.query.order_by(Endpoint.last_seen.desc().nullslast()).limit(10)
        ]

    def _attack_timeline(self, now: datetime) -> dict[str, Any]:
        """Return timeline series for chart ranges."""

        return {
            "last_hour": self._timeline_series(now, hours=1, bucket_minutes=5),
            "24_hours": self._timeline_series(now, hours=24, bucket_minutes=60),
            "7_days": self._timeline_series(now, hours=24 * 7, bucket_minutes=24 * 60),
        }

    def _timeline_series(
        self,
        now: datetime,
        hours: int,
        bucket_minutes: int,
    ) -> dict[str, list[Any]]:
        """Build telemetry, alert, and incident counts for a chart range."""

        start = now - timedelta(hours=hours)
        buckets = []
        cursor = start
        while cursor <= now:
            buckets.append(cursor)
            cursor += timedelta(minutes=bucket_minutes)

        return {
            "labels": [self._format_bucket(bucket, hours) for bucket in buckets],
            "telemetry": self._bucket_counts(Telemetry, Telemetry.timestamp, buckets, now),
            "alerts": self._bucket_counts(Alert, Alert.timestamp, buckets, now),
            "incidents": self._bucket_counts(
                CorrelatedIncident,
                CorrelatedIncident.created_at,
                buckets,
                now,
            ),
        }

    def _bucket_counts(self, model, column, buckets: list[datetime], now: datetime) -> list[int]:
        """Count model rows in each time bucket."""

        counts = []
        for index, bucket_start in enumerate(buckets):
            bucket_end = buckets[index + 1] if index + 1 < len(buckets) else now
            counts.append(
                model.query.filter(column >= bucket_start, column < bucket_end).count()
            )
        return counts

    def _format_bucket(self, bucket: datetime, hours: int) -> str:
        """Format a bucket label for the selected chart range."""

        if hours <= 24:
            return bucket.astimezone().strftime("%H:%M")

        return bucket.astimezone().strftime("%m-%d")

    def _system_health(self) -> dict[str, Any]:
        """Return platform health indicators."""

        database_status = "Online"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            database_status = "Error"

        memory_usage = None
        cpu_usage = None
        if psutil is not None:
            memory_usage = round(float(psutil.virtual_memory().percent), 1)
            cpu_usage = round(float(psutil.cpu_percent(interval=None)), 1)

        return {
            "telemetry_queue": 0,
            "detection_engine": "Online",
            "correlation_engine": "Online",
            "database_status": database_status,
            "average_processing_time_ms": 0,
            "dropped_events": 0,
            "memory_usage": memory_usage,
            "cpu_usage": cpu_usage,
            "recent_incidents": len(list_correlated_incidents()),
        }

    def _cloud_status(self) -> dict[str, Any]:
        """Return cloud deployment status for the homepage."""

        database_status = "Online"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            database_status = "Error"

        return {
            "application_mode": current_app.config["APPLICATION_MODE"],
            "public_url": effective_public_url(),
            "server_ip": server_ip(),
            "hostname": hostname(),
            "operating_system": platform.platform(),
            "gunicorn_status": gunicorn_status(),
            "nginx_status": process_status("nginx"),
            "database": _database_type(current_app.config["SQLALCHEMY_DATABASE_URI"]),
            "server_uptime": _format_duration(time.time() - DASHBOARD_STARTED_AT),
            "connected_endpoints": Endpoint.query.filter_by(status=STATUS_ONLINE).count(),
            "health_status": "Healthy" if database_status == "Online" else "Degraded",
        }


def _database_type(uri: str) -> str:
    if uri.startswith("sqlite:///"):
        return "SQLite"
    if uri.startswith("postgresql"):
        return "PostgreSQL"
    return "SQLAlchemy Database"


def _format_duration(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, sec = divmod(remainder, 60)
    return f"{hours}h {minutes}m {sec}s"


dashboard_service = DashboardService()
