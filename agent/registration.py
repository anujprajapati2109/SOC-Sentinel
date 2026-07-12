import logging

from api_client import APIClient
from config import AgentConfig, save_config
from system_info import collect_system_info


def ensure_registered(
    config: AgentConfig,
    client: APIClient,
    logger: logging.Logger,
) -> None:
    """Register the agent when credentials are missing or copied from another PC."""

    payload = collect_system_info()
    current_fingerprint = payload.get("device_fingerprint", "")
    current_mac = payload.get("mac_address", "")

    if config.is_registered:
        if _credentials_match_current_device(
            config,
            current_fingerprint,
            current_mac,
        ):
            logger.info("Agent already registered as %s", config.endpoint_id)
            return

        logger.warning(
            "Stored endpoint credentials do not match this device. "
            "Requesting endpoint identity from server."
        )
        config.endpoint_id = ""
        config.api_key = ""

    logger.info("No valid endpoint credentials found. Starting registration.")
    response = client.register(payload)
    endpoint = response["endpoint"]

    config.endpoint_id = endpoint["endpoint_id"]
    config.api_key = endpoint["api_key"]
    config.device_fingerprint = current_fingerprint
    config.mac_address = current_mac
    save_config(config)

    logger.info("Registration successful. Endpoint ID: %s", config.endpoint_id)


def _credentials_match_current_device(
    config: AgentConfig,
    current_fingerprint: str,
    current_mac: str,
) -> bool:
    """Return whether stored credentials were issued for this device."""

    if config.device_fingerprint:
        return config.device_fingerprint == current_fingerprint

    if config.mac_address:
        return config.mac_address.lower() == current_mac.lower()

    # Older configs did not store local identity. Re-registering lets the server
    # reuse the endpoint for this hardware or issue a fresh ID for another PC.
    return False
