# core/logging.py
from __future__ import annotations
from core.db import log_event as db_log_event, get_conn

def log_event(level="INFO", agent="App", event="", details=None):
    conn = get_conn()
    db_log_event(conn, level=level, agent=agent, event=event, details=details or {})
    
def log_info(agent: str, event: str, details: str = "") -> None:
    """Log an informational event."""
    log_event("INFO", agent, event, details)


def log_warn(agent: str, event: str, details: str = "") -> None:
    """Log a warning event."""
    log_event("WARN", agent, event, details)


def log_error(agent: str, event: str, details: str = "") -> None:
    """Log an error event."""
    log_event("ERROR", agent, event, details)
