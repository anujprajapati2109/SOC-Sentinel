import socket

from flask import current_app, has_request_context, request


try:
    import psutil
except ImportError:  # pragma: no cover - optional runtime dependency.
    psutil = None


def effective_public_url() -> str:
    """Return configured public URL or infer it from the proxied request."""

    configured = current_app.config.get("PUBLIC_URL", "").strip().rstrip("/")
    if configured and not is_placeholder_url(configured):
        return configured

    if has_request_context():
        return request.url_root.rstrip("/")

    host = current_app.config.get("HOST", "127.0.0.1")
    port = current_app.config.get("PORT", 5000)
    return f"http://{host}:{port}"


def is_placeholder_url(value: str) -> bool:
    lowered = value.lower()
    return any(
        placeholder in lowered
        for placeholder in (
            "your-domain.example.com",
            "your-server.example.com",
            "example.com",
        )
    )


def server_ip() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "Unknown"


def hostname() -> str:
    return socket.gethostname()


def gunicorn_status() -> str:
    if has_request_context():
        server_software = request.environ.get("SERVER_SOFTWARE", "")
        if "gunicorn" in server_software.lower():
            return "Running"
    return process_status("gunicorn")


def process_status(name: str) -> str:
    if psutil is None:
        return "Unknown"

    lowered = name.lower()
    for process in psutil.process_iter(["name", "cmdline"]):
        try:
            process_name = (process.info.get("name") or "").lower()
            command = " ".join(process.info.get("cmdline") or []).lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if lowered in process_name or lowered in command:
            return "Running"
    return "Not Running"
