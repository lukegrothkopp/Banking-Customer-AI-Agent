# agents/intent.py
import re
from dataclasses import dataclass

@dataclass
class DetectedIntent:
    name: str
    confidence: float

INTENT_PATTERNS = [
    # (name, regex pattern, confidence)
    ("freeze_lost_stolen_card", r"\b(stolen|lost)\b.*\b(card|debit|credit)\b|\b(shut ?off|freeze|block)\b.*\b(card)\b", 0.95),
    ("replace_card", r"\b(replace|replacement)\b.*\b(card)\b|\b(new\b.*\bcard)\b", 0.9),
    ("fraud_charge_dispute", r"\b(unauthorized|fraud|dispute)\b.*\b(charge|transaction)\b", 0.9),
    ("travel_notice", r"\b(travel|out of (the )?country|trip)\b", 0.85),
    ("address_update", r"\b(address|moved|move)\b.*\b(update|change)\b", 0.85),
    ("app_access_issue", r"\b(phone|device|app|login|signin|sign in|locked)\b.*\b(issue|problem|can.?t|cannot)\b", 0.8),
]

def classify_intent(user_text: str) -> DetectedIntent:
    text = user_text.lower()
    for name, pattern, conf in INTENT_PATTERNS:
        if re.search(pattern, text):
            return DetectedIntent(name=name, confidence=conf)
    return DetectedIntent(name="general_followup", confidence=0.5)
