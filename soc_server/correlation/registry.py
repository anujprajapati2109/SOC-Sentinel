from correlation.engine import CorrelationEngine


_engine: CorrelationEngine | None = None


def configure_correlation_engine(
    retention_seconds: int,
    duplicate_cooldown_seconds: int,
) -> CorrelationEngine:
    """Create the process-local engine with application configuration."""

    global _engine
    if _engine is None:
        _engine = CorrelationEngine.from_config(
            retention_seconds=retention_seconds,
            duplicate_cooldown_seconds=duplicate_cooldown_seconds,
        )

    return _engine


def get_correlation_engine() -> CorrelationEngine:
    """Return the process-local correlation engine singleton."""

    global _engine
    if _engine is None:
        _engine = CorrelationEngine()

    return _engine
