import importlib
import inspect
import logging
import pkgutil

from correlation.rules import __path__ as rules_path
from correlation.rules.base_rule import BaseCorrelationRule


logger = logging.getLogger(__name__)


class CorrelationRuleLoader:
    """Discovers correlation rule classes from the rules package."""

    def load_rules(self) -> list[BaseCorrelationRule]:
        """Import rule modules and instantiate concrete rule classes."""

        rules: list[BaseCorrelationRule] = []

        for module_info in pkgutil.iter_modules(rules_path):
            if module_info.name.startswith("_") or module_info.name == "base_rule":
                continue

            module = importlib.import_module(f"correlation.rules.{module_info.name}")
            rules.extend(self._load_module_rules(module))

        return sorted(rules, key=lambda rule: rule.rule_id)

    def _load_module_rules(self, module) -> list[BaseCorrelationRule]:
        """Return concrete BaseCorrelationRule subclasses from one module."""

        discovered: list[BaseCorrelationRule] = []
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is BaseCorrelationRule:
                continue

            if not issubclass(candidate, BaseCorrelationRule):
                continue

            if inspect.isabstract(candidate):
                continue

            try:
                discovered.append(candidate())
            except TypeError as exc:
                logger.warning(
                    "Skipping correlation rule %s: %s",
                    candidate.__name__,
                    exc,
                )

        return discovered
