import logging

from correlation.context import CorrelationContext
from correlation.rule_loader import CorrelationRuleLoader
from correlation.services.correlation_service import CorrelationService
from models import Alert, CorrelationRule


logger = logging.getLogger(__name__)


class CorrelationEngine:
    """Independent alert correlation engine foundation."""

    def __init__(
        self,
        rule_loader: CorrelationRuleLoader | None = None,
        service: CorrelationService | None = None,
        context: CorrelationContext | None = None,
    ) -> None:
        self.rule_loader = rule_loader or CorrelationRuleLoader()
        self.service = service or CorrelationService()
        self.context = context or CorrelationContext()
        self.rules = []
        self.enabled_rule_ids: set[str] = set()

    @classmethod
    def from_config(
        cls,
        retention_seconds: int,
        duplicate_cooldown_seconds: int,
    ) -> "CorrelationEngine":
        """Build an engine with configured context retention and cooldown."""

        return cls(
            context=CorrelationContext(retention_seconds=retention_seconds),
            service=CorrelationService(
                duplicate_cooldown_seconds=duplicate_cooldown_seconds
            ),
        )

    def start(self) -> None:
        """Load correlation rules and announce engine readiness."""

        logger.info("Correlation Engine Started")
        self.rules = self.rule_loader.load_rules()
        self.enabled_rule_ids = self._load_enabled_rule_ids()
        logger.info("Rules Loaded")
        logger.info("Number of Rules: %s", len(self.rules))
        logger.info("Correlation Engine Ready")

    def handle_alert(self, alert: Alert) -> None:
        """Update context with a new alert and evaluate correlation rules."""

        logger.info(
            "Alert received | alert=%s endpoint=%s",
            alert.alert_id,
            alert.endpoint_id,
        )
        if not self.rules:
            self.start()

        endpoint_alerts = self.context.add_alert(alert)
        self.evaluate(endpoint_alerts)

    def evaluate(self, alerts: list[Alert]) -> None:
        """Evaluate endpoint alert history with enabled rules."""

        for rule in self.rules:
            if not rule.enabled or rule.rule_id not in self.enabled_rule_ids:
                continue

            logger.info("Rule evaluation | correlation_rule=%s", rule.rule_id)
            for result in rule.evaluate(alerts):
                logger.info(
                    "Rule matched | correlation_rule=%s endpoint=%s",
                    rule.rule_id,
                    result.matched_alerts[0].endpoint_id
                    if result.matched_alerts
                    else "UNKNOWN",
                )
                self.service.create_incident(rule.rule_id, result)

    def _load_enabled_rule_ids(self) -> set[str]:
        """Return enabled correlation rule IDs from the database."""

        return {
            rule.rule_id
            for rule in CorrelationRule.query.filter_by(enabled=True).all()
        }
