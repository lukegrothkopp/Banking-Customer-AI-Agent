# agents/classifier.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

from ..core.llm import LLMClient
from ..core.logging import log_info
from ..core.utils import rule_based_classify

Label = Literal["positive_feedback", "negative_feedback", "query"]

SYSTEM = (
    "You are a banking inbox classifier. Given a user message, classify it as "
    "one of: positive_feedback, negative_feedback, or query. Answer with only the label."
)


class ClassifierAgent(BaseModel):
    use_llm: bool = True  # whether to use LLM; falls back to rule-based

    def classify(self, text: str) -> Label:
        """
        Returns one of: 'positive_feedback' | 'negative_feedback' | 'query'
        """
        label: Label = "query"
        if self.use_llm:
            llm = LLMClient()
            if llm.enabled:
                out = llm.chat(SYSTEM, f"Message: {text}\nRespond with one label only.")
                cand = (out or "").strip().lower()
                if cand in {"positive_feedback", "negative_feedback", "query"}:
                    label = cand  # type: ignore[assignment]
                else:
                    label = rule_based_classify(text)  # fallback if LLM response is noisy
            else:
                label = rule_based_classify(text)
        else:
            label = rule_based_classify(text)

        log_info("Classifier", "classified", f"label={label}")
        return label
