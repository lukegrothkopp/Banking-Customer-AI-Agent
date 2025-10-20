# core/llm.py
from __future__ import annotations
import os
from typing import Optional, Tuple

# Optional (if running in Streamlit)
try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # type: ignore

# Safe import: works even if 'openai' isn't installed
try:
    from openai import OpenAI  # SDK v1.x
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


def _from_secrets(name: str) -> Optional[str]:
    """Read from Streamlit secrets if available."""
    if st is None:
        return None
    try:
        val = st.secrets.get(name)  # type: ignore[attr-defined]
        return str(val) if val else None
    except Exception:
        return None


def _load_api_key() -> Optional[str]:
    """Prefer Streamlit secrets, then env; ignore masked/placeholder-looking values."""
    key = _from_secrets("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    masked_patterns = ("***", "A**", "REPLACE_ME", "YOUR_KEY")
    if any(p in key for p in masked_patterns) or key.strip().lower().startswith("openai_a"):
        return None
    return key.strip()


def check_openai_ready() -> Tuple[bool, str]:
    """Return (ok, message) indicating whether OpenAI SDK and API key look usable."""
    if OpenAI is None:
        return (False, "OpenAI SDK not installed. Run `pip install openai>=1.0.0`.")
    key = _load_api_key()
    if not key:
        return (False, "Missing or placeholder OPENAI_API_KEY. Add it to .streamlit/secrets.toml or environment.")
    return (True, "OpenAI client looks configured.")


class LLMClient:
    """Thin wrapper around OpenAI client with graceful fallback."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # Prefer explicit key, then secrets/env
        resolved_key = api_key or _load_api_key()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.enabled = bool(resolved_key and OpenAI is not None)
        self.client = OpenAI(api_key=resolved_key) if self.enabled else None

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        """
        Generic chat wrapper.
        Returns a short string or raises RuntimeError if the LLM path fails.
        """
        if not self.enabled or not self.client:
            # Do not silently fake output; signal upstream to fall back.
            raise RuntimeError("LLM disabled (no valid API key or OpenAI SDK missing).")

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=64,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            # Surface a clear error so caller can fall back to rule-based
            raise RuntimeError(f"OpenAI call failed: {e}")

    # Optional convenience for your ClassifierAgent
    def classify(self, text: str) -> str:
        """
        Return one of: 'positive_feedback', 'negative_feedback', 'query'.
        Raises RuntimeError if LLM path fails (so caller can fall back).
        """
        system = (
            "You are a short text classifier for banking support. "
            "Given a user message, return exactly one label:\n"
            " - positive_feedback\n - negative_feedback\n - query\n"
            "Return only the label, no punctuation."
        )
        out = self.chat(system=system, user=text, temperature=0)
        low = out.lower()
        if "positive" in low:
            return "positive_feedback"
        if "negative" in low:
            return "negative_feedback"
        return "query"
