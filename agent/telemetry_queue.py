import logging
import queue
import threading
import time
from typing import Iterable

import requests

from api_client import APIClient
from telemetry_event import TelemetryEvent


class TelemetryQueue:
    """Thread-safe in-memory queue for telemetry events."""

    def __init__(self) -> None:
        self._queue: queue.Queue[TelemetryEvent] = queue.Queue()

    def push(self, event: TelemetryEvent) -> None:
        """Add one event to the queue."""

        self._queue.put(event)

    def push_many(self, events: Iterable[TelemetryEvent]) -> None:
        """Add multiple events to the queue."""

        for event in events:
            self.push(event)

    def get_batch(self, max_items: int) -> list[TelemetryEvent]:
        """Return up to max_items without blocking after the first item."""

        events = [self._queue.get(timeout=1)]
        while len(events) < max_items:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    def requeue_front(self, events: list[TelemetryEvent]) -> None:
        """Requeue failed events so temporary outages do not drop data."""

        for event in events:
            self._queue.put(event)

    def empty(self) -> bool:
        """Return whether the queue has no pending events."""

        return self._queue.empty()

    def size(self) -> int:
        """Return approximate queue size."""

        return self._queue.qsize()


def start_sender_thread(
    telemetry_queue: TelemetryQueue,
    client: APIClient,
    logger: logging.Logger,
    stop_event: threading.Event,
    batch_size: int = 50,
) -> threading.Thread:
    """Start the telemetry sender thread."""

    thread = threading.Thread(
        target=_sender_loop,
        args=(telemetry_queue, client, logger, stop_event, batch_size),
        name="telemetry-sender",
        daemon=True,
    )
    thread.start()
    return thread


def _sender_loop(
    telemetry_queue: TelemetryQueue,
    client: APIClient,
    logger: logging.Logger,
    stop_event: threading.Event,
    batch_size: int,
) -> None:
    """Send queued telemetry batches with retry and exponential backoff."""

    backoff_seconds = 1
    max_backoff_seconds = 300

    while not stop_event.is_set() or not telemetry_queue.empty():
        batch: list[TelemetryEvent] = []
        try:
            batch = telemetry_queue.get_batch(batch_size)
            client.send_telemetry(batch)
            logger.info("Sent %s telemetry events.", len(batch))
            backoff_seconds = 1
        except queue.Empty:
            stop_event.wait(1)
        except requests.RequestException as exc:
            if batch:
                telemetry_queue.requeue_front(batch)
            if stop_event.is_set():
                logger.warning("Telemetry flush failed during shutdown: %s", exc)
                return
            logger.warning(
                "Telemetry send failed: %s. Retrying in %s seconds.",
                exc,
                backoff_seconds,
            )
            stop_event.wait(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, max_backoff_seconds)
