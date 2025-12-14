from __future__ import annotations

from typing import Iterable


class SimpleChunker:
    """
    Returns list[(chunk_index, chunk_text)].
    """
    def __init__(self, *, chunk_size: int = 800, overlap: int = 120):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be in [0, chunk_size)")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[tuple[int, str]]:
        t = (text or "").strip()
        if not t:
            return [(0, "")]

        chunks: list[tuple[int, str]] = []
        start = 0
        idx = 0
        step = self.chunk_size - self.overlap

        while start < len(t):
            part = t[start : start + self.chunk_size].strip()
            if part:
                chunks.append((idx, part))
                idx += 1
            start += step

        return chunks
