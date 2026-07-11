import sys
from pathlib import Path

from config import AGENT_DISPLAY_NAME


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def install_startup() -> None:
    """Install HKCU autorun entry for the current agent executable."""

    if is_startup_installed():
        return

    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, AGENT_DISPLAY_NAME, 0, winreg.REG_SZ, _startup_command())


def remove_startup() -> None:
    """Remove HKCU autorun entry if present."""

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, AGENT_DISPLAY_NAME)
    except FileNotFoundError:
        return


def is_startup_installed() -> bool:
    """Return whether HKCU autorun entry already exists."""

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, AGENT_DISPLAY_NAME)
            return value == _startup_command()
    except FileNotFoundError:
        return False


def _startup_command() -> str:
    """Return startup command for packaged exe or development source run."""

    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return f'"{executable}"'

    script_path = Path(__file__).resolve().parent / "main.py"
    return f'"{executable}" "{script_path}"'
