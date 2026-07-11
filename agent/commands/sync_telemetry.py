import time

from telemetry_queue import TelemetryQueue


def execute(telemetry_queue: TelemetryQueue, timeout_seconds: int = 10) -> dict:
    """Wait briefly for the telemetry sender to drain queued events."""

    deadline = time.time() + timeout_seconds
    while not telemetry_queue.empty() and time.time() < deadline:
        time.sleep(0.25)

    return {
        "queue_length": telemetry_queue.size(),
        "drained": telemetry_queue.empty(),
    }
