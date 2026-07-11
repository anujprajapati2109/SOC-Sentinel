from api_client import APIClient
from agent_state import AgentState


def execute(client: APIClient, state: AgentState | None = None) -> dict:
    """Send an immediate heartbeat."""

    response = client.heartbeat()
    if state is not None:
        state.record_heartbeat()
    return {"heartbeat": "sent", "server_response": response}
