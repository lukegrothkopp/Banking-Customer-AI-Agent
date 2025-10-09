from __future__ import annotations
import random
import re
from typing import Optional


TICKET_RE = re.compile(r"(?:ticket\s*#?)(\d{6})", re.IGNORECASE)


def extract_ticket_number(text: str) -> Optional[str]:
m = TICKET_RE.search(text)
return m.group(1) if m else None


def generate_ticket_number() -> str:
return f"{random.randint(0, 999_999):06d}"


def rule_based_classify(text: str) -> str:
"""Very simple fallback classifier: 'positive_feedback' | 'negative_feedback' | 'query'"""
t = text.lower()
# Query if it contains a ticket pattern or typical verbs
if re.search(r"\bticket\b|status|check|track|update", t):
return "query"
# Positive cues
pos_words = ["thank you", "thanks", "great", "appreciate", "resolved", "helpful", "awesome"]
if any(w in t for w in pos_words):
return "positive_feedback"
# If contains negative cues or complaint words, mark as negative
neg_words = ["not working", "hasn't", "hasnt", "still", "issue", "problem", "late", "angry", "frustrated", "unhappy", "poor", "bad", "missing"]
if any(w in t for w in neg_words):
return "negative_feedback"
# Default heuristic: query
return "query"
