import os
import sys
import threading
import time


def execute() -> dict:
    """Schedule a graceful process restart after the command result is posted."""

    threading.Thread(target=_restart_after_delay, name="agent-restart", daemon=True).start()
    return {"restart": "scheduled"}


def _restart_after_delay() -> None:
    time.sleep(2)
    os.execv(sys.executable, [sys.executable, *sys.argv])
