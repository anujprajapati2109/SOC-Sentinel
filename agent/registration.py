import logging

from api_client import APIClient
from config import AgentConfig, save_config
from system_info import collect_system_info


def ensure_registered(
    config: AgentConfig,
    client: APIClient,
    logger: logging.Logger,
) -> None:
    """Register the agent when endpoint credentials are missing."""

    if config.is_registered:
        logger.info("Agent already registered as %s", config.endpoint_id)
        return

    logger.info("No endpoint credentials found. Starting registration.")
    payload = collect_system_info()
    response = client.register(payload)
    endpoint = response["endpoint"]

    config.endpoint_id = endpoint["endpoint_id"]
    config.api_key = endpoint["api_key"]
    save_config(config)

    logger.info("Registration successful. Endpoint ID: %s", config.endpoint_id)
