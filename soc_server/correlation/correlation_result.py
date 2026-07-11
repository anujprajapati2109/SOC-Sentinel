from dataclasses import dataclass, field
from typing import Any

from models import Alert


@dataclass(frozen=True)
class CorrelationResult:
    """Result returned by a correlation rule after matching alerts."""

    incident_title: str
    severity: str
    summary: str
    confidence: int
    risk_score: int
    timeline: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    mitre_tactic: str | None = None
    mitre_technique: str | None = None
    matched_alerts: list[Alert] = field(default_factory=list)
