# core/utils.py
from __future__ import annotations
import random
import re
from typing import Optional

# Matches: "ticket 123456", "ticket#123456", "Ticket #123456"
TICKET_RE = re.compile(r"(?:ticket\s*#?)(\d{6})", re.IGNORECASE)

# --- Intent heuristics for richer replies ---
def infer_issue_type(text: str) -> str:
    """
    Heuristic mapping from free text to an issue 'type' for templated responses.
    Types: 'lost_debit_card', 'debit_card_not_arrived', 'pin_reset', 'login_issue', 'generic'
    """
    t = (text or "").lower()

    # Lost / stolen debit card
    if any(k in t for k in ["lost my debit card", "lost debit", "lost my card", "stolen card", "debit card lost", "debit card stolen"]):
        return "lost_debit_card"

    # Card not arrived / replacement delay
    if any(k in t for k in ["card hasn't arrived", "card hasnt arrived", "replacement still hasn’t", "replacement still hasnt", "where is my card", "tracking for my card"]):
        return "debit_card_not_arrived"

    # PIN / login
    if "pin" in t and any(k in t for k in ["reset", "forgot", "change"]):
        return "pin_reset"
    if any(k in t for k in ["login", "log in", "password", "locked out", "2fa", "otp"]):
        return "login_issue"

    return "generic"

def extract_ticket_number(text: str) -> Optional[str]:
    """Extract a 6-digit ticket number from free text."""
    m = TICKET_RE.search(text or "")
    return m.group(1) if m else None


def generate_ticket_number() -> str:
    """Generate a zero-padded 6-digit ticket number."""
    return f"{random.randint(0, 999_999):06d}"


def rule_based_classify(text: str) -> str:
    """
    Simple fallback classifier for routing:
    Returns one of: 'positive_feedback' | 'negative_feedback' | 'query'
    """
    t = (text or "").lower()

    # If it looks like a status request or references a ticket, treat as query.
    if re.search(r"\bticket\b|status|check|track|update", t):
        return "query"

    # Positive cues
    pos_words = [
        "thank you", "thanks", "great", "appreciate",
        "resolved", "helpful", "awesome", "excellent",
    ]
    if any(w in t for w in pos_words):
        return "positive_feedback"

    # Negative cues
    neg_words = [
        "not working", "isn't working", "hasn't", "hasnt", "still", "issue",
        "problem", "late", "angry", "frustrated", "unhappy", "poor", "bad",
        "missing", "failed", "declined", "error",
    ]
    if any(w in t for w in neg_words):
        return "negative_feedback"

    # Default to query if unsure (safer for support flows)
    return "query"
