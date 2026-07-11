from config import AgentConfig, AGENT_VERSION


def build_status_banner(config: AgentConfig) -> str:
    """Build a concise CLI status banner for startup."""

    endpoint = config.endpoint_id or "Not registered"
    return (
        "\n"
        "SOC Sentinel Windows Agent\n"
        "==========================\n"
        f"Agent Version      : {AGENT_VERSION}\n"
        f"Server URL         : {config.server_url}\n"
        f"Endpoint ID        : {endpoint}\n"
        f"Heartbeat Interval : {config.heartbeat_interval}s\n"
    )
