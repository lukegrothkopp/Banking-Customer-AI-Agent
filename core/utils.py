# core/utils.py
from __future__ import annotations
import random
import re
from typing import Optional

# Matches: "ticket 123456", "ticket#123456", "Ticket #123456"
TICKET_RE = re.compile(r"(?:ticket\s*#?)(\d{6})", re.IGNORECASE)


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
