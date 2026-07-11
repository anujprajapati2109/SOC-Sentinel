import logging
import os
import platform
import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileMovedEvent
from watchdog.observers import Observer

from telemetry_event import TelemetryEvent, utc_now
from telemetry_queue import TelemetryQueue


FILE_EVENT_SEVERITY = {
    "file_created": "low",
    "file_modified": "low",
    "file_deleted": "medium",
    "file_renamed": "medium",
}


def start_file_collector(
    endpoint_id: str,
    telemetry_queue: TelemetryQueue,
    logger: logging.Logger,
    stop_event: threading.Event,
) -> threading.Thread:
    """Start monitoring the current user's Documents folder."""

    thread = threading.Thread(
        target=_collector_loop,
        args=(endpoint_id, telemetry_queue, logger, stop_event),
        name="file-collector",
        daemon=True,
    )
    thread.start()
    return thread


class DocumentsEventHandler(FileSystemEventHandler):
    """Convert watchdog file events into SOC telemetry events."""

    def __init__(self, endpoint_id: str, telemetry_queue: TelemetryQueue) -> None:
        self.endpoint_id = endpoint_id
        self.telemetry_queue = telemetry_queue

    def on_created(self, event: FileSystemEvent) -> None:
        self._push("file_created", event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._push("file_modified", event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._push("file_deleted", event)

    def on_moved(self, event: FileMovedEvent) -> None:
        self._push("file_renamed", event)

    def _push(self, event_type: str, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        data = {"path": event.src_path}
        if isinstance(event, FileMovedEvent):
            data["destination_path"] = event.dest_path

        self.telemetry_queue.push(
            TelemetryEvent(
                endpoint_id=self.endpoint_id,
                collector="file",
                event_type=event_type,
                severity=FILE_EVENT_SEVERITY[event_type],
                timestamp=utc_now(),
                data=data,
            )
        )


def _collector_loop(
    endpoint_id: str,
    telemetry_queue: TelemetryQueue,
    logger: logging.Logger,
    stop_event: threading.Event,
) -> None:
    """Run a watchdog observer until the agent stops."""

    documents_path = get_documents_folder()
    documents_path.mkdir(exist_ok=True)

    observer = Observer()
    observer.schedule(
        DocumentsEventHandler(endpoint_id, telemetry_queue),
        str(documents_path),
        recursive=True,
    )
    observer.start()
    logger.info("File collector monitoring %s.", documents_path)

    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    finally:
        observer.stop()
        observer.join(timeout=10)


def get_documents_folder() -> Path:
    """Return the real user Documents folder, including OneDrive redirection."""

    if platform.system() != "Windows":
        return Path.home() / "Documents"

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "Personal")
            return Path(os.path.expandvars(value))
    except OSError:
        return Path.home() / "Documents"
