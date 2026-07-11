from logger import LOG_FILE


MAX_LOG_BYTES = 64 * 1024


def execute() -> dict:
    """Return the tail of the local agent log without uploading huge files."""

    if not LOG_FILE.exists():
        return {"log": "", "message": "agent.log does not exist"}

    with LOG_FILE.open("rb") as log_file:
        if LOG_FILE.stat().st_size > MAX_LOG_BYTES:
            log_file.seek(-MAX_LOG_BYTES, 2)
        content = log_file.read().decode("utf-8", errors="replace")

    return {
        "log": content,
        "truncated": LOG_FILE.stat().st_size > MAX_LOG_BYTES,
        "bytes_returned": len(content.encode("utf-8", errors="replace")),
    }
