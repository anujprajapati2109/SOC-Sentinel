import getpass
import os
import platform
import socket
import sys
import uuid

from config import AGENT_VERSION
from device_fingerprint import generate_device_fingerprint

try:
    import psutil
except ImportError:  # pragma: no cover - optional at runtime.
    psutil = None


def collect_system_info() -> dict[str, str]:
    """Collect endpoint identity and environment data for registration."""

    return {
        "hostname": socket.gethostname(),
        "username": getpass.getuser(),
        "operating_system": platform.system(),
        "os_version": platform.version(),
        "ip_address": get_local_ip_address(),
        "mac_address": get_mac_address(),
        "python_version": platform.python_version(),
        "agent_version": AGENT_VERSION,
        "device_fingerprint": generate_device_fingerprint(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": str(os.cpu_count() or ""),
        "total_memory_mb": get_total_memory_mb(),
        "system_drive": os.getenv("SystemDrive", ""),
    }


def get_local_ip_address() -> str:
    """Return the primary local IPv4 address without sending network traffic."""

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_mac_address() -> str:
    """Return the endpoint MAC address in a readable format."""

    mac_int = uuid.getnode()
    mac_hex = f"{mac_int:012x}"
    return ":".join(mac_hex[index : index + 2] for index in range(0, 12, 2))


def get_python_runtime() -> str:
    """Return a compact Python runtime description."""

    return f"{sys.implementation.name} {platform.python_version()}"


def get_total_memory_mb() -> str:
    """Return installed RAM in MB when psutil is available."""

    if psutil is None:
        return ""

    return str(round(psutil.virtual_memory().total / (1024 * 1024)))
