import ctypes
import os
import threading

import pystray
from PIL import Image, ImageDraw

from agent_state import AgentState
from config import AGENT_DISPLAY_NAME, AGENT_VERSION, BASE_DIR
from logger import LOG_DIR
from runtime import RuntimeManager


class TrayApp:
    """System tray integration for the SOC Sentinel agent."""

    def __init__(self, runtime: RuntimeManager, state: AgentState) -> None:
        self.runtime = runtime
        self.state = state
        self.icon = pystray.Icon(
            "soc_sentinel_agent",
            self._create_icon(),
            AGENT_DISPLAY_NAME,
            menu=pystray.Menu(
                pystray.MenuItem("SOC Sentinel Agent", self._show_status, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Status", self._show_status),
                pystray.MenuItem("Reconnect", self._reconnect),
                pystray.MenuItem("Open Logs", self._open_logs),
                pystray.MenuItem("Open Config Folder", self._open_config_folder),
                pystray.MenuItem("About", self._about),
                pystray.MenuItem("Exit", self._exit),
            ),
        )

    def run(self) -> None:
        """Run the tray icon loop."""

        self.icon.run()

    def stop(self) -> None:
        """Stop the tray icon."""

        self.icon.stop()

    def _show_status(self, *_args) -> None:
        snapshot = self.state.snapshot()
        _message_box(
            "SOC Sentinel Agent Status",
            (
                f"Endpoint ID: {snapshot.endpoint_id}\n"
                f"Server: {snapshot.server_url}\n"
                f"Connection Status: {snapshot.connection_status}\n"
                f"Last Heartbeat: {snapshot.last_heartbeat}"
            ),
        )

    def _reconnect(self, *_args) -> None:
        self.runtime.reconnect_async()

    def _open_logs(self, *_args) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(LOG_DIR)

    def _open_config_folder(self, *_args) -> None:
        os.startfile(BASE_DIR)

    def _about(self, *_args) -> None:
        snapshot = self.state.snapshot()
        _message_box(
            "About SOC Sentinel Agent",
            (
                "SOC Sentinel Agent\n"
                f"Version: {AGENT_VERSION}\n"
                "Developer: SOC Sentinel\n"
                f"Server URL: {snapshot.server_url}"
            ),
        )

    def _exit(self, *_args) -> None:
        threading.Thread(target=self._shutdown, name="tray-shutdown", daemon=True).start()

    def _shutdown(self) -> None:
        self.runtime.stop()
        self.stop()

    def _create_icon(self) -> Image.Image:
        """Create a simple in-memory tray icon."""

        image = Image.new("RGBA", (64, 64), (8, 12, 24, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((10, 8, 54, 58), radius=8, fill=(14, 165, 233, 255))
        draw.polygon((32, 16, 47, 24, 43, 47, 32, 54, 21, 47, 17, 24), fill="white")
        return image


def _message_box(title: str, message: str) -> None:
    """Show a Windows message box."""

    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
