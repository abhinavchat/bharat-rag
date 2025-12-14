from __future__ import annotations
from typing import Protocol


class LLM(Protocol):
    def generate(self, prompt: str) -> str: ...
