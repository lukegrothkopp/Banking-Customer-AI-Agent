from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AgentResult:
route: str
message: str
meta: Dict[str, Any]
