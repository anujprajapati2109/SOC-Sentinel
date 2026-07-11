import os
from pathlib import Path


def _database_uri(default_path: Path) -> str:
    """Return configured database URI while preserving SQLite defaults."""

    configured = os.getenv("DATABASE_URL")
    if configured:
        # Heroku-style URLs still appear in examples; SQLAlchemy expects postgresql.
        if configured.startswith("postgres://"):
            return configured.replace("postgres://", "postgresql://", 1)
        return configured

    return f"sqlite:///{default_path.as_posix()}"


class Config:
    """Base application configuration for SOC Sentinel."""

    BASE_DIR = Path(__file__).resolve().parent
    DATABASE_DIR = BASE_DIR / "database"
    DATABASE_PATH = DATABASE_DIR / "soc_sentinel.db"
    LOG_DIR = BASE_DIR / "logs"

    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-before-production")
    SQLALCHEMY_DATABASE_URI = _database_uri(DATABASE_PATH)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    HOST = os.getenv("SERVER_HOST", os.getenv("SOC_SENTINEL_HOST", "127.0.0.1"))
    PORT = int(os.getenv("SERVER_PORT", os.getenv("SOC_SENTINEL_PORT", "5000")))
    PUBLIC_URL = os.getenv("PUBLIC_URL", f"http://{HOST}:{PORT}").rstrip("/")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    APPLICATION_MODE = os.getenv("FLASK_CONFIG", "development")
    PREFERRED_URL_SCHEME = "https" if PUBLIC_URL.startswith("https://") else "http"
    SESSION_COOKIE_SECURE = PUBLIC_URL.startswith("https://")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    ENDPOINT_HEARTBEAT_TIMEOUT_SECONDS = int(
        os.getenv("ENDPOINT_HEARTBEAT_TIMEOUT_SECONDS", "90")
    )
    CORRELATION_RETENTION_SECONDS = int(
        os.getenv("CORRELATION_RETENTION_SECONDS", "900")
    )
    CORRELATION_DUPLICATE_COOLDOWN_SECONDS = int(
        os.getenv("CORRELATION_DUPLICATE_COOLDOWN_SECONDS", "300")
    )


class DevelopmentConfig(Config):
    """Development defaults used by python app.py."""

    DEBUG = True
    APPLICATION_MODE = "development"


class ProductionConfig(Config):
    """Production configuration for WSGI deployments."""

    DEBUG = False
    APPLICATION_MODE = "production"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
