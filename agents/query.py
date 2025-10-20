# agents/query.py
from typing import Optional
from core.db import get_ticket
from core.utils import extract_ticket_number, infer_issue_type

class QueryHandler:
    """
    Returns a helpful, human-friendly status message.
    Still accepts a single 'text' input so existing call sites work.
    """

    def __init__(self, conn=None):
        self.conn = conn  # kept for future use if you decide to expand

    def handle(self, text: str) -> str:
        # 1) Extract ticket number from the incoming text
        tno = extract_ticket_number(text)
        if not tno:
            return "I couldn’t find a 6-digit ticket number in your message. Please provide one, or uncheck the 'I already have a ticket' box so I can create or reuse one automatically."

        # 2) Lookup the ticket (backward-compatible get_ticket handles both styles)
        rec = get_ticket(tno)
        if not rec:
            return f"I couldn’t find ticket #{tno}. Please double-check the number or reply without a ticket so I can create one for you."

        status = rec.get("status", "Open")
        description = (rec.get("description") or "").strip()

        # 3) Infer intent from the user's message first, then fallback to the stored description
        issue_type = infer_issue_type(text) or infer_issue_type(description)

        # 4) Build a richer, actionable reply
        base = f"Your ticket #{tno} is currently marked as: **{status}**."

        detail = self._detail_for(issue_type, status, description)

        # 5) Join the response
        return f"{base}\n\n{detail}"

    # ---------------- internal helpers ----------------

    def _detail_for(self, issue_type: str, status: str, description: str) -> str:
        """
        Returns a templated, helpful paragraph describing what's likely happening,
        typical timelines, and next steps. These are generic SLAs that you can tune.
        """
        if issue_type == "lost_debit_card":
            if status.lower() in ("open", "in-progress"):
                return (
                    "I’ve initiated a **debit-card replacement workflow** for you. "
                    "Typical processing takes **1 business day**, with standard delivery in **3–5 business days**. "
                    "If you need it faster, reply **“expedite”** and we’ll check availability for **1–2 business day** shipping. "
                    "If you haven’t already, consider **temporarily blocking your old card** to prevent new charges."
                )
            else:  # resolved or other
                return (
                    "This replacement request appears **completed**. "
                    "If you haven’t received your new card yet, reply **“tracking”** and we’ll share shipment details or reissue if needed."
                )

        if issue_type == "debit_card_not_arrived":
            return (
                "Your replacement card is **in progress**. Standard shipping is **3–5 business days** after processing. "
                "If it’s past that window, reply **“tracking”** so we can verify shipment status or **reissue** the card."
            )

        if issue_type == "pin_reset":
            return (
                "For **PIN resets**, we’ll text or email a secure verification link. "
                "Once verified, you can set a new PIN immediately. If you don’t receive a code within a few minutes, reply **“resend code”**."
            )

        if issue_type == "login_issue":
            return (
                "For **login issues**, we’ll verify your identity and help you unlock the account or reset your password. "
                "If you see an **OTP/2FA** problem, reply **“2FA help”** to get step-by-step instructions."
            )

        # Generic catch-all
        if status.lower() in ("open", "in-progress"):
            return (
                "We’re actively working on this. Typical updates are provided within **1 business day**. "
                "If you can share any new details (e.g., dates, amounts, device used), reply with them here to help us resolve faster."
            )
        else:
            return "This ticket looks **resolved**. If anything is still outstanding, reply here and we’ll reopen and continue assisting."
