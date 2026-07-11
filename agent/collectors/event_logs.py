import logging
import platform
import threading
from typing import Any

from telemetry_event import TelemetryEvent, utc_now
from telemetry_queue import TelemetryQueue


SECURITY_EVENT_TYPES = {
    4624: ("login_success", "info"),
    4625: ("login_failure", "high"),
    4720: ("user_created", "high"),
    4726: ("user_deleted", "high"),
}


def start_windows_event_collector(
    endpoint_id: str,
    telemetry_queue: TelemetryQueue,
    logger: logging.Logger,
    stop_event: threading.Event,
    interval_seconds: int = 10,
) -> threading.Thread:
    """Start a collector for selected Windows Security Event Log IDs."""

    thread = threading.Thread(
        target=_collector_loop,
        args=(endpoint_id, telemetry_queue, logger, stop_event, interval_seconds),
        name="windows-event-collector",
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
    """Poll Windows Security events and emit only selected new event IDs."""

    if platform.system() != "Windows":
        logger.warning("Windows Event collector skipped on non-Windows platform.")
        return

    try:
        import win32evtlog
    except ImportError:
        logger.warning("Windows Event collector skipped because pywin32 is missing.")
        return

    try:
        seen_records = _read_security_events(
            win32evtlog,
            endpoint_id,
            telemetry_queue,
            True,
        )
    except Exception as exc:
        logger.warning("Windows Event collector unavailable: %s", exc)
        return
    logger.info(
        "Windows Event collector initialized with %s existing Security records.",
        len(seen_records),
    )

    while not stop_event.is_set():
        try:
            seen_records.update(
                _read_security_events(
                    win32evtlog,
                    endpoint_id,
                    telemetry_queue,
                    False,
                    seen_records,
                )
            )
        except Exception as exc:
            logger.warning("Windows Event collector poll failed: %s", exc)
        stop_event.wait(interval_seconds)


def _read_security_events(
    win32evtlog: Any,
    endpoint_id: str,
    telemetry_queue: TelemetryQueue,
    initialize_only: bool,
    seen_records: set[int] | None = None,
) -> set[int]:
    """Read selected Security events and return observed record numbers."""

    observed: set[int] = set()
    seen_records = seen_records or set()
    handle = win32evtlog.OpenEventLog(None, "Security")
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    try:
        while True:
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            if not events:
                break

            for event in events:
                record_number = int(event.RecordNumber)
                if record_number in seen_records:
                    return observed

                observed.add(record_number)
                event_id = int(event.EventID) & 0xFFFF
                if initialize_only or event_id not in SECURITY_EVENT_TYPES:
                    continue

                event_type, severity = SECURITY_EVENT_TYPES[event_id]
                telemetry_queue.push(
                    TelemetryEvent(
                        endpoint_id=endpoint_id,
                        collector="windows_event",
                        event_type=event_type,
                        severity=severity,
                        timestamp=utc_now(),
                        data={
                            "event_id": event_id,
                            "record_number": record_number,
                            "source": event.SourceName,
                            "category": event.EventCategory,
                            "strings": list(event.StringInserts or []),
                        },
                    )
                )
    finally:
        win32evtlog.CloseEventLog(handle)

    return observed
