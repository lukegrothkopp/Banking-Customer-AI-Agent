from __future__ import annotations
from pydantic import BaseModel
from ..core.db import get_ticket
from ..core.logging import log_info
from ..core.utils import extract_ticket_number


class QueryHandler(BaseModel):
def handle(self, text: str) -> str:
tno = extract_ticket_number(text)
if not tno:
log_info("QueryHandler", "no_ticket_found", text)
return "I couldn’t find a ticket number in your message. Please provide a 6‑digit ticket ID (e.g., ticket 123456)."
rec = get_ticket(tno)
if not rec:
log_info("QueryHandler", "ticket_missing", tno)
return f"I couldn’t find ticket #{tno}. Please verify the number."
log_info("QueryHandler", "ticket_status", f"ticket={tno} status={rec['status']}")
return f"Your ticket #{tno} is currently marked as: {rec['status']}."
