# agents/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AgentResult:
    """
    Generic container for results returned by any agent.
    Holds the routing label, the response message,
    and any optional metadata (e.g., ticket number, sentiment).
    """
    route: str
    message: str
    meta: Dict[str, Any]
