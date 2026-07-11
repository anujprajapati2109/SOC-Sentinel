import importlib
import inspect
import logging
import pkgutil

from detection.rules import BaseRule
from models import DetectionRule, Telemetry
from services.alert_service import AlertService


logger = logging.getLogger(__name__)


class DetectionEngine:
    """Loads enabled rules and evaluates telemetry against them."""

    def __init__(self, alert_service: AlertService | None = None) -> None:
        self.alert_service = alert_service or AlertService()
        self.rule_classes = self._discover_rule_classes()

    def evaluate(self, telemetry_events: list[Telemetry]) -> int:
        """Evaluate stored telemetry events and return created alert count."""

        enabled_rules = DetectionRule.query.filter_by(enabled=True).all()
        created_count = 0

        for event in telemetry_events:
            for rule_config in enabled_rules:
                rule_class = self.rule_classes.get(rule_config.rule_id)
                if rule_class is None:
                    logger.warning("No rule implementation for %s", rule_config.rule_id)
                    continue

                rule = rule_class(rule_config)
                result = rule.evaluate(event)
                if result is None:
                    continue

                alert = self.alert_service.create_alert(result)
                if alert is not None:
                    created_count += 1

        return created_count

    def _discover_rule_classes(self) -> dict[str, type[BaseRule]]:
        """Discover BaseRule subclasses from detection.rules modules."""

        import detection.rules as rules_package

        discovered: dict[str, type[BaseRule]] = {}
        for module_info in pkgutil.iter_modules(rules_package.__path__):
            if module_info.name in {"base_rule"}:
                continue

            module = importlib.import_module(f"detection.rules.{module_info.name}")
            for _, candidate in inspect.getmembers(module, inspect.isclass):
                if candidate is BaseRule or not issubclass(candidate, BaseRule):
                    continue
                discovered[candidate.rule_id] = candidate

        return discovered
