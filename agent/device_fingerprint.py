import hashlib
import platform
import re
import socket
import subprocess
import uuid
from functools import lru_cache


try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows development fallback.
    winreg = None


_PLACEHOLDER_VALUES = {
    "",
    "none",
    "null",
    "unknown",
    "to be filled by o.e.m.",
    "to be filled by oem",
    "default string",
    "system serial number",
    "serial number",
    "0",
}


@lru_cache(maxsize=1)
def generate_device_fingerprint() -> str:
    """Return a deterministic SHA-256 fingerprint for this endpoint."""

    identifiers = collect_hardware_identifiers()
    normalized_parts = [
        f"{name}={value}"
        for name, value in sorted(identifiers.items())
        if value
    ]
    fingerprint_source = "|".join(normalized_parts)
    return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()


def collect_hardware_identifiers() -> dict[str, str]:
    """Collect stable hardware and OS identifiers without requiring all of them."""

    identifiers = {
        "machine_guid": get_windows_machine_guid(),
        "bios_serial": query_wmic_value("bios", "serialnumber"),
        "motherboard_serial": query_wmic_value("baseboard", "serialnumber"),
        "cpu_id": query_wmic_value("cpu", "processorid"),
        "mac_address": get_mac_address(),
    }

    cleaned = {
        name: value
        for name, raw_value in identifiers.items()
        if (value := normalize_identifier(raw_value))
    }

    if cleaned:
        return cleaned

    # Last-resort fallback keeps the hash deterministic on constrained systems.
    return {
        "hostname": normalize_identifier(socket.gethostname()) or "unavailable",
        "platform": normalize_identifier(platform.platform()) or "unavailable",
    }


def get_windows_machine_guid() -> str | None:
    """Read the Windows MachineGuid from HKLM when available."""

    if winreg is None:
        return None

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as registry_key:
            value, _ = winreg.QueryValueEx(registry_key, "MachineGuid")
            return str(value)
    except OSError:
        return None


def query_wmic_value(alias: str, field: str) -> str | None:
    """Query a single WMIC value and tolerate unavailable providers."""

    try:
        completed = subprocess.run(
            ["wmic", alias, "get", field, "/value"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip().lower() == field.lower():
            return value

    return None


def get_mac_address() -> str:
    """Return the primary MAC address from Python's UUID helper."""

    mac_int = uuid.getnode()
    mac_hex = f"{mac_int:012x}"
    return ":".join(mac_hex[index : index + 2] for index in range(0, 12, 2))


def normalize_identifier(value: str | None) -> str | None:
    """Normalize hardware identifiers before hashing."""

    if value is None:
        return None

    cleaned = re.sub(r"\s+", " ", str(value)).strip().lower()
    if cleaned in _PLACEHOLDER_VALUES:
        return None

    return cleaned
