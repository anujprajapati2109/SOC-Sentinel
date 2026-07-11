import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def get_runtime_dir() -> Path:
    """Return the directory where persistent agent files should live."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


BASE_DIR = get_runtime_dir()
CONFIG_PATH = BASE_DIR / "config.json"
AGENT_VERSION = "0.8.0"
AGENT_DISPLAY_NAME = "SOC Sentinel Agent"
DEFAULT_SERVER_URL = os.getenv("SOC_SENTINEL_SERVER_URL", "http://127.0.0.1:5000")


@dataclass
class AgentConfig:
    """Runtime configuration for the SOC Sentinel agent."""

    server_url: str
    endpoint_id: str
    api_key: str
    heartbeat_interval: int
    run_at_startup: bool
    show_tray_icon: bool
    log_level: str

    @property
    def is_registered(self) -> bool:
        """Return whether the agent has server-issued credentials."""

        return bool(self.endpoint_id and self.api_key)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config for writing back to config.json."""

        return {
            "server_url": self.server_url,
            "endpoint_id": self.endpoint_id,
            "api_key": self.api_key,
            "heartbeat_interval": self.heartbeat_interval,
            "run_at_startup": self.run_at_startup,
            "show_tray_icon": self.show_tray_icon,
            "log_level": self.log_level,
        }


def load_config() -> AgentConfig:
    """Load agent configuration from config.json."""

    if not CONFIG_PATH.exists():
        save_config(
            AgentConfig(
                server_url=DEFAULT_SERVER_URL,
                endpoint_id="",
                api_key="",
                heartbeat_interval=30,
                run_at_startup=True,
                show_tray_icon=True,
                log_level="INFO",
            )
        )

    with CONFIG_PATH.open("r", encoding="utf-8-sig") as config_file:
        data = json.load(config_file)

    config = AgentConfig(
        server_url=str(data.get("server_url", DEFAULT_SERVER_URL)).rstrip("/"),
        endpoint_id=str(data.get("endpoint_id", "")),
        api_key=str(data.get("api_key", "")),
        heartbeat_interval=int(data.get("heartbeat_interval", 30)),
        run_at_startup=bool(data.get("run_at_startup", True)),
        show_tray_icon=bool(data.get("show_tray_icon", True)),
        log_level=str(data.get("log_level", "INFO")).upper(),
    )

    if _is_missing_new_fields(data):
        save_config(config)

    return config


def save_config(config: AgentConfig) -> None:
    """Persist agent configuration to config.json."""

    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(config.to_dict(), config_file, indent=2)
        config_file.write("\n")


def _is_missing_new_fields(data: dict[str, Any]) -> bool:
    """Return whether an older config file needs v0.3.5 defaults persisted."""

    required_fields = {"run_at_startup", "show_tray_icon", "log_level"}
    return not required_fields.issubset(data.keys())
