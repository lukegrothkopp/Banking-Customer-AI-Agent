from __future__ import annotations
import os
from typing import Optional


try:
from openai import OpenAI
except Exception: # pragma: no cover
OpenAI = None # type: ignore




class LLMClient:
"""Thin wrapper around OpenAI client with graceful fallback."""


def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
self.api_key = api_key or os.getenv("OPENAI_API_KEY")
self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
self.enabled = bool(self.api_key and OpenAI is not None)
self.client = OpenAI(api_key=self.api_key) if self.enabled else None


def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
if not self.enabled or not self.client:
# Fallback: echo-lite behavior; real routing uses rule-based backup
return "(LLM disabled)"
resp = self.client.chat.completions.create(
model=self.model,
temperature=temperature,
messages=[
{"role": "system", "content": system},
{"role": "user", "content": user},
],
)
return resp.choices[0].message.content or ""
