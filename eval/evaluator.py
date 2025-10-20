# eval/evaluator.py
"""
Compact classifier benchmark for the Banking Support Agent.

Returns: (correct, total, rows)
  - correct: int
  - total: int
  - rows: list[dict] with keys: text, expected, predicted, correct
"""

from typing import List, Tuple, Dict
from agents.classifier import ClassifierAgent

# Canonical labels expected from your ClassifierAgent:
#   "positive_feedback", "negative_feedback", "query"
TESTS: List[Dict[str, str]] = [
    # Positive feedback
    {"text": "Thanks for resolving my credit card issue!", "expected": "positive_feedback"},
    {"text": "Appreciate the quick help on my loan question.", "expected": "positive_feedback"},
    {"text": "Great support today—really happy!", "expected": "positive_feedback"},

    # Negative feedback (complaints)
    {"text": "My debit card replacement still hasn’t arrived.", "expected": "negative_feedback"},
    {"text": "I’m frustrated—charges are incorrect and no one responded.", "expected": "negative_feedback"},
    {"text": "Terrible experience with net banking again.", "expected": "negative_feedback"},

    # Queries (ask for info / status lookups)
    {"text": "Could you check the status of ticket 650932?", "expected": "query"},
    {"text": "What’s the balance on my savings account?", "expected": "query"},
    {"text": "How long does a wire transfer take?", "expected": "query"},

    # Edge phrasing / mixed tone
    {"text": "Thanks, but the dispute still shows as pending. Can you update me?", "expected": "query"},
    {"text": "Not cool—card is locked again. Why?", "expected": "negative_feedback"},
    {"text": "Great agent last time—can you also tell me my ticket status 123456?", "expected": "query"},
]

def run_benchmark(use_llm: bool = False, limit: int = None) -> Tuple[int, int, List[Dict[str, str]]]:
    """
    Execute the benchmark.
    :param use_llm: If True, use LLM path in ClassifierAgent (if implemented in your repo).
    :param limit: Optional cap on number of test cases to run.
    :return: (correct, total, rows)
    """
    agent = ClassifierAgent(use_llm=use_llm)
    cases = TESTS[:limit] if limit else TESTS

    correct = 0
    rows: List[Dict[str, str]] = []

    for case in cases:
        text = case["text"]
        expected = case["expected"]
        try:
            predicted = agent.classify(text)
        except Exception as e:
            predicted = f"ERROR: {e}"

        ok = (predicted == expected)
        correct += int(ok)
        rows.append({
            "text": text,
            "expected": expected,
            "predicted": predicted,
            "correct": ok,
        })

    total = len(cases)
    return correct, total, rows
