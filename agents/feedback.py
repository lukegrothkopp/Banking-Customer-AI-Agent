from __future__ import annotations
from typing import Optional, Tuple
from pydantic import BaseModel

from core.llm import LLMClient                               # absolute (kept for future use)
from core.db import (
    get_conn,
    insert_ticket,
    log_event,
    append_ticket_note,
    add_ticket_action_flag,
    update_ticket_status,
)                                                            # absolute
from core.logging import log_info                            # absolute
from core.utils import generate_ticket_number                # absolute
from agents.intent import classify_intent                    # new

POS_SYSTEM = "You are a helpful banking assistant. Craft a warm, concise thank-you reply."
NEG_SYSTEM = "You are an empathetic banking assistant. Acknowledge frustration and reassure with next steps."

class FeedbackHandler:
    def __init__(self, conn=None):
        # Ensure we always have a valid connection
        self.conn = conn or get_conn()

    # ------------------------
    # Existing behavior
    # ------------------------
    def handle_positive(self, customer_name: str | None = None) -> str:
        name = (customer_name or "Customer").strip() or "Customer"
        log_event(self.conn, level="INFO", agent="FeedbackHandler", event="positive_ack",
                  details={"customer_name": name})
        return f"Thank you for your kind words, {name}! We’re delighted to assist you."

    def handle_negative(self, customer_name: str | None, description: str) -> str:
        name = (customer_name or "Unknown").strip() or "Unknown"
        ticket_no = generate_ticket_number()
        insert_ticket(
            self.conn,
            ticket_id=ticket_no,
            customer_name=name,
            description=description or "",
            status="Open",
        )
        log_event(self.conn, level="INFO", agent="FeedbackHandler", event="negative_ticket_created",
                  details={"customer_name": name, "ticket_id": ticket_no})
        return (
            f"We apologize for the inconvenience. A new ticket #{ticket_no} has been generated, "
            f"and our team will follow up shortly."
        )

    # ------------------------
    # NEW: Follow-up handling
    # ------------------------
    @staticmethod
    def _compose_followup_response(customer_name: str, ticket_id: str, intent_name: str) -> str:
        tail = (" We’ll keep you updated (typically within 1 business day). "
                "If there’s a better phone number for urgent follow-up, please share it.")

        if intent_name == "freeze_lost_stolen_card":
            return (f"Hi {customer_name}, I’m sorry to hear about your card. "
                    f"We’ve initiated an immediate card freeze on ticket #{ticket_id} to prevent unauthorized use. "
                    f"We’re also queuing a replacement card and will confirm shipment details shortly." + tail)

        if intent_name == "replace_card":
            return (f"Hi {customer_name}, we’ve added a replacement card request to ticket #{ticket_id}. "
                    f"We’ll confirm your mailing address and delivery timeframe in our next update." + tail)

        if intent_name == "fraud_charge_dispute":
            return (f"Thanks {customer_name}. We’ve flagged ticket #{ticket_id} for a fraud review. "
                    f"Please reply with dates, amounts, and any merchants you don’t recognize so we can accelerate the investigation." + tail)

        if intent_name == "travel_notice":
            return (f"Got it, {customer_name}. We’ve added a travel notice to ticket #{ticket_id}. "
                    f"Please share destinations and travel dates so we can ensure uninterrupted card usage." + tail)

        if intent_name == "address_update":
            return (f"Thanks {customer_name}. We’ve added an address update step to ticket #{ticket_id}. "
                    f"Please reply with your full new address for verification." + tail)

        if intent_name == "app_access_issue":
            return (f"Understood, {customer_name}. We’ve noted an app/device access issue on ticket #{ticket_id}. "
                    f"Please share your device type and any error messages; we’ll help you regain access." + tail)

        # Fallback
        return (f"Thanks for the update, {customer_name}. We’ve attached your message to ticket #{ticket_id} "
                f"and escalated it. Someone will reach out shortly to help you with this problem. "
                f"Please provide the best phone number for a quick call-back.")

    def handle_followup(self, *, ticket_id: str, customer_name: Optional[str], user_text: str) -> Tuple[str, Optional[str]]:
        """
        Stores a note, applies intent-specific flags, sets status to 'In-Progress' when an action is taken,
        and returns an empathetic, intent-aware message.
        """
        name = (customer_name or "Customer").strip() or "Customer"

        try:
            detected = classify_intent(user_text or "")
            # Always store the follow-up text as a note
            append_ticket_note(self.conn, ticket_id=ticket_id, note=user_text or "", author=name)

            took_action = False
            if detected.name == "freeze_lost_stolen_card":
                add_ticket_action_flag(self.conn, ticket_id=ticket_id, action="freeze_card_now")
                add_ticket_action_flag(self.conn, ticket_id=ticket_id, action="queue_replacement_card")
                took_action = True
            elif detected.name == "replace_card":
                add_ticket_action_flag(self.conn, ticket_id=ticket_id, action="queue_replacement_card")
                took_action = True
            elif detected.name == "fraud_charge_dispute":
                add_ticket_action_flag(self.conn, ticket_id=ticket_id, action="investigate_fraud")
                took_action = True
            elif detected.name == "travel_notice":
                add_ticket_action_flag(self.conn, ticket_id=ticket_id, action="add_travel_notice")
                took_action = True
            elif detected.name == "address_update":
                add_ticket_action_flag(self.conn, ticket_id=ticket_id, action="verify_address")
                took_action = True
            elif detected.name == "app_access_issue":
                add_ticket_action_flag(self.conn, ticket_id=ticket_id, action="reset_app_access")
                took_action = True

            if took_action:
                update_ticket_status(self.conn, ticket_id=ticket_id, status="In-Progress")

            msg = self._compose_followup_response(name, ticket_id, detected.name)

            log_event(
                self.conn,
                level="INFO",
                agent="FeedbackHandler",
                event="followup_handled",
                details={"ticket_id": ticket_id, "customer_name": name, "intent": detected.name, "took_action": took_action},
            )

            return msg, None

        except Exception as e:
            log_event(
                self.conn,
                level="WARN",
                agent="FeedbackHandler",
                event="followup_error",
                details={"ticket_id": ticket_id, "customer_name": name, "error": str(e)},
            )
            # Safe fallback
            return (
                "Thanks for the update. We’ve attached your message to the ticket and alerted our team. "
                "Someone will reach out shortly to help you with this problem. "
                "Please provide the best phone number for a quick call-back."
            ), str(e)
