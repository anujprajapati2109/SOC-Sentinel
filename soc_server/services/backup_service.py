import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app


@dataclass(frozen=True)
class BackupResult:
    """Result of a database backup request."""

    success: bool
    message: str
    path: Path | None = None


def is_sqlite_database() -> bool:
    """Return whether the configured database is SQLite."""

    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    return uri.startswith("sqlite:///")


def database_label() -> str:
    """Return a non-secret database type label."""

    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///"):
        return "SQLite"
    if uri.startswith("postgresql"):
        return "PostgreSQL"
    return "SQLAlchemy Database"


def create_sqlite_backup() -> BackupResult:
    """Create a timestamped SQLite database backup for download."""

    if not is_sqlite_database():
        return BackupResult(
            False,
            "PostgreSQL backups must use pg_dump or managed database snapshots.",
        )

    source = Path(current_app.config["DATABASE_PATH"])
    if not source.exists():
        return BackupResult(False, "SQLite database file does not exist.")

    backup_dir = Path(current_app.config["DATABASE_DIR"]) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"soc_sentinel-{timestamp}.db"
    shutil.copy2(source, target)
    return BackupResult(True, "SQLite backup created.", target)
