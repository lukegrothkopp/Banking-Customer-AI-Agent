from __future__ import annotations
from .db import log_event




def log_info(agent: str, event: str, details: str = "") -> None:
log_event("INFO", agent, event, details)




def log_warn(agent: str, event: str, details: str = "") -> None:
log_event("WARN", agent, event, details)




def log_error(agent: str, event: str, details: str = "") -> None:
log_event("ERROR", agent, event, details)
