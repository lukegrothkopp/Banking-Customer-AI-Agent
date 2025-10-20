from __future__ import annotations
from pydantic import BaseModel

from core.llm import LLMClient                               # absolute
from core.db import get_conn, insert_ticket, log_event       # absolute
from core.logging import log_info                            # absolute
from core.utils import generate_ticket_number                # absolute

POS_SYSTEM = "You are a helpful banking assistant. Craft a warm, concise thank-you reply."
NEG_SYSTEM = "You are an empathetic banking assistant. Acknowledge frustration and reassure with next steps."

class FeedbackHandler:
    def __init__(self, conn=None):
        # Ensure we always have a valid connection
        self.conn = conn or get_conn()

    def handle_positive(self, customer_name: str | None = None) -> str:
        name = (customer_name or "Customer").strip() or "Customer"
        log_event(self.conn, level="INFO", agent="FeedbackHandler", event="positive_ack", details={"customer_name": name})
        return f"Thank you for your kind words, {name}! We’re delighted to assist you."

    def handle_negative(self, customer_name: str | None, description: str) -> str:
        name = (customer_name or "Unknown").strip() or "Unknown"
        ticket_no = generate_ticket_number()
        # ✅ Pass conn and use keyword args
        insert_ticket(
            self.conn,
            ticket_id=ticket_no,
            customer_name=name,
            description=description or "",
            status="Open",
        )
        log_event(self.conn, level="INFO", agent="FeedbackHandler", event="negative_ticket_created",
                  details={"customer_name": name, "ticket_id": ticket_no})
        return f"We apologize for the inconvenience. A new ticket #{ticket_no} has been generated, and our team will follow up shortly."
