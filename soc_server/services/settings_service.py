from dataclasses import dataclass
from typing import Any

from models import Setting, db


@dataclass(frozen=True)
class SettingDefinition:
    """Definition and validation metadata for one editable setting."""

    key: str
    label: str
    category: str
    default: str
    value_type: str
    description: str


DEFAULT_SETTINGS = [
    SettingDefinition("soc_name", "SOC Name", "General", "SOC Sentinel", "text", "Display name for this SOC instance."),
    SettingDefinition("organization", "Organization", "General", "Local SOC", "text", "Organization name shown in reports."),
    SettingDefinition("dashboard_refresh_interval", "Dashboard Refresh Interval", "Dashboard", "5", "int", "Live dashboard polling interval in seconds."),
    SettingDefinition("heartbeat_interval", "Heartbeat Interval", "Agent Configuration", "30", "int", "Expected endpoint heartbeat interval in seconds."),
    SettingDefinition("telemetry_retention", "Telemetry Retention", "Detection Configuration", "30", "int", "Telemetry retention period in days."),
    SettingDefinition("duplicate_suppression_cooldown", "Duplicate Suppression Cooldown", "Detection Configuration", "300", "int", "Duplicate incident suppression cooldown in seconds."),
    SettingDefinition("correlation_window", "Correlation Window", "Detection Configuration", "900", "int", "Correlation context retention window in seconds."),
    SettingDefinition("theme", "Theme", "Dashboard", "Dark", "choice:Dark,Light", "Dashboard color theme."),
    SettingDefinition("timezone", "Timezone", "Dashboard", "UTC", "text", "Preferred display timezone label."),
    SettingDefinition("log_level", "Log Level", "General", "INFO", "choice:DEBUG,INFO,WARNING,ERROR", "Server log verbosity."),
]


def seed_settings() -> None:
    """Create default settings if missing."""

    for definition in DEFAULT_SETTINGS:
        setting = Setting.query.filter_by(key=definition.key).first()
        if setting is None:
            db.session.add(
                Setting(
                    key=definition.key,
                    value=definition.default,
                    label=definition.label,
                    category=definition.category,
                    value_type=definition.value_type,
                    description=definition.description,
                )
            )
            continue

        setting.label = definition.label
        setting.category = definition.category
        setting.value_type = definition.value_type
        setting.description = definition.description

    db.session.commit()


def list_settings_grouped() -> dict[str, list[Setting]]:
    """Return editable settings grouped by category."""

    settings = Setting.query.order_by(Setting.category.asc(), Setting.id.asc()).all()
    grouped: dict[str, list[Setting]] = {}
    for setting in settings:
        grouped.setdefault(setting.category, []).append(setting)
    return grouped


def get_setting_value(key: str, fallback: str = "") -> str:
    """Return one setting value or fallback."""

    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting is not None else fallback


def update_settings(values: dict[str, Any]) -> tuple[bool, str]:
    """Validate and persist editable settings."""

    settings = Setting.query.all()
    for setting in settings:
        if setting.key not in values:
            continue

        raw_value = str(values[setting.key]).strip()
        valid, message = validate_setting(setting, raw_value)
        if not valid:
            return False, message

        setting.value = raw_value

    db.session.commit()
    return True, "Settings saved successfully."


def reset_settings() -> None:
    """Reset all settings to defaults."""

    defaults = {definition.key: definition.default for definition in DEFAULT_SETTINGS}
    for setting in Setting.query.all():
        if setting.key in defaults:
            setting.value = defaults[setting.key]
    db.session.commit()


def validate_setting(setting: Setting, value: str) -> tuple[bool, str]:
    """Validate a submitted setting value."""

    if not value:
        return False, f"{setting.label} is required."

    if setting.value_type == "int":
        try:
            parsed = int(value)
        except ValueError:
            return False, f"{setting.label} must be a number."

        if parsed < 1:
            return False, f"{setting.label} must be greater than zero."

    if setting.value_type.startswith("choice:"):
        choices = setting.value_type.split(":", 1)[1].split(",")
        if value not in choices:
            return False, f"{setting.label} must be one of: {', '.join(choices)}."

    return True, ""
