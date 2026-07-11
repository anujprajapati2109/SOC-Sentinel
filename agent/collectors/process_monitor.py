import logging
import threading

import psutil

from telemetry_event import TelemetryEvent, utc_now
from telemetry_queue import TelemetryQueue


def start_process_collector(
    endpoint_id: str,
    telemetry_queue: TelemetryQueue,
    logger: logging.Logger,
    stop_event: threading.Event,
    interval_seconds: int = 5,
) -> threading.Thread:
    """Start a background collector for newly started processes."""

    thread = threading.Thread(
        target=_collector_loop,
        args=(endpoint_id, telemetry_queue, logger, stop_event, interval_seconds),
        name="process-collector",
        daemon=True,
    )
    thread.start()
    return thread


def _collector_loop(
    endpoint_id: str,
    telemetry_queue: TelemetryQueue,
    logger: logging.Logger,
    stop_event: threading.Event,
    interval_seconds: int,
) -> None:
    """Poll running processes and emit events only for new PIDs."""

    known_pids = {process.pid for process in psutil.process_iter(["pid"])}
    logger.info("Process collector started with %s existing PIDs.", len(known_pids))

    while not stop_event.is_set():
        current_pids = set()
        for process in psutil.process_iter(
            ["pid", "name", "username", "cpu_percent", "memory_percent"]
        ):
            current_pids.add(process.pid)
            if process.pid in known_pids:
                continue

            try:
                info = process.info
                telemetry_queue.push(
                    TelemetryEvent(
                        endpoint_id=endpoint_id,
                        collector="process",
                        event_type="process_started",
                        severity="info",
                        timestamp=utc_now(),
                        data={
                            "process_name": info.get("name"),
                            "pid": info.get("pid"),
                            "username": info.get("username"),
                            "cpu_percent": info.get("cpu_percent"),
                            "memory_percent": info.get("memory_percent"),
                        },
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        known_pids = current_pids
        stop_event.wait(interval_seconds)
