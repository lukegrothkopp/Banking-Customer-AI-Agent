from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from ..agents.classifier import ClassifierAgent

@dataclass
class EvalCase:
text: str
expected: str # "positive_feedback" | "negative_feedback" | "query"

TESTS: List[EvalCase] = [
EvalCase("Thanks for resolving my credit card issue!", "positive_feedback"),
EvalCase("My debit card replacement still hasn’t arrived.", "negative_feedback"),
EvalCase("Could you check the status of ticket 650932?", "query"),
EvalCase("Net banking login keeps failing.", "negative_feedback"),
EvalCase("Appreciate the quick help earlier.", "positive_feedback"),
]

def run_eval(use_llm: bool = True) -> Tuple[int, int, List[Tuple[str, str, str]]]:
clf = ClassifierAgent(use_llm=use_llm)
correct = 0
rows: List[Tuple[str, str, str]] = []
for case in TESTS:
pred = clf.classify(case.text)
if pred == case.expected:
correct += 1
rows.append((case.text, case.expected, pred))
return correct, len(TESTS), rows
