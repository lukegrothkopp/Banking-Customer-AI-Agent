from __future__ import annotations
from pydantic import BaseModel
from ..core.llm import LLMClient
from ..core.db import insert_ticket
from ..core.logging import log_info
from ..core.utils import generate_ticket_number


POS_SYSTEM = (
"You are a helpful banking assistant. Craft a warm, concise thank‑you reply."
)
NEG_SYSTEM = (
"You are an empathetic banking assistant. Acknowledge frustration and reassure with next steps."
)


class FeedbackHandler(BaseModel):
def handle_positive(self, customer_name: str | None) -> str:
llm = LLMClient()
prompt = (
f"Customer name: {customer_name or 'there'}\n"
"Write a one‑sentence thank‑you with friendly tone."
)
if llm.enabled:
msg = llm.chat(POS_SYSTEM, prompt)
else:
msg = f"Thank you for your kind words, {customer_name or 'friend'}! We’re delighted to assist you."
log_info("FeedbackHandler", "positive_response", msg)
return msg


def handle_negative(self, customer_name: str | None, description: str) -> str:
# create ticket
ticket_no = generate_ticket_number()
insert_ticket(ticket_no, customer_name, description, status="Open")
msg = (
f"We apologize for the inconvenience. A new ticket #{ticket_no} has been generated, "
"and our team will follow up shortly."
)
log_info("FeedbackHandler", "negative_ticket_created", f"ticket={ticket_no}")
return msg
